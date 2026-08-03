variable "project_name" {
  description = "Name assigned to the requested EC2 instance."
  type        = string

  validation {
    condition = (
      length(var.project_name) >= 3 &&
      length(var.project_name) <= 30 &&
      can(regex("^[a-z0-9-]+$", var.project_name))
    )

    error_message = <<-EOT
      The project name must contain 3-30 lowercase letters,
      numbers, or hyphens.
    EOT
  }
}