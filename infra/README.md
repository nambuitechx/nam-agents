# Terraform layout

Each AgentCore runtime has its own stack with **separate state**:

```
infra/
├── modules/agent-runtime/   # Shared ECR + IAM + AgentCore runtime module
├── simple/                  # General Q&A agent (runtimes.simple)
└── kb/                      # Knowledge-base agent (runtimes.knowledge_base)
```

## Quick start

```bash
# Simple runtime
cp infra/simple/terraform.tfvars.example infra/simple/terraform.tfvars
make tf-init-simple && make tf-apply-simple
make deploy-simple

# Knowledge-base runtime
cp infra/kb/terraform.tfvars.example infra/kb/terraform.tfvars
# edit opensearch_url in terraform.tfvars
make tf-init-kb && make tf-apply-kb
make deploy-kb
```

## State keys (S3 backend)

| Stack | State key |
|-------|-----------|
| `simple/` | `nam-agents/regions/ap-southeast-1/dev/simple/terraform.tfstate` |
| `kb/` | `nam-agents/regions/ap-southeast-1/dev/kb/terraform.tfstate` |

## Naming

Resources are named `{project}_{suffix}_{runtime_slug}`, e.g. `nam_agents_a1b2c3d4_simple` and `nam_agents_a1b2c3d4_kb`. Pin the same `name_suffix` in both `terraform.tfvars` files to keep prefixes aligned.

## Deploy images

Each runtime has its own ECR repository. Images share `src/agents/Dockerfile` but bake a different entrypoint module via `RUNTIME_MODULE` build arg (`runtimes.simple` vs `runtimes.knowledge_base`).

```bash
make deploy-simple   # build + push + update simple runtime
make deploy-kb       # build + push + update kb runtime
```

Or run the `deploy_image_command` from `terraform output` in each stack.

## Migrating from the old single-stack layout

The previous root `infra/` stack used state key `.../dev/terraform.tfstate`. New stacks use separate keys — run `terraform init` in each folder. Existing AWS resources from the old stack are **not** imported automatically; either destroy the old stack first or import resources into the matching new stack.
