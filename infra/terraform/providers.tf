# Configures the AWS provider - the plugin that talks to AWS on our behalf.
# Region comes from a variable so it is not hard-coded. default_tags stamps
# EVERY resource we create with these tags, which makes cost tracking and
# cleanup easy in the shared RMIT research account.

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project   = var.project_name
      ManagedBy = "terraform"
    }
  }
}
