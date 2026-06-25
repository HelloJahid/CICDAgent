# Route Demand Assistant — an end-to-end CI/CD pipeline on AWS

[![CI](https://github.com/HelloJahid/CICDAgent/actions/workflows/ci.yaml/badge.svg)](https://github.com/HelloJahid/CICDAgent/actions/workflows/ci.yaml)
[![CD](https://github.com/HelloJahid/CICDAgent/actions/workflows/cd.yaml/badge.svg)](https://github.com/HelloJahid/CICDAgent/actions/workflows/cd.yaml)

A portfolio project whose centrepiece is a **GitHub Actions CI/CD pipeline** that builds, tests,
security-scans and deploys a containerised application to **AWS Lambda**, authenticating to AWS with
**keyless OpenID Connect** and promoting releases through **staging and production environments** with a
**manual approval gate**.

The application it ships is a small **AWS Bedrock agent** that estimates daily passenger demand on
Australian routes. The app is deliberately simple. It exists to give the pipeline something real and
modern to deliver.

## Architecture

```
  Pull request to main                 Merge to main
        │                                    │
        ▼                                    ▼
  ┌───────────┐                     ┌──────────────────────────────────────────┐
  │    CI     │  lint ║ test        │                  CD                        │
  │ ci.yaml   │  then build+scan    │  lint ║ test → build image (git SHA)       │
  └───────────┘  (no deploy)        │      → push to ECR  (via GitHub OIDC)      │
                                    │      → deploy to STAGING  + smoke test     │
                                    │      → manual approval (production env)    │
                                    │      → deploy to PRODUCTION + smoke test   │
                                    │      → Slack notify (success / failure)    │
                                    └──────────────────────────────────────────┘
                                                       │ pulls image
                                                       ▼
                         Amazon ECR  ──►  AWS Lambda (staging + production)
                                          container image + Lambda Web Adapter
                                          public Function URL  →  /ping  /invocations
```

All AWS resources are defined with **Terraform** and can be removed with a single `terraform destroy`.

## The CI/CD pipeline

### Continuous Integration — [`.github/workflows/ci.yaml`](.github/workflows/ci.yaml)
Runs on every pull request to `main` (path-filtered).
- **`lint`** and **`test`** run in parallel (`ruff` and `pytest`).
- **`build`** is gated on both passing. It builds the container image and runs a **Trivy**
  vulnerability scan, failing on fixable HIGH or CRITICAL issues.

### Continuous Delivery and Deployment — [`.github/workflows/cd.yaml`](.github/workflows/cd.yaml)
Runs on a merge to `main`.
- Re-runs `lint` and `test`, then **builds an image tagged with the git SHA** and pushes it to ECR.
- Deploys to **staging** automatically and smoke-tests it.
- **Pauses for manual approval** before deploying the same image to **production**, then smoke-tests it.
- Posts a **Slack** alert on a successful production deploy and on any failure.

## Security

- **No AWS access keys anywhere.** GitHub Actions assumes an IAM role through **OIDC**, exchanging a
  short-lived signed token for temporary credentials. The role trusts only this repository.
- **Least-privilege IAM.** Separate roles for the Lambda runtime (`bedrock:InvokeModel` plus logs) and
  the pipeline (ECR push and Lambda deploy only).
- **Third-party actions pinned to commit SHAs**, not mutable tags.
- **Image scanning** with Trivy in CI and ECR scan-on-push.
- **Manual approval** protects production via a GitHub Environment reviewer rule.

## Tech stack

Python · FastAPI · AWS Bedrock (Converse API tool use) · Docker · AWS Lambda (container image) +
AWS Lambda Web Adapter · Amazon ECR · Terraform · GitHub Actions.

## Repository layout

```
app/                         the agent app and its tests
  agent.py                   Bedrock Converse tool-use loop
  tools.py                   deterministic demand tools (pure, unit-tested)
  main.py                    FastAPI /ping + /invocations
  tests/                     pytest suite (Bedrock mocked, no live AWS)
infra/terraform/             ECR, Lambda (staging + prod), IAM, OIDC, logs
.github/
  workflows/ci.yaml          CI: lint, test, build, scan
  workflows/cd.yaml          CD: build, push, deploy, approve, notify
  actions/setup-python-env/  reusable composite action
Dockerfile                   one image for local and Lambda
```

## Running it

### Locally (app and tests, no AWS needed)
```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt   # Windows
ruff check . && ruff format --check .
python -m pytest
python -m uvicorn app.main:app --reload                       # serves /ping and /invocations
```

### Deploy to AWS
1. Enable **Bedrock model access** for Claude Haiku 4.5 in your region (`ap-southeast-2`).
2. Provide AWS credentials locally once and run the Terraform bootstrap in `infra/terraform`
   (`terraform init`, then `terraform apply`). This creates ECR, the IAM roles and the OIDC provider.
3. Set the GitHub repository **variables** `AWS_ROLE_ARN`, `AWS_REGION`, `ECR_REPOSITORY` and the
   **secret** for the Slack webhook.
4. Push to `main`. The pipeline builds, pushes, deploys to staging, waits for your approval, then
   deploys to production.

### Teardown
```bash
cd infra/terraform
terraform destroy
```

## The app (the cargo)

A single Bedrock agent behind FastAPI. `POST /invocations` with `{"message": "How busy is the Albury
to Wagga route?"}` and the model decides to call the deterministic `estimate_demand` tool, then answers
in plain language. `GET /ping` is a dependency-free health check used by the deployment smoke tests.

## License

Released under the [MIT License](LICENSE).
