provider "aws" {
  region = var.region

  default_tags {
    tags = var.tags
  }
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

resource "random_id" "suffix" {
  byte_length = 4
}

locals {
  name_suffix = coalesce(var.name_suffix, random_id.suffix.hex)

  name_prefix = "${replace(var.project_name, "-", "_")}_${local.name_suffix}"

  agent_runtime_name = coalesce(
    var.agent_runtime_name,
    "${local.name_prefix}_general",
  )

  ecr_repository_name = coalesce(
    var.ecr_repository_name,
    "${replace(var.project_name, "_", "-")}-${local.name_suffix}",
  )
}
