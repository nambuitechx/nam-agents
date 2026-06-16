# Agents package

Python package for a general-purpose Q&A agent powered by [Strands Agents](https://strandsagents.com/) and [Amazon Bedrock](https://aws.amazon.com/bedrock/). The same agent runs locally (CLI), as an HTTP server (AgentCore contract), and in a container on Bedrock AgentCore Runtime.

## Files

| File | Purpose |
|------|---------|
| `general_agent.py` | Strands agent factory — Bedrock model + system prompt |
| `settings.py` | Configuration from environment variables / `.env` |
| `main.py` | Interactive local CLI |
| `runtime.py` | AgentCore Runtime entry point (`/invocations`, `/ping`) |
| `Dockerfile` | ARM64 container image for AgentCore |
| `pyproject.toml` | Dependencies and package metadata |

## Setup

```bash
cd src/agents
uv sync
cp .env.example .env
```

Edit `.env` with your Bedrock model and AWS credentials (or rely on `aws configure` / IAM role).

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BEDROCK_MODEL_ID` | `apac.anthropic.claude-sonnet-4-20250514-v1:0` | Model or inference profile ID |
| `BEDROCK_REGION` | `ap-southeast-1` | AWS region for Bedrock |
| `BEDROCK_TEMPERATURE` | *(unset)* | Optional sampling temperature |
| `BEDROCK_MAX_TOKENS` | *(unset)* | Optional max output tokens |

Aliases `STRANDS_MODEL_ID`, `AWS_REGION`, and `BEDROCK_REGION` are also accepted.

When deployed via Terraform, `BEDROCK_MODEL_ID`, `BEDROCK_REGION`, and optional tuning vars are injected into the container by `infra/agent_runtime.tf`.

## Local usage

### Interactive CLI

```bash
uv run python main.py
```

Type questions at the `You:` prompt. Exit with `exit` or `quit`.

### Test deployed AgentCore Runtime (aioboto3)

Interactive CLI against a live AgentCore Runtime ARN (same REPL UX as `main.py`):

```bash
uv run python test_runtime.py arn:aws:bedrock-agentcore:ap-southeast-1:123456789012:runtime/...
# or
export AGENT_RUNTIME_ARN="$(terraform -chdir=../../infra output -raw agent_runtime_arn)"
uv run python test_runtime.py
```

Requires `bedrock-agentcore:InvokeAgentRuntime` on your AWS credentials. Region is parsed from the ARN, or override with `--region`.

### AgentCore HTTP server (local)

Runs the same entry point used in production on port 8080:

```bash
uv run python runtime.py
```

Test with curl:

```bash
# Health check
curl http://localhost:8080/ping

# Invoke
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is machine learning?"}'
```

### Use the agent in code

```python
from general_agent import create_agent

agent = create_agent()
result = agent("Explain quantum computing in one paragraph.")
print(result.message)
```

## AgentCore Runtime

`runtime.py` uses the [`bedrock-agentcore`](https://pypi.org/project/bedrock-agentcore/) Python SDK — not the AgentCore CLI. It wraps `create_agent()` with a `@app.entrypoint` handler.

**Request payload:**

```json
{ "prompt": "Your question here" }
```

**Response:**

```json
{ "result": "Agent answer text..." }
```

### Container requirements

AgentCore Runtime enforces:

- **Architecture:** `linux/arm64`
- **Port:** 8080
- **Endpoints:** `POST /invocations`, `GET /ping`
- **User:** non-root (configured in `Dockerfile`)

Build and test locally:

```bash
docker buildx build --platform linux/arm64 -t nam-agents:local --load .
docker run --platform linux/arm64 -p 8080:8080 \
  -e AWS_REGION=ap-southeast-1 \
  -e BEDROCK_MODEL_ID=apac.anthropic.claude-sonnet-4-20250514-v1:0 \
  nam-agents:local
```

Deploy to AWS is handled from the repo root — see [../../README.md](../../README.md) and `scripts/deploy-image.sh`.

## Extending the agent

### Change the system prompt

Edit `SYSTEM_PROMPT` in `general_agent.py`.

### Add tools or a different model

Use Strands APIs inside `create_agent()` in `general_agent.py`. The runtime entry point in `runtime.py` can stay thin — it only forwards the `prompt` field to the agent.

### Add a new agent

1. Create a new module (e.g. `research_agent.py`) with its own `create_agent()`.
2. Add a matching `runtime_*.py` entry point or parameterize `runtime.py`.
3. Add a separate ECR image / Terraform runtime resource if deploying independently.

## Dependencies

- `strands-agents` — agent framework and Bedrock model integration
- `pydantic-settings` — typed settings from env
- `bedrock-agentcore` — AgentCore Runtime HTTP server (production entry point)

Managed with [uv](https://docs.astral.sh/uv/). Lockfile: `uv.lock`.
