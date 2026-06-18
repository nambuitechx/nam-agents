resource "random_id" "suffix" {
  count       = var.name_suffix == null ? 1 : 0
  byte_length = 4
}

locals {
  name_suffix = coalesce(var.name_suffix, try(random_id.suffix[0].hex, "00000000"))

  name_prefix = "${replace(var.project_name, "-", "_")}_${local.name_suffix}_${var.runtime_slug}"

  agent_runtime_name = coalesce(
    var.agent_runtime_name,
    local.name_prefix,
  )

  ecr_repository_name = coalesce(
    var.ecr_repository_name,
    "${replace(var.project_name, "_", "-")}-${local.name_suffix}-${var.runtime_slug}",
  )

  base_environment_variables = merge(
    {
      BEDROCK_MODEL_ID = var.bedrock_model_id
      BEDROCK_REGION   = var.region
      AWS_REGION       = var.region
    },
    var.bedrock_temperature != "" ? { BEDROCK_TEMPERATURE = var.bedrock_temperature } : {},
    var.bedrock_max_tokens != "" ? { BEDROCK_MAX_TOKENS = var.bedrock_max_tokens } : {},
    var.environment_variables,
  )
}
