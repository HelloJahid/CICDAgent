"""Tests for the Bedrock tool-use loop.

We never call AWS. A FakeBedrockClient returns scripted Converse responses, which
lets us prove the loop runs tools and feeds results back exactly as the real API
expects, with zero cost and full determinism.
"""

from app.agent import run_agent


class FakeBedrockClient:
    """Replays a queue of Converse responses and records the requests it saw."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.requests = []

    def converse(self, **kwargs):
        self.requests.append(kwargs)
        return self._responses.pop(0)


def _tool_use_response(tool_use_id, name, tool_input):
    return {
        "stopReason": "tool_use",
        "output": {
            "message": {
                "role": "assistant",
                "content": [
                    {"toolUse": {"toolUseId": tool_use_id, "name": name, "input": tool_input}}
                ],
            }
        },
    }


def _final_response(text):
    return {
        "stopReason": "end_turn",
        "output": {"message": {"role": "assistant", "content": [{"text": text}]}},
    }


def test_agent_runs_tool_then_returns_final_answer():
    client = FakeBedrockClient(
        [
            _tool_use_response(
                "t1", "estimate_demand", {"origin": "Albury", "destination": "Wagga Wagga"}
            ),
            _final_response("About 441 passengers a day on the Albury to Wagga route."),
        ]
    )

    result = run_agent("How busy is Albury to Wagga?", client=client)

    assert result["stop_reason"] == "end_turn"
    assert result["tool_calls"] == ["estimate_demand"]
    assert "passengers" in result["reply"]


def test_tool_result_is_fed_back_to_the_model():
    client = FakeBedrockClient(
        [
            _tool_use_response(
                "t1", "estimate_demand", {"origin": "Sydney", "destination": "Melbourne"}
            ),
            _final_response("That is a high-demand corridor."),
        ]
    )

    run_agent("Sydney to Melbourne demand?", client=client)

    # The second request must carry a toolResult referencing the tool use id.
    second_request_messages = client.requests[1]["messages"]
    tool_result_blocks = [
        block
        for message in second_request_messages
        for block in message.get("content", [])
        if "toolResult" in block
    ]
    assert tool_result_blocks, "expected a toolResult message to be sent back"
    tr = tool_result_blocks[0]["toolResult"]
    assert tr["toolUseId"] == "t1"
    assert tr["content"][0]["json"]["known"] is True


def test_agent_handles_immediate_final_answer_without_tools():
    client = FakeBedrockClient([_final_response("Hello, ask me about a route.")])
    result = run_agent("hi", client=client)
    assert result["tool_calls"] == []
    assert result["stop_reason"] == "end_turn"


def test_agent_stops_at_max_turns():
    # Always returns tool_use, so the loop must bail out at max_turns.
    looping = [_tool_use_response(f"t{i}", "list_routes", {}) for i in range(10)]
    client = FakeBedrockClient(looping)
    result = run_agent("loop forever", client=client, max_turns=3)
    assert result["stop_reason"] == "max_turns"
    assert len(result["tool_calls"]) == 3
