variable "environment" {
  type        = string
  description = "Environment name"

  validation {
    condition     = contains(["dev", "stage", "prod"], var.environment)
    error_message = "Must be dev, stage, or prod."
  }
}

variable "project_name" {
  type        = string
  description = "Project name used for resource naming and tagging"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,30}$", var.project_name))
    error_message = "Must be lowercase alphanumeric with hyphens, 2-31 characters."
  }
}

variable "tags" {
  type        = map(string)
  default     = {}
  description = "Additional tags to apply to all resources"
}
