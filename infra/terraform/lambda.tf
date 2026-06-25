# The Lambda function (our container) and its public HTTPS endpoint.

resource "aws_lambda_function" "app" {
  # Switched off for the first bootstrap apply (needs an image in ECR first),
  # switched on later with -var create_lambda=true. See variables.tf.
  count = var.create_lambda ? 1 : 0

  function_name = var.project_name
  role          = aws_iam_role.lambda_exec.arn

  # Run from a container image (no runtime/handler needed - the image is
  # self-contained). The image lives in our ECR repo, tagged by var.image_tag.
  package_type = "Image"
  image_uri    = "${aws_ecr_repository.app.repository_url}:${var.image_tag}"

  # Sized for a Bedrock round-trip: enough memory, generous timeout.
  timeout     = 30
  memory_size = 512

  # Make the model configurable without rebuilding the image.
  environment {
    variables = {
      BEDROCK_MODEL_ID = var.bedrock_model_id
    }
  }

  # The CD pipeline updates the running image on every deploy
  # (`aws lambda update-function-code`). Ignore image drift here so Terraform
  # and the pipeline do not fight over which image is live.
  lifecycle {
    ignore_changes = [image_uri]
  }

  # Ensure our retention-managed log group exists before the function does.
  depends_on = [aws_cloudwatch_log_group.lambda]
}

# A Function URL: a built-in HTTPS endpoint for the function, no API Gateway.
# authorization_type = NONE makes it publicly callable - simplest for a demo.
# Trade-off: anyone with the URL can call it and each call spends Bedrock
# tokens, so treat the URL as semi-private; auth/throttling can be added later.
resource "aws_lambda_function_url" "app" {
  count = var.create_lambda ? 1 : 0

  function_name      = aws_lambda_function.app[0].function_name
  authorization_type = "NONE"
}

output "lambda_function_name" {
  description = "Name of the Lambda function (used by the CD pipeline to deploy)."
  value       = var.create_lambda ? aws_lambda_function.app[0].function_name : null
}

output "function_url" {
  description = "Public HTTPS endpoint for the service (/ping and /invocations)."
  value       = var.create_lambda ? aws_lambda_function_url.app[0].function_url : null
}
