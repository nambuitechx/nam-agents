variable "region" {
  description = "AWS region for AgentCore Runtime and Bedrock"
  type        = string
  default     = "ap-southeast-1"
}

variable "project_name" {
  description = "Project prefix for resource names (use lowercase letters and underscores)"
  type        = string
  default     = "nam_agents"
}

variable "name_suffix" {
  description = "Short unique suffix for resource names (auto-generated if null)"
  type        = string
  default     = null
}

variable "agent_runtime_name" {
  description = "AgentCore runtime name override (underscores only; auto-generated if null)"
  type        = string
  default     = null
}

variable "ecr_repository_name" {
  description = "ECR repository name override (auto-generated if null)"
  type        = string
  default     = null
}

variable "image_tag" {
  description = "Container image tag deployed to AgentCore Runtime"
  type        = string
  default     = "latest"
}

variable "bedrock_model_id" {
  description = "Bedrock model or inference profile ID passed to the agent container"
  type        = string
  default     = "apac.anthropic.claude-sonnet-4-20250514-v1:0"
}

variable "bedrock_temperature" {
  description = "Optional model temperature (omit to use model default)"
  type        = string
  default     = ""
}

variable "bedrock_max_tokens" {
  description = "Optional max output tokens (omit to use model default)"
  type        = string
  default     = ""
}

variable "idle_runtime_session_timeout_seconds" {
  description = "Idle session timeout before the runtime scales down"
  type        = number
  default     = 900
}

variable "max_lifetime_seconds" {
  description = "Maximum lifetime of a runtime session"
  type        = number
  default     = 28800
}

variable "tags" {
  description = "Tags applied to all resources"
  type        = map(string)
  default = {
    Project = "nam-agents"
  }
}
