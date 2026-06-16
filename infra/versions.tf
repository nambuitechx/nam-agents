terraform {
  required_version = ">= 1.5.0"

  backend "s3" {
    bucket = "nam-general-203918858918-ap-southeast-1"
    key    = "nam-agents/regions/ap-southeast-1/dev/terraform.tfstate"
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
