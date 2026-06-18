# Agent guidance — nam-agents

Instructions for AI coding assistants working in this repository.

**Keep this file small.** It holds only the guidance assistants need in-repo: where to edit, coding rules, guardrails, and a short verification checklist. For everything else — commands, deploy steps, env vars, local services — use the docs below instead of duplicating them here.

| Need | Read |
|------|------|
| Commands & workflows | `make help`, [README.md](README.md) |
| Agent package usage | [src/agents/README.md](src/agents/README.md) |
| Embedding service | [src/embedding/README.md](src/embedding/README.md) |
| Upstream deploy reference | [Strands + AgentCore guide](https://strandsagents.com/docs/user-guide/deploy/deploy_to_bedrock_agentcore/python/) |

When updating documentation:

- **README files** ([README.md](README.md), [src/agents/README.md](src/agents/README.md), package READMEs): avoid duplicating content across files — document each topic once, then **link to the canonical source** elsewhere. Prefer short summaries + references over copy-paste.
- **This file (`AGENTS.md`)**: add only what is essential for assistants editing code; link out for commands, deploy, and usage details.

## What this is

Strands Agents SDK on **Amazon Bedrock**, deployed to **Bedrock AgentCore Runtime** via **Terraform**. Image deploy uses `scripts/deploy-image.sh` — **not** the AgentCore CLI. Production container runs the **knowledge-base agent** (`runtimes.knowledge_base`). Defaults: region `ap-southeast-1`, chat model `apac.anthropic.claude-sonnet-4-20250514-v1:0`, embeddings `cohere.embed-multilingual-v3`.

```
Client → AgentCore Runtime → ECR container → KB agent → Bedrock + OpenSearch
```

HTTP contract: `POST /invocations` with `{"prompt":"..."}` → `{"result":"..."}` or `{"error":"..."}`; `GET /ping`.

## Where to edit

| Goal | Location |
|------|----------|
| System prompt, model, tools | `src/agents/core/agent.py` |
| Knowledge-base agent + OpenSearch search | `src/agents/core/kb_agent.py`, `core/knowledge_base.py` |
| KB AgentCore HTTP handler | `src/agents/runtimes/knowledge_base.py` |
| Settings / env defaults | `src/agents/configs/settings.py`, `.env.example` |
| Local / deployed REPLs | `src/agents/cmd/` |
| AgentCore HTTP handler | `src/agents/runtimes/simple.py` |
| Container & deps | `src/agents/Dockerfile`, `pyproject.toml`, `uv.lock` |
| Deployed runtime env (Bedrock, OpenSearch, embeddings) | `infra/simple/`, `infra/kb/`, `infra/modules/agent-runtime/` |
| IAM, ECR, runtime | `infra/modules/agent-runtime/` |
| Local Postgres / OpenSearch | `docker-compose.yml`, `compose/.env.example` |
| Document embedding | `src/embedding/core/`, `src/embedding/cmd/`, `src/embedding/api/` |

**Rule:** keep `cmd/` and `runtimes/` thin — parse input, call core, return JSON. Agents: call `create_agent()`. Embedding: call `EmbeddingService`.

## Python (`src/agents/`)

- **uv**, Python 3.12+. Run from `src/agents/`: `uv run python -m cmd.main`, `-m cmd.kb_main`, `-m runtimes.simple`, `-m runtimes.knowledge_base`, `-m cmd.test_runtime`.
- Match existing style: PEP 8, type hints on public APIs, `snake_case` / `PascalCase`, module docstrings.
- Absolute imports from package root (`from core.agent import create_agent`).
- Settings via `get_settings()` in `configs/settings.py` (pydantic-settings).
- New agent: `core/<name>_agent.py` + `runtimes/<name>.py` (copy `simple.py`); update `Dockerfile` / Terraform if deploying separately.

## Python (`src/embedding/`)

- Separate **uv** project. Run from `src/embedding/`: `uv run python -m cmd.cli`, `-m api.server`.
- Async-first: `aioboto3` (Bedrock Cohere), `AsyncOpenSearch`. Logic in `core/`; keep `cmd/` and `api/` thin.
- Settings via `get_settings()` in `configs/settings.py`. See [src/embedding/README.md](src/embedding/README.md) for CLI, API, and env vars.
- `document_id`: optional on embed — client UUID if provided, server-generated `uuid4` if omitted. Save the returned ID.

## Do not

- Use AgentCore CLI for deploy.
- Build x86_64 images for production (ARM64 only).
- Commit `terraform.tfvars`, `.env`, `compose/.env`, or credentials.
- Run `terraform destroy` unless explicitly asked.
- Change S3 state backend in `infra/versions.tf` without explicit request.
- Add dependencies without updating `uv.lock`.
- Over-scope: no unrelated refactors or over-abstraction.

## Before claiming done

1. `cd src/agents && uv sync` succeeds.
2. Logic changes: `make cli` or `make http` + `make invoke-local` behave sensibly.
3. Embedding changes: `cd src/embedding && uv sync`; CLI/API against local OpenSearch (`make up`) behave sensibly.
4. Infra changes: `terraform validate` in `infra/simple/` and/or `infra/kb/`.
5. Dockerfile/runtime changes: ARM64 build + `make deploy-simple` / `make deploy-kb`; KB stack needs `opensearch_url` in `infra/kb/terraform.tfvars`.
