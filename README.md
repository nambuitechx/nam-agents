# nam-agents

General-purpose AI agents built with the [Strands Agents SDK](https://strandsagents.com/), deployed to [Amazon Bedrock AgentCore Runtime](https://docs.aws.amazon.com/bedrock-agentcore/) using Terraform — no AgentCore CLI required.

## Project structure

```
nam-agents/
├── Makefile               # Convenience targets — run `make help`
├── docker-compose.yml     # Local PostgreSQL + OpenSearch
├── compose/               # Local service config (.env.example)
├── infra/                 # Terraform — one stack per runtime → [infra/README.md](infra/README.md)
│   ├── modules/agent-runtime/
│   ├── simple/            # General Q&A AgentCore runtime
│   └── kb/                # Knowledge-base AgentCore runtime
├── scripts/               # Build, push, and invoke helpers
└── src/
    ├── agents/            # Main agent package → [src/agents/README.md](src/agents/README.md)
    └── embedding/         # Document embedding → OpenSearch → [src/embedding/README.md](src/embedding/README.md)
```

## Prerequisites

| Tool | Purpose |
|------|---------|
| Python 3.12+ and [uv](https://docs.astral.sh/uv/) | Local agent development |
| [make](https://www.gnu.org/software/make/) | Convenience commands (`make help`) |
| [Docker](https://www.docker.com/) with Compose | Local PostgreSQL + OpenSearch; ARM64 image builds |
| [Terraform](https://www.terraform.io/) >= 1.5 | Provision AWS resources |
| AWS CLI | ECR login, runtime invoke, bootstrap image push |
| AWS account | Bedrock model access + Bedrock AgentCore enabled in your region |

Configure credentials once: `aws configure` or AWS SSO. Remote state is stored in S3 — see `infra/versions.tf`.

---

## Quick start

Run `make help` from the repo root for all targets.

```bash
make up                    # local Postgres + OpenSearch
make sync && make cli      # agent deps + interactive Bedrock CLI
make http                  # local AgentCore HTTP server on :8080
```

Embedding (separate uv project — see [src/embedding/README.md](src/embedding/README.md)):

```bash
make up && make embed-sync && make embed-server   # OpenSearch :9200 + API :8090
make embed FILE=sample.md                         # index a document (CLI)
```

```bash
make tf-init-kb && make tf-apply-kb   # first-time AWS provision (KB runtime)
make deploy-kb                # build ARM64 KB image, push ECR, update runtime
make invoke-kb PROMPT="Hello" # smoke test deployed KB runtime
```

For the **simple** (general Q&A) runtime: `make tf-init-simple`, `make tf-apply-simple`, `make deploy-simple`, `make invoke-simple`. See [infra/README.md](infra/README.md).

- **Agent development** (setup, env vars, `uv` commands, extending): [src/agents/README.md](src/agents/README.md)
- **Embedding service** (CLI, FastAPI, OpenSearch): [src/embedding/README.md](src/embedding/README.md)
- **AI assistant guidance** (where to edit, coding rules): [AGENTS.md](AGENTS.md)

---

## Local services (PostgreSQL + OpenSearch)

Local backing services for development. **OpenSearch** (`:9200`) is used by the [embedding package](src/embedding/README.md). Postgres is available for future use.

```bash
make up      # start Postgres (:5432) and OpenSearch (:9200)
make ps      # status
make down    # stop, keep data
make clean   # stop and wipe volumes
```

`make env` copies `compose/.env.example` → `compose/.env`. Use `localhost` from the host; connection URLs are in the example file.

---

## Deploy agents

Two steps — do not skip the image push.

### 1. Configure & provision

Each runtime has its own Terraform stack under `infra/simple/` and `infra/kb/` ([infra/README.md](infra/README.md)).

**Knowledge-base runtime:**

```bash
cp infra/kb/terraform.tfvars.example infra/kb/terraform.tfvars
# edit opensearch_url, bedrock_model_id, image_tag, tags
make tf-init-kb && make tf-apply-kb
```

**Simple (general Q&A) runtime:**

```bash
cp infra/simple/terraform.tfvars.example infra/simple/terraform.tfvars
make tf-init-simple && make tf-apply-simple
```

**First apply** needs Docker and AWS CLI — Terraform pushes a placeholder Alpine image to ECR so each runtime can be created before the real agent image exists.

Creates per stack: ECR repo, IAM execution role, AgentCore runtime, caller invoke policy. The KB stack also injects OpenSearch and embedding env vars. OpenSearch must be reachable from AgentCore (PUBLIC network mode).

Pin the same `name_suffix` in both `terraform.tfvars` files for aligned resource naming.

### 2. Push the agent image

```bash
make deploy-kb       # KB runtime (runtimes.knowledge_base)
make deploy-simple   # simple runtime (runtimes.simple)
```

Each command runs that stack's `deploy_image_command` output (build with `RUNTIME_MODULE` build arg, push to stack ECR, update runtime).

### 3. Verify

```bash
make invoke-kb PROMPT="Summarize what our indexed documents say about remote work."
make test-runtime-kb

make invoke-simple PROMPT="What is Amazon Bedrock AgentCore?"
make test-runtime-simple
```

See [Test the deployed agent](#test-the-deployed-agent) and [src/agents/README.md](src/agents/README.md) for details.

---

## Re-deploy agent

For changes under `src/agents/` only — no `terraform apply` needed.

1. (Optional) `make sync && make cli` or `make kb-cli` — see [src/agents/README.md](src/agents/README.md)
2. `make deploy-kb` and/or `make deploy-simple`
3. `make invoke-kb` / `make invoke-simple` or `make test-runtime-kb` / `make test-runtime-simple`

| Change | Action |
|--------|--------|
| Agent code only | `make deploy-kb` and/or `make deploy-simple` |
| Model ID, timeouts, runtime env | Edit stack `terraform.tfvars` → `make tf-apply-kb` / `make tf-apply-simple` |
| IAM, ECR, runtime settings | `make tf-apply-kb` / `make tf-apply-simple` |
| Code + infra | `terraform apply` in affected stack(s), then deploy |

**Versioned tags:** pass a tag to `deploy-image.sh` and set `image_tag` in the stack's `terraform.tfvars`.

**Runtime update failed after ECR push?** Use outputs from the relevant stack (`make tf-output-kb` or `make tf-output-simple`):

```bash
aws bedrock-agentcore-control update-agent-runtime \
  --region ap-southeast-1 \
  --agent-runtime-id "$(terraform -chdir=infra/kb output -raw agent_runtime_id)" \
  --role-arn "$(terraform -chdir=infra/kb output -raw agent_runtime_execution_role_arn)" \
  --network-configuration "networkMode=PUBLIC" \
  --agent-runtime-artifact "containerConfiguration={containerUri=$(terraform -chdir=infra/kb output -raw ecr_repository_url):latest}"
```

Replace region and tag if different.

---

## Test the deployed agent

| Tool | Command | Best for |
|------|---------|----------|
| One-shot KB | `make invoke-kb PROMPT="..."` | RAG smoke test |
| One-shot simple | `make invoke-simple PROMPT="..."` | General Q&A smoke test |
| Interactive KB | `make test-runtime-kb` | Multi-turn KB debugging |
| Interactive simple | `make test-runtime-simple` | Multi-turn Q&A debugging |

Requires `bedrock-agentcore:InvokeAgentRuntime`. Attach `invoke_agent_runtime_policy_arn` (from `make tf-output-kb` or `make tf-output-simple`) to your IAM principal if invokes are denied.

Manual `uv` usage and ARN options: [src/agents/README.md](src/agents/README.md#test-deployed-agentcore-runtime).

---

## Destroy agents

```bash
terraform -chdir=infra/kb destroy
terraform -chdir=infra/simple destroy
```

Before destroying: detach `invoke_agent_runtime_policy_arn` from any manually attached principals; wait for idle sessions (default 15 min).

Removes each stack's runtime, ECR, IAM resources, and state object. Re-deploy with [Deploy agents](#deploy-agents).

---

## Architecture

```
Client (CLI / Lambda / App)
        │
        ▼ InvokeAgentRuntime
Amazon Bedrock AgentCore Runtime
        │
        ├── pulls container from ECR
        └── Strands KB agent (src/agents/runtimes/knowledge_base.py) → Bedrock + OpenSearch
```

**Embedding** (local / standalone): file upload → Bedrock Cohere embeddings → OpenSearch k-NN index. Details: [src/embedding/README.md](src/embedding/README.md#architecture).

HTTP contract, container requirements, and local docker build: [src/agents/README.md](src/agents/README.md#agentcore-runtime).

---

## Terraform outputs

`make tf-output-kb` / `make tf-output-simple` or `terraform -chdir=infra/<stack> output`

| Output | Use |
|--------|-----|
| `deploy_image_command` | Build/push/update one-liner |
| `ecr_repository_url` | Image push target |
| `agent_runtime_arn` | `InvokeAgentRuntime` / `make test-runtime` |
| `agent_runtime_id` | `update-agent-runtime` |
| `agent_runtime_execution_role_arn` | Runtime IAM role |
| `invoke_agent_runtime_policy_arn` | Attach to callers |
| `name_suffix`, `agent_runtime_name` | Resource identification |

---

## Notes

- `terraform apply` alone does not build the agent — always run `make deploy` before invoking.
- ARM64 only. `deploy-image.sh` uses `docker buildx --platform linux/arm64` (temporary builder `nam-agents-builder`).
- Deployed runtimes read Bedrock settings from Terraform. Local dev uses `src/agents/.env` or `settings.py` defaults.
- Ensure Bedrock model access for `bedrock_model_id` in your region.

## Further reading

- [src/agents/README.md](src/agents/README.md) — package setup, usage, extending
- [src/embedding/README.md](src/embedding/README.md) — document embedding, CLI, FastAPI
- [AGENTS.md](AGENTS.md) — guidance for AI coding assistants
- [Strands + AgentCore deployment guide](https://strandsagents.com/docs/user-guide/deploy/deploy_to_bedrock_agentcore/python/)
- [AgentCore Runtime without CLI](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/getting-started-custom.html)
- [Terraform: aws_bedrockagentcore_agent_runtime](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/bedrockagentcore_agent_runtime)
