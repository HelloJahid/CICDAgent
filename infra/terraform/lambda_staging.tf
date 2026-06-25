# Staging environment: a second Lambda that mirrors production.
#
# The pipeline deploys a new image HERE first (automatically), proves it with a
# smoke test, and only then - after manual approval - deploys the same image to
# production. It shares the execution role with production (same permissions)
# but has its own function, URL, and log group.

resource "aws_cloudwatch_log_group" "lambda_staging" {
  name              = "/aws/lambda/${var.project_name}-staging"
  retention_in_days = 14
}

resource "aws_lambda_function" "staging" {
  count = var.create_lambda ? 1 : 0

  function_name = "${var.project_name}-staging"
  role          = aws_iam_role.lambda_exec.arn

  package_type = "Image"
  image_uri    = "${aws_ecr_repository.app.repository_url}:${var.image_tag}"

  timeout     = 30
  memory_size = 512

  environment {
    variables = {
      BEDROCK_MODEL_ID = var.bedrock_model_id
    }
  }

  # The pipeline owns image updates for staging too.
  lifecycle {
    ignore_changes = [image_uri]
  }

  depends_on = [aws_cloudwatch_log_group.lambda_staging]
}

resource "aws_lambda_function_url" "staging" {
  count = var.create_lambda ? 1 : 0

  function_name      = aws_lambda_function.staging[0].function_name
  authorization_type = "NONE"
}

output "staging_function_url" {
  description = "Public HTTPS endpoint for the staging environment."
  value       = var.create_lambda ? aws_lambda_function_url.staging[0].function_url : null
}
