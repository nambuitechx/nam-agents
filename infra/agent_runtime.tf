resource "aws_bedrockagentcore_agent_runtime" "general" {
  agent_runtime_name = local.agent_runtime_name
  description        = "General Q&A Strands agent on AgentCore Runtime"
  role_arn           = aws_iam_role.agent_runtime.arn

  protocol_configuration {
    server_protocol = "HTTP"
  }

  environment_variables = merge(
    {
      BEDROCK_MODEL_ID = var.bedrock_model_id
      BEDROCK_REGION   = var.region
      AWS_REGION       = var.region
    },
    var.bedrock_temperature != "" ? { BEDROCK_TEMPERATURE = var.bedrock_temperature } : {},
    var.bedrock_max_tokens != "" ? { BEDROCK_MAX_TOKENS = var.bedrock_max_tokens } : {},
  )

  agent_runtime_artifact {
    container_configuration {
      container_uri = "${aws_ecr_repository.agent.repository_url}:${var.image_tag}"
    }
  }

  network_configuration {
    network_mode = "PUBLIC"
  }

  lifecycle_configuration {
    idle_runtime_session_timeout = var.idle_runtime_session_timeout_seconds
    max_lifetime               = var.max_lifetime_seconds
  }

  depends_on = [
    aws_iam_role_policy.agent_runtime,
    null_resource.bootstrap_image,
  ]
}
