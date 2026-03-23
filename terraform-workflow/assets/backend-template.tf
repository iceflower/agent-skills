# =============================================================================
# Remote Backend Configuration
# =============================================================================
# Choose ONE backend below based on your cloud provider.
# Run `terraform init` after configuring.

# --- AWS S3 Backend ---
# terraform {
#   backend "s3" {
#     bucket       = "${PROJECT}-terraform-state"
#     key          = "${ENVIRONMENT}/terraform.tfstate"
#     region       = "us-east-1"
#     encrypt      = true
#     use_lockfile = true  # v1.11+ native S3 locking (replaces DynamoDB)
#   }
# }

# --- Azure Storage Backend ---
# terraform {
#   backend "azurerm" {
#     resource_group_name  = "${PROJECT}-terraform-rg"
#     storage_account_name = "${PROJECT}tfstate"
#     container_name       = "tfstate"
#     key                  = "${ENVIRONMENT}.tfstate"
#   }
# }

# --- GCP Cloud Storage Backend ---
# terraform {
#   backend "gcs" {
#     bucket = "${PROJECT}-terraform-state"
#     prefix = "${ENVIRONMENT}"
#   }
# }
