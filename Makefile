.DEFAULT_GOAL := help

AGENTS_DIR := src/agents
COMPOSE_ENV := compose/.env
COMPOSE := docker compose --env-file $(COMPOSE_ENV)
UV := cd $(AGENTS_DIR) && uv

EMBEDDING_DIR := src/embedding
EMBED_ENV := $(EMBEDDING_DIR)/.env
UV_EMBED := cd $(EMBEDDING_DIR) && uv

INFRA_SIMPLE := infra/simple
INFRA_KB := infra/kb

.PHONY: help env up down ps logs restart clean \
        sync cli kb-cli http kb-http test-runtime test-runtime-simple test-runtime-kb \
        ping invoke-local \
        embed-env embed-sync embed-cli embed-server embed-health embed-list embed embed-remove embed-upload \
        tf-init-simple tf-apply-simple tf-output-simple \
        tf-init-kb tf-apply-kb tf-output-kb \
        deploy-simple deploy-kb invoke-simple invoke-kb

help: ## Show available targets
	@grep -E '^[a-zA-Z0-9_.-]+:.*##' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

# --- Local services (PostgreSQL + OpenSearch) ---

env: $(COMPOSE_ENV) ## Create compose/.env from example if missing

$(COMPOSE_ENV):
	cp compose/.env.example $@

up: env ## Start local Postgres and OpenSearch
	$(COMPOSE) up -d

down: env ## Stop local services (keep data volumes)
	$(COMPOSE) down

ps: env ## Show service status
	$(COMPOSE) ps

logs: env ## Tail service logs
	$(COMPOSE) logs -f

restart: env ## Restart local services
	$(COMPOSE) restart

clean: env ## Stop services and remove data volumes
	$(COMPOSE) down -v

# --- Agent development ---

sync: ## Install Python dependencies (uv sync)
	$(UV) sync

cli: sync ## Interactive agent CLI (direct Bedrock)
	$(UV) run python -m cmd.main

kb-cli: sync ## Interactive knowledge-base agent CLI
	$(UV) run python -m cmd.kb_main

http: sync ## Local HTTP runtime on :8080 (simple)
	$(UV) run python -m runtimes.simple

kb-http: sync ## Knowledge-base HTTP runtime on :8080
	$(UV) run python -m runtimes.knowledge_base

ping: ## Health check local HTTP runtime
	curl -sf http://localhost:8080/ping

invoke-local: ## Smoke test local HTTP runtime (usage: make invoke-local [PROMPT="..."])
	curl -sf -X POST http://localhost:8080/invocations \
		-H "Content-Type: application/json" \
		-d '{"prompt": "$(or $(PROMPT),Hello)"}'

# --- Embedding development ---

embed-env: $(EMBED_ENV) ## Create src/embedding/.env from example if missing

$(EMBED_ENV):
	cp $(EMBEDDING_DIR)/.env.example $@

embed-sync: ## Install embedding package dependencies
	$(UV_EMBED) sync

embed-cli: embed-sync ## Embedding CLI (usage: make embed-cli ARGS="list --all")
	$(UV_EMBED) run python -m cmd.cli $(ARGS)

embed-server: embed-sync ## Embedding FastAPI server on :8090
	$(UV_EMBED) run python -m api.server

embed-health: ## Health check local embedding server
	curl -sf http://localhost:8090/health

embed-list: embed-sync ## List all indexed documents (CLI)
	$(UV_EMBED) run python -m cmd.cli list --all

embed: embed-sync ## Embed a file (usage: make embed FILE=path/to/doc.md [DOCUMENT_ID=uuid] [REPLACE=true])
	@test -n "$(FILE)" || (echo 'Usage: make embed FILE=path/to/doc.md [DOCUMENT_ID=uuid] [REPLACE=true]'; exit 1)
	$(UV_EMBED) run python -m cmd.cli embed --file "$(FILE)" \
		$(if $(DOCUMENT_ID),--document-id "$(DOCUMENT_ID)",) \
		$(if $(filter true,$(REPLACE)),--replace,)

embed-remove: embed-sync ## Remove document (usage: make embed-remove DOCUMENT_ID=uuid)
	@test -n "$(DOCUMENT_ID)" || (echo 'Usage: make embed-remove DOCUMENT_ID=uuid'; exit 1)
	$(UV_EMBED) run python -m cmd.cli remove --document-id "$(DOCUMENT_ID)"

embed-upload: ## Upload file via API (usage: make embed-upload FILE=sample.md [DOCUMENT_ID=uuid])
	@test -n "$(FILE)" || (echo 'Usage: make embed-upload FILE=path/to/doc.md [DOCUMENT_ID=uuid]'; exit 1)
	curl -sf -X POST http://localhost:8090/documents \
		$(if $(DOCUMENT_ID),-F "document_id=$(DOCUMENT_ID)",) \
		-F "file=@$(FILE)"

test-runtime: test-runtime-kb ## Interactive CLI against deployed KB runtime

test-runtime-simple: sync ## Interactive CLI against deployed simple runtime
	@AGENT_RUNTIME_ARN="$$(terraform -chdir=$(INFRA_SIMPLE) output -raw agent_runtime_arn)" \
		$(UV) run python -m cmd.test_runtime

test-runtime-kb: sync ## Interactive CLI against deployed KB runtime
	@AGENT_RUNTIME_ARN="$$(terraform -chdir=$(INFRA_KB) output -raw agent_runtime_arn)" \
		$(UV) run python -m cmd.test_runtime

# --- Deploy & infrastructure ---

tf-init-simple: ## Terraform init (simple runtime)
	terraform -chdir=$(INFRA_SIMPLE) init

tf-apply-simple: ## Terraform apply (simple runtime)
	terraform -chdir=$(INFRA_SIMPLE) apply

tf-output-simple: ## Terraform outputs (simple runtime)
	terraform -chdir=$(INFRA_SIMPLE) output

tf-init-kb: ## Terraform init (kb runtime)
	terraform -chdir=$(INFRA_KB) init

tf-apply-kb: ## Terraform apply (kb runtime)
	terraform -chdir=$(INFRA_KB) apply

tf-output-kb: ## Terraform outputs (kb runtime)
	terraform -chdir=$(INFRA_KB) output

deploy-simple: ## Build ARM64 simple image, push ECR, update runtime
	@eval "$$(terraform -chdir=$(INFRA_SIMPLE) output -raw deploy_image_command)"

deploy-kb: ## Build ARM64 KB image, push ECR, update runtime
	@eval "$$(terraform -chdir=$(INFRA_KB) output -raw deploy_image_command)"

invoke-simple: ## Invoke deployed simple runtime (usage: make invoke-simple PROMPT="...")
	RUNTIME=simple ./scripts/invoke-runtime.sh "$(or $(PROMPT),What is Amazon Bedrock AgentCore?)"

invoke-kb: ## Invoke deployed KB runtime (usage: make invoke-kb PROMPT="...")
	RUNTIME=kb ./scripts/invoke-runtime.sh "$(or $(PROMPT),Summarize our indexed documents.)"
