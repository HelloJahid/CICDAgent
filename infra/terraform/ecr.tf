# Amazon ECR - the private container registry for this project.
# The CD pipeline builds the image, tags it with the git SHA, and pushes it
# here; Lambda then pulls the image from here to run. This is the "shelf" the
# build artifact sits on between being built and being deployed.

resource "aws_ecr_repository" "app" {
  name = var.project_name

  # Once a tag (a git SHA) is pushed it cannot be overwritten, so a given SHA
  # always points at exactly one image - reproducible, auditable deploys.
  image_tag_mutability = "IMMUTABLE"

  # ECR scans each pushed image for known vulnerabilities. This is the "Scan"
  # stage from the reference doc, enabled at the registry with one setting.
  image_scanning_configuration {
    scan_on_push = true
  }

  # Let `terraform destroy` remove the repo even if it still holds images.
  # Convenient for a teardown-friendly demo; in production you would be careful.
  force_delete = true
}

# Cost control: keep only the most recent images so old ones do not pile up and
# accrue storage charges in the shared RMIT account.
resource "aws_ecr_lifecycle_policy" "app" {
  repository = aws_ecr_repository.app.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep only the last 10 images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 10
        }
        action = { type = "expire" }
      }
    ]
  })
}

# The repository URL the pipeline pushes to and Lambda pulls from.
output "ecr_repository_url" {
  description = "URL to push/pull the container image (used by the CD pipeline)."
  value       = aws_ecr_repository.app.repository_url
}
