resource "aws_ecr_repository" "agent" {
  name                 = local.ecr_repository_name
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = var.tags
}

resource "aws_ecr_lifecycle_policy" "agent" {
  repository = aws_ecr_repository.agent.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Expire untagged images after 7 days"
      selection = {
        tagStatus   = "untagged"
        countType   = "sinceImagePushed"
        countUnit   = "days"
        countNumber = 7
      }
      action = {
        type = "expire"
      }
    }]
  })
}

resource "null_resource" "bootstrap_image" {
  triggers = {
    repository_url = aws_ecr_repository.agent.repository_url
    region         = var.region
    image_tag      = var.image_tag
  }

  provisioner "local-exec" {
    command = <<-EOT
      set -euo pipefail
      REPO="${aws_ecr_repository.agent.repository_url}"
      REGION="${var.region}"
      TAG="${var.image_tag}"
      ACCOUNT="${data.aws_caller_identity.current.account_id}"

      if aws ecr describe-images --repository-name "${aws_ecr_repository.agent.name}" --image-ids imageTag="$TAG" --region "$REGION" >/dev/null 2>&1; then
        echo "Image $REPO:$TAG already exists, skipping bootstrap."
        exit 0
      fi

      echo "Pushing bootstrap placeholder image to $REPO:$TAG"
      aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$ACCOUNT.dkr.ecr.$REGION.amazonaws.com"
      docker pull --platform linux/arm64 public.ecr.aws/docker/library/alpine:3.20
      docker tag public.ecr.aws/docker/library/alpine:3.20 "$REPO:$TAG"
      docker push "$REPO:$TAG"
    EOT
  }
}
