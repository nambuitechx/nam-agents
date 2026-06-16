# nam-agents

General-purpose AI agents built with the [Strands Agents SDK](https://strandsagents.com/), deployed to [Amazon Bedrock AgentCore Runtime](https://docs.aws.amazon.com/bedrock-agentcore/) using Terraform — no AgentCore CLI required.

## Project structure

```
nam-agents/
├── infra/                 # Terraform — ECR, IAM, AgentCore Runtime
├── scripts/               # Build, push, and invoke helpers
│   ├── deploy-image.sh    # Build ARM64 image, push to ECR, update runtime
│   └── invoke-runtime.sh  # Test a deployed runtime from the CLI
└── src/agents/            # Python agent package (see src/agents/README.md)
    └── test_runtime.py    # Interactive CLI against a deployed runtime
```

## Prerequisites

| Tool | Purpose |
|------|---------|
| Python 3.12+ and [uv](https://docs.astral.sh/uv/) | Local agent development |
| [Terraform](https://www.terraform.io/) >= 1.5 | Provision AWS resources |
| [Docker](https://www.docker.com/) with buildx | ARM64 image builds (deploy + first `terraform apply`) |
| AWS CLI | ECR login, runtime invoke, bootstrap image push |
| AWS account | Bedrock model access + Bedrock AgentCore enabled in your region |

Configure credentials once: `aws configure` or AWS SSO.

Remote state is stored in S3 — backend config lives in `infra/versions.tf`.

---

## Deploy agents

Deployment is **two steps**: provision AWS infrastructure with Terraform, then build and push the agent container.

### Step 1 — Configure

```bash
cp infra/terraform.tfvars.example infra/terraform.tfvars
```

Edit `infra/terraform.tfvars` as needed:

| Variable | Purpose |
|----------|---------|
| `region` | AWS region for ECR, AgentCore, and Bedrock |
| `bedrock_model_id` | Model ID injected into the runtime container |
| `image_tag` | Container tag (default `latest`) |
| `tags` | Applied to all AWS resources |

Resource names (ECR repo, runtime, IAM roles) get a **unique suffix** per stack via `random_id`. Pin `name_suffix` in `terraform.tfvars` if you need stable names across re-deploys.

### Step 2 — Provision infrastructure

```bash
cd infra
terraform init
terraform apply
```

**First apply requires Docker and AWS CLI** — Terraform pushes a placeholder Alpine image to ECR so the AgentCore runtime can be created before the real agent image exists.

This creates:

- ECR repository
- IAM execution role (ECR pull, CloudWatch Logs, Bedrock invoke)
- AgentCore runtime (`aws_bedrockagentcore_agent_runtime`)
- IAM policy for callers (`bedrock-agentcore:InvokeAgentRuntime`)

Bedrock settings (`BEDROCK_MODEL_ID`, `BEDROCK_REGION`, etc.) are injected into the runtime by Terraform — see `infra/agent_runtime.tf`.

### Step 3 — Push the agent image

From the **repo root** (recommended):

```bash
eval "$(terraform -chdir=infra output -raw deploy_image_command)"
```

This runs `scripts/deploy-image.sh`, which:

1. Builds the ARM64 image from `src/agents/`
2. Pushes it to your ECR repository
3. Calls `bedrock-agentcore-control update-agent-runtime` so AgentCore pulls the new image

**After pulling infra changes** (or if `eval` fails with a bad script path), refresh Terraform outputs once:

```bash
terraform -chdir=infra apply
```

No resource changes are expected — this updates stored outputs such as `deploy_image_command`.

**Manual equivalent** (same result; replace `ap-southeast-1` with your `region` from `infra/terraform.tfvars`):

```bash
./scripts/deploy-image.sh ap-southeast-1 \
  "$(terraform -chdir=infra output -raw ecr_repository_url)" \
  latest
```

### Step 4 — Verify

Quick one-shot test (AWS CLI):

```bash
./scripts/invoke-runtime.sh "What is Amazon Bedrock AgentCore?"
```

For an interactive chat session against the live runtime, use `test_runtime.py` — see [Test the deployed agent](#test-the-deployed-agent) below.

---

## Re-deploy agent

Use this whenever you change **agent code** under `src/agents/` — Python sources, `pyproject.toml` / `uv.lock`, or `Dockerfile`. You do **not** need `terraform apply` for code-only changes.

### 1. (Optional) Test locally

```bash
cd src/agents
uv sync
uv run python main.py          # interactive CLI against Bedrock directly
uv run python runtime.py       # local AgentCore HTTP server on :8080
```

### 2. Build, push, and update the runtime

From the **repo root**:

```bash
eval "$(terraform -chdir=infra output -raw deploy_image_command)"
```

Or manually:

```bash
./scripts/deploy-image.sh ap-southeast-1 \
  "$(terraform -chdir=infra output -raw ecr_repository_url)" \
  latest
```

Docker rebuilds the image, pushes to ECR, and the script updates the existing AgentCore runtime to use the new container URI. Expect a few minutes for the runtime to pull and start the new image.

**Versioned tags** — to keep `latest` unchanged, pass a tag as the third argument and set `image_tag` in `terraform.tfvars` if Terraform should track it:

```bash
./scripts/deploy-image.sh ap-southeast-1 \
  "$(terraform -chdir=infra output -raw ecr_repository_url)" \
  v1.2.0
```

### 3. Verify the new build

```bash
./scripts/invoke-runtime.sh "Summarize what changed in this deploy."
```

Or an interactive session:

```bash
export AGENT_RUNTIME_ARN="$(terraform -chdir=infra output -raw agent_runtime_arn)"
cd src/agents && uv run python test_runtime.py
```

### When you also need Terraform

| Change | What to run |
|--------|-------------|
| Agent code only (`src/agents/`) | `eval "$(terraform -chdir=infra output -raw deploy_image_command)"` |
| Model ID, timeouts, env vars | Edit `infra/terraform.tfvars`, then `terraform -chdir=infra apply` |
| Infra (IAM, ECR, runtime settings) | `terraform -chdir=infra apply` |
| Both code and infra | `terraform -chdir=infra apply`, then deploy the image (step 2 above) |

### Image pushed but runtime update failed?

If ECR push succeeded but `update-agent-runtime` errored, point the runtime at the image without rebuilding:

```bash
aws bedrock-agentcore-control update-agent-runtime \
  --region ap-southeast-1 \
  --agent-runtime-id "$(terraform -chdir=infra output -raw agent_runtime_id)" \
  --role-arn "$(terraform -chdir=infra output -raw agent_runtime_execution_role_arn)" \
  --network-configuration "networkMode=PUBLIC" \
  --agent-runtime-artifact "containerConfiguration={containerUri=$(terraform -chdir=infra output -raw ecr_repository_url):latest}"
```

Replace `ap-southeast-1` and `:latest` if you use a different region or tag.

---

## Test the deployed agent

After deploy (Steps 2–3), you can test the live AgentCore runtime from your machine.

### Option A — Interactive chat (`test_runtime.py`)

`src/agents/test_runtime.py` is a REPL that calls the deployed runtime via **aioboto3** — same conversational UX as `main.py`, but hits AWS instead of Bedrock directly.

**Setup** (once):

```bash
cd src/agents
uv sync
```

**Run** — from `src/agents/`:

```bash
# ARN from Terraform (recommended)
export AGENT_RUNTIME_ARN="$(terraform -chdir=../../infra output -raw agent_runtime_arn)"
uv run python test_runtime.py
```

Or pass the ARN directly:

```bash
uv run python test_runtime.py arn:aws:bedrock-agentcore:ap-southeast-1:123456789012:runtime/...
```

Override region if needed (otherwise parsed from the ARN, or taken from `BEDROCK_REGION` / `.env`):

```bash
uv run python test_runtime.py --region ap-southeast-1 "$AGENT_RUNTIME_ARN"
```

Type questions at the `You:` prompt. Exit with `exit` or `quit`.

**Requirements:** your AWS credentials need `bedrock-agentcore:InvokeAgentRuntime` on the runtime ARN. Attach the policy from `terraform -chdir=infra output -raw invoke_agent_runtime_policy_arn` to your IAM user or role if invokes are denied.

### Option B — One-shot test (`invoke-runtime.sh`)

From the repo root — no Python setup required:

```bash
export AGENT_RUNTIME_ARN="$(terraform -chdir=infra output -raw agent_runtime_arn)"
./scripts/invoke-runtime.sh "What is Amazon Bedrock AgentCore?"
```

Prints the JSON response and exits.

| Tool | Best for |
|------|----------|
| `test_runtime.py` | Multi-turn chat, debugging agent behavior |
| `invoke-runtime.sh` | Quick smoke test, CI, shell scripts |

---

## Destroy agents

Teardown removes the runtime, ECR repo, and IAM resources managed by this stack.

```bash
cd infra
terraform destroy
```

Confirm the plan when prompted. Terraform deletes resources in dependency order.

### Before you destroy

1. **Detach the invoke policy** if you attached `invoke_agent_runtime_policy_arn` to users or roles outside Terraform:
   ```bash
   terraform -chdir=infra output invoke_agent_runtime_policy_arn
   ```
2. **Wait for idle sessions** — active AgentCore sessions can block deletion. Default idle timeout is 15 minutes (`idle_runtime_session_timeout_seconds` in `terraform.tfvars`).

### What is removed

| Resource | Behavior |
|----------|----------|
| AgentCore runtime | Deleted |
| ECR repository + images | Deleted (`force_delete = true`) |
| IAM role and policies | Deleted unless still attached elsewhere |
| Terraform state object in S3 | Deleted with the stack |

### What is **not** removed

- The **S3 state bucket** configured in `infra/versions.tf` — managed outside this stack
- Any **IAM policy attachments** you made manually to other principals

### Re-deploy after destroy

Run the full deploy flow again (`terraform apply` → push image). A new `random_id` suffix is generated unless you pin `name_suffix` in `terraform.tfvars`.

---

## Notes

- **Two-step deploy is required.** `terraform apply` alone does not build your agent — it only provisions AWS resources and a placeholder image. Always run `deploy-image.sh` (or the `deploy_image_command` output) before invoking the agent.
- **Re-deploy is one command.** After the first deploy, agent code changes only need `deploy_image_command` — no Terraform unless you change infra or runtime env vars.
- **ARM64 only.** AgentCore Runtime requires `linux/arm64`. `deploy-image.sh` builds with `docker buildx --platform linux/arm64`.
- **Buildx builder container.** `deploy-image.sh` creates a temporary BuildKit builder (`nam-agents-builder`) for ARM64 cross-builds and removes it when the script exits (success or failure). If you still see `buildx_buildkit_nam-agents-builder0` from an older run, remove it once with `docker buildx rm nam-agents-builder`.
- **Model access.** Ensure your AWS account has access to the Bedrock model in `bedrock_model_id` (inference profile or foundation model) in the target region.
- **Unique resource names.** Each `terraform apply` on a fresh state generates names like `nam-agents-a1b2c3d4` (ECR) and `nam_agents_a1b2c3d4_general` (runtime). This avoids name collisions when you destroy and re-deploy in the same account.
- **Config split.** Deployed runtimes read Bedrock settings from Terraform-injected env vars. Local development uses `.env` (copy from `src/agents/.env.example`) or defaults in `settings.py`.
- **No AgentCore CLI.** Image deploy uses `scripts/deploy-image.sh` calling the AWS API directly. Infrastructure is pure Terraform.
- **Caller permissions.** To invoke the runtime from your own app, Lambda, or `test_runtime.py`, attach the policy from `invoke_agent_runtime_policy_arn` to the caller's IAM user or role.

---

## Local development

For agent code and local testing, see [src/agents/README.md](src/agents/README.md).

```bash
cd src/agents
uv sync
cp .env.example .env
uv run python main.py          # interactive CLI
uv run python runtime.py       # local AgentCore HTTP server on :8080
```

---

## Architecture

```
Client (CLI / Lambda / App)
        │
        ▼ InvokeAgentRuntime
Amazon Bedrock AgentCore Runtime
        │
        ├── pulls container from ECR
        └── agent calls Bedrock models
                │
                ▼
        Strands agent (general_agent.py)
```

## Terraform outputs

| Output | Description |
|--------|-------------|
| `name_suffix` | Unique suffix used in generated resource names |
| `agent_runtime_name` | Runtime name for scripts and AWS API calls |
| `ecr_repository_url` | Push target for the agent image |
| `agent_runtime_arn` | ARN for `InvokeAgentRuntime` calls |
| `agent_runtime_id` | Runtime ID for `update-agent-runtime` |
| `agent_runtime_execution_role_arn` | Role assumed by the runtime |
| `invoke_agent_runtime_policy_arn` | Attach to Lambda/ECS callers |
| `deploy_image_command` | Ready-to-run build/push/update command (run from repo root) |

## Further reading

- [Agent package docs](src/agents/README.md)
- [Strands + AgentCore deployment guide](https://strandsagents.com/docs/user-guide/deploy/deploy_to_bedrock_agentcore/python/)
- [AgentCore Runtime without CLI](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/getting-started-custom.html)
- [Terraform: aws_bedrockagentcore_agent_runtime](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/bedrockagentcore_agent_runtime)
