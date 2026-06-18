output "name_suffix" {
  value = module.runtime.name_suffix
}

output "runtime_slug" {
  value = module.runtime.runtime_slug
}

output "runtime_module" {
  value = module.runtime.runtime_module
}

output "agent_runtime_name" {
  value = module.runtime.agent_runtime_name
}

output "ecr_repository_url" {
  value = module.runtime.ecr_repository_url
}

output "ecr_repository_name" {
  value = module.runtime.ecr_repository_name
}

output "agent_runtime_arn" {
  value = module.runtime.agent_runtime_arn
}

output "agent_runtime_id" {
  value = module.runtime.agent_runtime_id
}

output "agent_runtime_execution_role_arn" {
  value = module.runtime.agent_runtime_execution_role_arn
}

output "invoke_agent_runtime_policy_arn" {
  value = module.runtime.invoke_agent_runtime_policy_arn
}

output "deploy_image_command" {
  value = module.runtime.deploy_image_command
}
