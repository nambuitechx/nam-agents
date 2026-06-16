output "name_suffix" {
  description = "Unique suffix used in generated resource names"
  value       = local.name_suffix
}

output "agent_runtime_name" {
  description = "AgentCore runtime name (for deploy-image.sh and invoke-runtime.sh)"
  value       = local.agent_runtime_name
}

output "ecr_repository_url" {
  description = "ECR repository URL — push the agent image here"
  value       = aws_ecr_repository.agent.repository_url
}

output "ecr_repository_name" {
  description = "ECR repository name"
  value       = aws_ecr_repository.agent.name
}

output "agent_runtime_arn" {
  description = "AgentCore Runtime ARN — use with bedrock-agentcore:InvokeAgentRuntime"
  value       = aws_bedrockagentcore_agent_runtime.general.agent_runtime_arn
}

output "agent_runtime_id" {
  description = "AgentCore Runtime ID"
  value       = aws_bedrockagentcore_agent_runtime.general.agent_runtime_id
}

output "agent_runtime_execution_role_arn" {
  description = "IAM role assumed by the AgentCore Runtime"
  value       = aws_iam_role.agent_runtime.arn
}

output "invoke_agent_runtime_policy_arn" {
  description = "IAM policy to attach to callers (Lambda, ECS, etc.)"
  value       = aws_iam_policy.invoke_agent_runtime.arn
}

output "deploy_image_command" {
  description = "Build and push the agent container, then update the runtime (run from any directory)"
  value       = "cd ${abspath("${path.root}/..")} && AGENT_RUNTIME_NAME=${local.agent_runtime_name} ./scripts/deploy-image.sh ${var.region} ${aws_ecr_repository.agent.repository_url} ${var.image_tag}"
}
