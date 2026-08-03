terraform {
  backend "s3" {
    bucket       = "shayke-aws-platform-state"
    key          = "products/basic-ec2/terraform.tfstate"
    region       = "eu-west-1"
    encrypt      = true
    use_lockfile = true
  }
}