terraform {
  required_version = "~> 1.14"

  required_providers {
    # Uncomment the provider you need:

    # aws = {
    #   source  = "hashicorp/aws"
    #   version = "~> 6.0"
    # }

    # azurerm = {
    #   source  = "hashicorp/azurerm"
    #   version = "~> 4.0"
    # }

    # google = {
    #   source  = "hashicorp/google"
    #   version = "~> 6.0"
    # }
  }
}

# =============================================================================
# Resources
# =============================================================================

# Use for_each over count to avoid index-based drift
# Use implicit dependencies (resource references) over depends_on
# Apply lifecycle rules for critical resources:
#   - prevent_destroy for databases and storage
#   - create_before_destroy for certificates and load balancers
