# Version pins for Terraform itself and the providers it uses.
# Pinning makes the infrastructure reproducible: anyone running this gets the
# same provider behaviour, the same way requirements.txt pins our Python deps.

terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0" # latest major line (6.x); verified current
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0" # used only to read GitHub's OIDC certificate thumbprint
    }
  }
}
