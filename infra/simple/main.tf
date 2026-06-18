terraform {
  required_version = ">= 1.5.0"

  backend "s3" {
    bucket = "nam-general-203918858918-ap-southeast-1"
    key    = "nam-agents/regions/ap-southeast-1/dev/simple/terraform.tfstate"
    region = "ap-southeast-1"
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 6.28.0"
    }
    null = {
      source  = "hashicorp/null"
      version = ">= 3.2.0"
    }
    random = {
      source  = "hashicorp/random"
      version = ">= 3.6.0"
    }
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = var.tags
  }
}

module "runtime" {
  source = "../modules/agent-runtime"

  region            = var.region
  project_name      = var.project_name
  runtime_slug      = "simple"
  runtime_description = "General Q&A Strands agent on AgentCore Runtime"
  runtime_module    = "runtimes.simple"

  name_suffix         = var.name_suffix
  agent_runtime_name  = var.agent_runtime_name
  ecr_repository_name = var.ecr_repository_name
  image_tag           = var.image_tag

  bedrock_model_id    = var.bedrock_model_id
  bedrock_temperature = var.bedrock_temperature
  bedrock_max_tokens  = var.bedrock_max_tokens

  idle_runtime_session_timeout_seconds = var.idle_runtime_session_timeout_seconds
  max_lifetime_seconds                 = var.max_lifetime_seconds
  tags                                 = var.tags
}
