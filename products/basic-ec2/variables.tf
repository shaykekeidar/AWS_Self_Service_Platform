variable "aws_region" {
  description = "AWS Region in which the EC2 product is provisioned."
  type        = string
  default     = "eu-west-1"

  validation {
    condition     = var.aws_region == "eu-west-1"
    error_message = "This lab currently supports only the eu-west-1 Region."
  }
}

variable "instance_name" {
  description = "Name assigned to the EC2 instance."
  type        = string

  validation {
    condition = (
      length(var.instance_name) >= 3 &&
      length(var.instance_name) <= 30 &&
      can(regex("^[a-z0-9]+(?:-[a-z0-9]+)*$", var.instance_name))
    )

    error_message = "The instance name must contain 3-30 lowercase letters, numbers, or hyphens, and cannot start or end with a hyphen."
  }
}