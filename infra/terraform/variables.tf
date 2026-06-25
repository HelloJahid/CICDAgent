# Input variables - the knobs for this configuration. Giving them defaults
# means `terraform` runs with no extra flags, but values can still be overridden
# per environment later (e.g. a different region or image tag).

variable "aws_region" {
  description = "AWS region to deploy into."
  type        = string
  default     = "ap-southeast-2"
}

variable "project_name" {
  description = "Project name used to name and tag resources."
  type        = string
  default     = "route-demand-assistant"
}

variable "image_tag" {
  description = "Container image tag the Lambda runs. The CD pipeline updates this per deploy; the default is the one-off bootstrap tag used to create the function the first time."
  type        = string
  default     = "bootstrap"
}

variable "bedrock_model_id" {
  description = "Bedrock model / inference-profile id the agent calls at runtime."
  type        = string
  default     = "au.anthropic.claude-haiku-4-5-20251001-v1:0"
}

variable "create_lambda" {
  description = "Whether to create the Lambda function and its URL. Kept false for the first bootstrap apply because a container Lambda needs an image in ECR first. Set true (terraform apply -var create_lambda=true) after the first image has been pushed."
  type        = bool
  default     = false
}
