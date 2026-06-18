#!/usr/bin/env bash
# Invoke the deployed AgentCore Runtime.
#
# Usage:
#   ./scripts/invoke-runtime.sh "What is AWS Bedrock?"
#
set -euo pipefail

PROMPT="${1:?Usage: $0 \"your question\"}"
REGION="${AWS_REGION:-ap-southeast-1}"
RUNTIME_ARN="${AGENT_RUNTIME_ARN:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNTIME="${RUNTIME:-kb}"
INFRA_DIR="${INFRA_DIR:-$(cd "$SCRIPT_DIR/../infra/$RUNTIME" && pwd)}"

if [[ -z "$RUNTIME_ARN" ]]; then
  RUNTIME_ARN="$(terraform -chdir="$INFRA_DIR" output -raw agent_runtime_arn 2>/dev/null || true)"
fi

if [[ -z "$RUNTIME_ARN" || "$RUNTIME_ARN" == "None" ]]; then
  RUNTIME_NAME="${AGENT_RUNTIME_NAME:-}"
  if [[ -z "$RUNTIME_NAME" ]]; then
    RUNTIME_NAME="$(terraform -chdir="$INFRA_DIR" output -raw agent_runtime_name 2>/dev/null || true)"
  fi
  RUNTIME_NAME="${RUNTIME_NAME:-nam_agents_general}"
  RUNTIME_ARN="$(aws bedrock-agentcore-control list-agent-runtimes --region "$REGION" \
    --query "agentRuntimes[?agentRuntimeName=='${RUNTIME_NAME}'].agentRuntimeArn | [0]" \
    --output text)"
fi

if [[ -z "$RUNTIME_ARN" || "$RUNTIME_ARN" == "None" ]]; then
  echo "Set AGENT_RUNTIME_ARN or deploy the runtime with terraform first." >&2
  exit 1
fi

SESSION_ID="$(python3 -c 'import uuid; print(uuid.uuid4().hex + uuid.uuid4().hex[:1])')"

aws bedrock-agentcore invoke-agent-runtime \
  --region "$REGION" \
  --agent-runtime-arn "$RUNTIME_ARN" \
  --runtime-session-id "$SESSION_ID" \
  --qualifier DEFAULT \
  --payload "$(python3 -c "import json,sys; print(json.dumps({'prompt': sys.argv[1]}))" "$PROMPT")" \
  --cli-binary-format raw-in-base64-out \
  output.json

python3 -c "import json; print(json.dumps(json.load(open('output.json')), indent=2))"
rm -f output.json
