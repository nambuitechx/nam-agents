resource "aws_bedrockagentcore_agent_runtime" "this" {
  agent_runtime_name = local.agent_runtime_name
  description        = var.runtime_description
  role_arn           = aws_iam_role.agent_runtime.arn

  protocol_configuration {
    server_protocol = "HTTP"
  }

  environment_variables = local.base_environment_variables

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
