"""The Route Demand Assistant agent.

A deliberately small agent built on the AWS Bedrock **Converse API** with **tool
use** (function calling). The Converse API is model-agnostic, so the same code
works across Bedrock models, and the tool-use loop is the canonical "model asks
to call a tool, we run it, feed the result back, model answers" pattern.

The agent is the cargo for the CI/CD pipeline, so it stays simple: one model,
two deterministic tools (see ``tools.py``), and a bounded loop.
"""

from __future__ import annotations

import os

import boto3

from app.tools import TOOL_FUNCTIONS, estimate_demand, list_routes

# AU-localised inference profile for Claude Haiku 4.5: cheapest modern model that
# supports tool use, kept in-region for the Australian theme. Override per
# environment with BEDROCK_MODEL_ID. Verified available in ap-southeast-2.
DEFAULT_MODEL_ID = "au.anthropic.claude-haiku-4-5-20251001-v1:0"

SYSTEM_PROMPT = (
    "You are the Route Demand Assistant. You help users estimate daily passenger "
    "demand on Australian origin-to-destination routes. Use the estimate_demand "
    "tool to get figures and list_routes to see what data is available. Never "
    "invent numbers. If a route is unknown, say so plainly and suggest using "
    "list_routes. Keep answers short and clear."
)

# Tool schemas advertised to the model via the Converse API. The model reads
# these to decide whether and how to call a tool.
TOOL_CONFIG = {
    "tools": [
        {
            "toolSpec": {
                "name": "estimate_demand",
                "description": (
                    "Estimate daily passenger demand between an origin and a "
                    "destination city in Australia."
                ),
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "origin": {"type": "string", "description": "Origin city name."},
                            "destination": {
                                "type": "string",
                                "description": "Destination city name.",
                            },
                        },
                        "required": ["origin", "destination"],
                    }
                },
            }
        },
        {
            "toolSpec": {
                "name": "list_routes",
                "description": "List the origin-to-destination routes that have demand data.",
                "inputSchema": {"json": {"type": "object", "properties": {}}},
            }
        },
    ]
}


def get_model_id() -> str:
    """Resolve the Bedrock model id, allowing per-environment override."""
    return os.environ.get("BEDROCK_MODEL_ID", DEFAULT_MODEL_ID)


def _make_client():
    """Create a Bedrock Runtime client. Region comes from the standard AWS env."""
    region = os.environ.get("AWS_REGION", "ap-southeast-2")
    return boto3.client("bedrock-runtime", region_name=region)


def _dispatch_tool(name: str, tool_input: dict) -> dict:
    """Run a requested tool by name and return its structured result."""
    func = TOOL_FUNCTIONS.get(name)
    if func is None:
        return {"error": f"Unknown tool: {name}"}
    return func(**tool_input)


def _final_text(message: dict) -> str:
    """Join the text blocks of a Converse assistant message into one string."""
    return "".join(block["text"] for block in message.get("content", []) if "text" in block).strip()


def run_agent(user_message: str, client=None, max_turns: int = 5) -> dict:
    """Run one conversation turn through the Bedrock tool-use loop.

    Args:
        user_message: the user's natural-language question.
        client: an optional Bedrock Runtime client. Injectable so tests can pass
            a fake and run with no AWS calls.
        max_turns: safety bound on tool-use round trips.

    Returns:
        ``{"reply": <text>, "stop_reason": <str>, "tool_calls": [<names>]}``.
    """
    client = client or _make_client()
    model_id = get_model_id()
    messages = [{"role": "user", "content": [{"text": user_message}]}]
    tool_calls: list[str] = []

    for _ in range(max_turns):
        response = client.converse(
            modelId=model_id,
            system=[{"text": SYSTEM_PROMPT}],
            messages=messages,
            toolConfig=TOOL_CONFIG,
        )
        output_message = response["output"]["message"]
        messages.append(output_message)
        stop_reason = response.get("stopReason")

        if stop_reason != "tool_use":
            return {
                "reply": _final_text(output_message),
                "stop_reason": stop_reason,
                "tool_calls": tool_calls,
            }

        # The model asked for one or more tools. Run each and feed results back.
        tool_results = []
        for block in output_message["content"]:
            if "toolUse" not in block:
                continue
            tool_use = block["toolUse"]
            tool_calls.append(tool_use["name"])
            result = _dispatch_tool(tool_use["name"], tool_use.get("input", {}))
            tool_results.append(
                {
                    "toolResult": {
                        "toolUseId": tool_use["toolUseId"],
                        "content": [{"json": result}],
                    }
                }
            )
        messages.append({"role": "user", "content": tool_results})

    return {
        "reply": "Sorry, I could not complete that within the allowed steps.",
        "stop_reason": "max_turns",
        "tool_calls": tool_calls,
    }


__all__ = ["run_agent", "get_model_id", "estimate_demand", "list_routes", "TOOL_CONFIG"]
