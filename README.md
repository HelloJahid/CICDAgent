# Route Demand Assistant — a CI/CD pipeline showcase

This repository is a portfolio project. The **star is the CI/CD pipeline** built with GitHub
Actions, which builds, tests, scans and deploys a small agentic AI app to AWS. The app itself
is deliberately simple cargo for the pipeline to ship.

## The app (the cargo)

A small **AWS Bedrock agent** that estimates daily passenger demand on Australian
origin-to-destination routes. It uses the Bedrock **Converse API with tool use**: the model
decides when to call the deterministic `estimate_demand` and `list_routes` tools, then answers
in plain language. It is served by FastAPI with two endpoints:

- `GET /ping` — health check
- `POST /invocations` — send `{"message": "How busy is Albury to Wagga?"}`, get a reply

The same container image runs locally and on AWS Lambda (via the Lambda Web Adapter).

## Project layout

```
app/                 # the agent app + tests
  agent.py           # Bedrock Converse tool-use loop
  tools.py           # deterministic demand tools (pure, unit-tested)
  main.py            # FastAPI /ping + /invocations
  tests/             # pytest suite (CI runs these; Bedrock is mocked)
infra/terraform/     # AWS infrastructure as code (added in a later phase)
.github/workflows/   # ci.yaml + cd.yaml — the centrepiece (added in a later phase)
docs/                # reference doc + Medium blog
```

## Run the app locally

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

A live `/invocations` call needs AWS credentials and Bedrock model access for
`au.anthropic.claude-haiku-4-5-20251001-v1:0` in `ap-southeast-2`. The tests do not.

## Lint and test

```powershell
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\ruff.exe format --check .
.\.venv\Scripts\python.exe -m pytest
```
