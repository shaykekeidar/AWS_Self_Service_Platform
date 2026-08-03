provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      ManagedBy = "Terraform"
      Platform  = "aws-mini-platform"
      Product   = "basic-ec2"
    }
  }
}