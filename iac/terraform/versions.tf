# Terraform 版本与 Provider —— deployment-and-ops D1
# 区域 ap-northeast-1（P0 决策）。后端 state 暂用本地，上线前切 S3+DynamoDB 锁。

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # 上线前启用远程 state（取消注释并 terraform init -migrate-state）：
  # backend "s3" {
  #   bucket         = "surf-forecast-tfstate-153705321444-apne1"
  #   key            = "deployment-and-ops/terraform.tfstate"
  #   region         = "ap-northeast-1"
  #   dynamodb_table = "surf-forecast-tflock"
  #   encrypt        = true
  # }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project   = "surf-forecast"
      ManagedBy = "terraform"
      Env       = var.env
    }
  }
}
