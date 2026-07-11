# Reference only, non-deploying architecture example.
# No Azure resources are provisioned by this repository.

variable "environment" {
  description = "Reference environment name: dev, test, or prod."
  type        = string
  default     = "dev"
}

variable "region" {
  description = "Reference Azure region placeholder."
  type        = string
  default     = "uksouth"
}
