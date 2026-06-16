#!/usr/bin/env bash
# Build the ARM64 agent image, push to ECR, and update the AgentCore Runtime.
#
# Usage:
#   ./scripts/deploy-image.sh [region] [ecr_repo_url] [tag]
#
# Or after terraform apply:
#   ./scripts/deploy-image.sh $(terraform -chdir=infra output -raw ecr_repository_url | xargs -I{} echo ap-southeast-1 {} latest)
#
set -euo pipefail

REGION="${1:-ap-southeast-1}"
ECR_REPO_URL="${2:?ECR repository URL required (e.g. 123456789012.dkr.ecr.ap-southeast-1.amazonaws.com/nam-agents-general)}"
IMAGE_TAG="${3:-latest}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_DIR="$(cd "$SCRIPT_DIR/../src/agents" && pwd)"
INFRA_DIR="$(cd "$SCRIPT_DIR/../infra" && pwd)"
ACCOUNT_ID="$(echo "$ECR_REPO_URL" | cut -d. -f1)"
REPO_NAME="$(basename "$ECR_REPO_URL")"
BUILDX_BUILDER="nam-agents-builder"

cleanup_buildx_builder() {
  docker buildx use default >/dev/null 2>&1 || true
  docker buildx rm "$BUILDX_BUILDER" >/dev/null 2>&1 || true
}
trap cleanup_buildx_builder EXIT

echo "==> Building ARM64 image from $AGENT_DIR"
cd "$AGENT_DIR"
uv lock
docker buildx create --use --name "$BUILDX_BUILDER" 2>/dev/null || docker buildx use "$BUILDX_BUILDER"
docker buildx build --platform linux/arm64 -t "${ECR_REPO_URL}:${IMAGE_TAG}" --load .

echo "==> Logging in to ECR ($REGION)"
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

echo "==> Pushing ${ECR_REPO_URL}:${IMAGE_TAG}"
docker push "${ECR_REPO_URL}:${IMAGE_TAG}"

RUNTIME_ID="${AGENT_RUNTIME_ID:-}"
if [[ -z "$RUNTIME_ID" ]]; then
  RUNTIME_ID="$(terraform -chdir="$INFRA_DIR" output -raw agent_runtime_id 2>/dev/null || true)"
fi

ROLE_ARN="${AGENT_RUNTIME_ROLE_ARN:-}"
if [[ -z "$ROLE_ARN" ]]; then
  ROLE_ARN="$(terraform -chdir="$INFRA_DIR" output -raw agent_runtime_execution_role_arn 2>/dev/null || true)"
fi

if [[ -z "$RUNTIME_ID" || "$RUNTIME_ID" == "None" ]]; then
  RUNTIME_NAME="${AGENT_RUNTIME_NAME:-}"
  if [[ -z "$RUNTIME_NAME" ]]; then
    RUNTIME_NAME="$(terraform -chdir="$INFRA_DIR" output -raw agent_runtime_name 2>/dev/null || true)"
  fi
  RUNTIME_NAME="${RUNTIME_NAME:-nam_agents_general}"
  RUNTIME_ID="$(aws bedrock-agentcore-control list-agent-runtimes --region "$REGION" \
    --query "agentRuntimes[?agentRuntimeName=='${RUNTIME_NAME}'].agentRuntimeId | [0]" \
    --output text 2>/dev/null || true)"
fi

if [[ -n "$RUNTIME_ID" && "$RUNTIME_ID" != "None" ]]; then
  if [[ -z "$ROLE_ARN" || "$ROLE_ARN" == "None" ]]; then
    echo "Could not resolve execution role ARN. Run 'terraform apply' in infra/ first." >&2
    exit 1
  fi
  echo "==> Updating AgentCore Runtime to use new image"
  aws bedrock-agentcore-control update-agent-runtime \
    --region "$REGION" \
    --agent-runtime-id "$RUNTIME_ID" \
    --agent-runtime-artifact "containerConfiguration={containerUri=${ECR_REPO_URL}:${IMAGE_TAG}}" \
    --role-arn "$ROLE_ARN" \
    --network-configuration "networkMode=PUBLIC"
  echo "Runtime updated: $RUNTIME_ID"
else
  echo "No AgentCore runtime found yet. Run 'terraform apply' in infra/ first, or update manually."
fi

echo "Done."
