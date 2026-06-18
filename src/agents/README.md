# Agents package

General-purpose Q&A agent on [Strands Agents](https://strandsagents.com/) and [Amazon Bedrock](https://aws.amazon.com/bedrock/). Runs locally (CLI / HTTP), and in a container on Bedrock AgentCore Runtime.

**Repo-level docs:** [Local development quickstart](../../README.md#local-development-quickstart), [Makefile cheat sheet](../../README.md#make-vs-raw-commands-cheat-sheet), [deploy](../../README.md#deploy-agents). Document embedding: [../embedding/README.md](../embedding/README.md).

## Quick start (local)

Full step-by-step (OpenSearch → embed → KB agent): **[README — Local development quickstart](../../README.md#local-development-quickstart)**.

Minimal commands from repo root:

```bash
make up && make embed-sync && make embed FILE=/path/to/doc.md
make sync && make kb-cli                    # interactive KB agent
# or: make kb-http  (terminal 1) + make ping (terminal 2)
```

## Layout

| Path | Purpose |
|------|---------|
| `core/agent.py` | General Q&A agent factory |
| `core/kb_agent.py` | Knowledge-base agent — OpenSearch retrieval tool |
| `core/knowledge_base.py` | Bedrock query embedding + OpenSearch k-NN search |
| `configs/settings.py` | Settings from env / `.env` |
| `cmd/main.py` | Interactive local CLI (direct Bedrock) |
| `cmd/kb_main.py` | Interactive CLI for the knowledge-base agent |
| `cmd/test_runtime.py` | Interactive CLI against deployed AgentCore runtime |
| `runtimes/simple.py` | Production HTTP entry point (`/invocations`, `/ping`) |
| `runtimes/knowledge_base.py` | KB agent HTTP entry point (OpenSearch retrieval) |
| `Dockerfile` | ARM64 container for AgentCore |

## Setup

```bash
cd src/agents
uv sync
cp .env.example .env   # optional; aws configure / IAM also works
```

Or from repo root: `make sync`.

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BEDROCK_MODEL_ID` | `apac.anthropic.claude-sonnet-4-20250514-v1:0` | Model or inference profile ID |
| `BEDROCK_REGION` | `ap-southeast-1` | AWS region for Bedrock |
| `BEDROCK_TEMPERATURE` | *(unset)* | Optional sampling temperature |
| `BEDROCK_MAX_TOKENS` | *(unset)* | Optional max output tokens |
| `EMBEDDING_MODEL_ID` | `cohere.embed-multilingual-v3` | Cohere model for KB query embeddings |
| `OPENSEARCH_URL` | `http://localhost:9200` | OpenSearch endpoint (index from embedding service) |
| `OPENSEARCH_INDEX_NAME` | `nam-documents` | k-NN index name |
| `KB_SEARCH_TOP_K` | `5` | Default chunks retrieved per search |

Aliases: `STRANDS_MODEL_ID`, `AWS_REGION`. Deployed containers get Bedrock chat vars from Terraform (`infra/agent_runtime.tf`). Index documents first via [embedding package](../embedding/README.md).

## Local usage

Canonical walkthrough: [README — Local development quickstart](../../README.md#local-development-quickstart). Makefile wrappers below assume **repo root**.

| Goal | Make | Raw (`uv`) |
|------|------|------------|
| Simple interactive CLI | `make cli` | `cd src/agents && uv run python -m cmd.main` |
| KB interactive CLI | `make kb-cli` | `cd src/agents && uv run python -m cmd.kb_main` |
| Simple HTTP `:8080` | `make http` | `cd src/agents && uv run python -m runtimes.simple` |
| KB HTTP `:8080` | `make kb-http` | `cd src/agents && uv run python -m runtimes.knowledge_base` |
| Health check | `make ping` | `curl -sf http://localhost:8080/ping` |
| Invoke HTTP | `make invoke-local PROMPT="..."` | see curl examples below |

### Interactive CLI

```bash
uv run python -m cmd.main
```

### AgentCore HTTP server

Same contract as production, port `8080`:

```bash
uv run python -m runtimes.simple
```

```bash
curl http://localhost:8080/ping
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is machine learning?"}'
```

### Knowledge-base agent

Uses the `search_knowledge_base` tool to retrieve chunks from OpenSearch (same index as [embedding service](../embedding/README.md)). **Prerequisites:** OpenSearch running (`make up`) and at least one document indexed — see [embedding quickstart](../../README.md#path-a--index-documents-then-test-the-kb-agent).

```bash
# Interactive CLI
uv run python -m cmd.kb_main

# HTTP runtime (same /invocations contract, port 8080)
uv run python -m runtimes.knowledge_base
```

```bash
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Summarize what our policy documents say about remote work."}'
```

### Test deployed AgentCore Runtime

Requires `bedrock-agentcore:InvokeAgentRuntime` — see [invoke policy](../../README.md#test-the-deployed-agent).

```bash
# from repo root
make test-runtime-kb          # KB runtime (default)
make test-runtime-simple      # simple runtime

# or manually from src/agents/
export AGENT_RUNTIME_ARN="$(terraform -chdir=../../infra/kb output -raw agent_runtime_arn)"
uv run python -m cmd.test_runtime
uv run python -m cmd.test_runtime --region ap-southeast-1 "$AGENT_RUNTIME_ARN"
```

One-shot smoke test: `make invoke-kb PROMPT="..."` / `make invoke-simple PROMPT="..."` ([../../README.md#test-the-deployed-agent](../../README.md#test-the-deployed-agent)).

### Use in code

```python
from core.agent import create_agent

agent = create_agent()
result = agent("Explain quantum computing in one paragraph.")
print(result.message)
```

## AgentCore Runtime

Production container entry point is selected at **image build time** via `RUNTIME_MODULE` (`runtimes.simple` or `runtimes.knowledge_base`). Local: `make http` / `make kb-http`. Deploy: `make deploy-simple` / `make deploy-kb`.

| | |
|---|---|
| Request | `{"prompt": "..."}` |
| Response | `{"result": "..."}` or `{"error": "..."}` |
| Health | `GET /ping` |

**Container requirements:** `linux/arm64`, port `8080`, non-root user, endpoints above.

Local image build:

```bash
docker buildx build --platform linux/arm64 \
  --build-arg RUNTIME_MODULE=runtimes.knowledge_base \
  -t nam-agents-kb:local --load .
docker run --platform linux/arm64 -p 8080:8080 \
  -e AWS_REGION=ap-southeast-1 \
  -e BEDROCK_MODEL_ID=apac.anthropic.claude-sonnet-4-20250514-v1:0 \
  -e EMBEDDING_MODEL_ID=cohere.embed-multilingual-v3 \
  -e OPENSEARCH_URL=http://host.docker.internal:9200 \
  -e OPENSEARCH_INDEX_NAME=nam-documents \
  nam-agents-kb:local
```

Deploy to AWS: [../../README.md#deploy-agents](../../README.md#deploy-agents) — `make deploy-simple` / `make deploy-kb`. KB stack: set `opensearch_url` in `infra/kb/terraform.tfvars`.

## Extending the agent

- **System prompt** — edit `SYSTEM_PROMPT` in `core/agent.py`
- **Tools / model** — extend `create_agent()` in `core/agent.py`; keep `runtimes/` thin
- **New agent** — add `core/<name>_agent.py` + `runtimes/<name>.py`; add a stack under `infra/<slug>/` calling `modules/agent-runtime`

## Dependencies

`strands-agents`, `pydantic-settings`, `bedrock-agentcore` — managed with [uv](https://docs.astral.sh/uv/) (`uv.lock`).
