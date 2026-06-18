variable "region" {
  description = "AWS region for AgentCore Runtime and Bedrock"
  type        = string
  default     = "ap-southeast-1"
}

variable "project_name" {
  description = "Project prefix for resource names"
  type        = string
  default     = "nam_agents"
}

variable "name_suffix" {
  description = "Short unique suffix shared across runtimes (auto-generated if null)"
  type        = string
  default     = null
}

variable "agent_runtime_name" {
  description = "AgentCore runtime name override"
  type        = string
  default     = null
}

variable "ecr_repository_name" {
  description = "ECR repository name override"
  type        = string
  default     = null
}

variable "image_tag" {
  description = "Container image tag"
  type        = string
  default     = "latest"
}

variable "bedrock_model_id" {
  description = "Bedrock chat model or inference profile ID"
  type        = string
  default     = "apac.anthropic.claude-sonnet-4-20250514-v1:0"
}

variable "bedrock_temperature" {
  description = "Optional model temperature"
  type        = string
  default     = ""
}

variable "bedrock_max_tokens" {
  description = "Optional max output tokens"
  type        = string
  default     = ""
}

variable "idle_runtime_session_timeout_seconds" {
  type    = number
  default = 900
}

variable "max_lifetime_seconds" {
  type    = number
  default = 28800
}

variable "tags" {
  type = map(string)
  default = {
    Project = "nam-agents"
    Runtime = "simple"
  }
}
