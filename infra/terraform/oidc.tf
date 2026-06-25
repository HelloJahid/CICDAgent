# Keyless GitHub -> AWS authentication (the security centrepiece).
#
# Instead of storing AWS keys in GitHub, we register GitHub as an OpenID Connect
# (OIDC) identity provider in this account and create a role it may assume. Each
# workflow run receives a short-lived, signed token; AWS verifies it against the
# provider and issues temporary credentials for the role. No long-lived secrets
# live in GitHub at all.

locals {
  # The only repository allowed to assume the pipeline role.
  github_repo = "HelloJahid/CICDAgent"
}

# Read GitHub's OIDC TLS certificate chain so we can pin the thumbprint
# dynamically (the last cert in the chain is the root CA) rather than
# hard-coding a value that could rotate.
data "tls_certificate" "github" {
  url = "https://token.actions.githubusercontent.com/.well-known/openid-configuration"
}

# Register GitHub Actions as a trusted identity provider in this AWS account.
resource "aws_iam_openid_connect_provider" "github" {
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
  thumbprint_list = [
    data.tls_certificate.github.certificates[length(data.tls_certificate.github.certificates) - 1].sha1_fingerprint
  ]
}

# --- Trust policy: WHO may assume the pipeline role ---
# Only GitHub's OIDC provider, only the sts audience, and only tokens whose
# subject is our repository. The repo condition is what stops any other repo
# (or fork) from assuming this role.
data "aws_iam_policy_document" "pipeline_assume" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${local.github_repo}:*"]
    }
  }
}

resource "aws_iam_role" "pipeline" {
  name               = "${var.project_name}-github-actions"
  assume_role_policy = data.aws_iam_policy_document.pipeline_assume.json
}

# --- Permissions: WHAT the pipeline may do (least privilege for a deploy) ---
data "aws_iam_policy_document" "pipeline_permissions" {
  # ECR login token. This action cannot be scoped to a single repo, so it must
  # be granted on "*"; it only returns a temporary docker login.
  statement {
    sid       = "EcrAuth"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }

  # Push and pull image layers, scoped to our repository only.
  statement {
    sid = "EcrPushPull"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:GetDownloadUrlForLayer",
      "ecr:BatchGetImage",
      "ecr:InitiateLayerUpload",
      "ecr:UploadLayerPart",
      "ecr:CompleteLayerUpload",
      "ecr:PutImage",
    ]
    resources = [aws_ecr_repository.app.arn]
  }

  # Update the Lambda image and manage versions/alias for deploys (including the
  # canary in Phase 5), scoped to our function and its qualified ARNs.
  statement {
    sid = "LambdaDeploy"
    actions = [
      "lambda:GetFunction",
      "lambda:UpdateFunctionCode",
      "lambda:PublishVersion",
      "lambda:GetAlias",
      "lambda:CreateAlias",
      "lambda:UpdateAlias",
    ]
    # Constructed ARN (not a reference to the resource) so this policy is valid
    # even before the Lambda exists - the role is simply allowed to act on the
    # function ARN that will appear after the bootstrap.
    resources = [
      "arn:aws:lambda:${var.aws_region}:${data.aws_caller_identity.current.account_id}:function:${var.project_name}",
      "arn:aws:lambda:${var.aws_region}:${data.aws_caller_identity.current.account_id}:function:${var.project_name}:*",
    ]
  }
}

resource "aws_iam_role_policy" "pipeline" {
  name   = "${var.project_name}-pipeline"
  role   = aws_iam_role.pipeline.id
  policy = data.aws_iam_policy_document.pipeline_permissions.json
}

# The role ARN the GitHub Actions workflows assume. Store this in GitHub later.
output "pipeline_role_arn" {
  description = "IAM role ARN that GitHub Actions assumes via OIDC (store in GitHub)."
  value       = aws_iam_role.pipeline.arn
}
