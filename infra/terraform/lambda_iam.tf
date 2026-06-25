# The Lambda's RUNTIME identity and its logs.
#
# A Lambda function runs "as" an IAM role. That role defines exactly which AWS
# APIs the function may call. We grant the bare minimum: write logs, and invoke
# our Bedrock model. Nothing else. That is least privilege.

# Who we are (account id), used to scope ARNs below without hard-coding.
data "aws_caller_identity" "current" {}

# --- Trust policy: WHO may assume this role ---
# Only the Lambda service is allowed to assume it.
data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda_exec" {
  name               = "${var.project_name}-lambda-exec"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

# --- Permission 1: write logs to CloudWatch ---
# AWS provides a managed policy for exactly this; we attach it rather than
# re-writing it ourselves.
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# --- Permission 2: call Bedrock, scoped tightly ---
# Allow only InvokeModel (the action the Converse API uses), and only on Claude
# foundation models plus this account's inference profiles - not bedrock:* on *.
data "aws_iam_policy_document" "bedrock_invoke" {
  statement {
    sid = "InvokeClaude"
    actions = [
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream",
    ]
    resources = [
      "arn:aws:bedrock:*::foundation-model/anthropic.claude-*",
      "arn:aws:bedrock:*:${data.aws_caller_identity.current.account_id}:inference-profile/*",
    ]
  }
}

resource "aws_iam_role_policy" "bedrock_invoke" {
  name   = "${var.project_name}-bedrock-invoke"
  role   = aws_iam_role.lambda_exec.id
  policy = data.aws_iam_policy_document.bedrock_invoke.json
}

# --- Logs ---
# Declare the log group ourselves so we control retention (cost). If we let
# Lambda auto-create it, logs would be kept forever by default.
resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${var.project_name}"
  retention_in_days = 14
}
