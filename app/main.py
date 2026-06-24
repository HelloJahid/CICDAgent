"""FastAPI service wrapping the Route Demand Assistant.

Two endpoints, matching the simple container contract in CLAUDE.md:

* ``GET /ping``         - health check used by smoke tests and the Lambda
                          Web Adapter readiness probe.
* ``POST /invocations`` - the agent entrypoint. Send a natural-language
                          question, get the assistant's reply back.

The same image runs locally (uvicorn) and on AWS Lambda (via the Lambda Web
Adapter), so there is no Lambda-specific code here.
"""

from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.agent import get_model_id, run_agent

app = FastAPI(title="Route Demand Assistant", version="0.1.0")


class InvocationRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Natural-language question for the agent.")


class InvocationResponse(BaseModel):
    reply: str
    stop_reason: str
    tool_calls: list[str]


@app.get("/ping")
def ping() -> dict:
    """Liveness/readiness check. Cheap and dependency-free on purpose."""
    return {"status": "ok", "model_id": get_model_id()}


@app.post("/invocations", response_model=InvocationResponse)
def invocations(request: InvocationRequest) -> InvocationResponse:
    """Run the user's question through the Bedrock tool-use agent."""
    result = run_agent(request.message)
    return InvocationResponse(**result)
