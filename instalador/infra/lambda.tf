data "archive_file" "lambda_vault_lint" {
  type        = "zip"
  source_file = "${path.module}/lambda_vault_lint.py"
  output_path = "${path.module}/lambda_vault_lint.zip"
}

resource "aws_iam_role" "lambda_vault_lint" {
  name = "${var.project_name}-lambda-vault-lint"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRole"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "lambda_vault_lint" {
  name = "${var.project_name}-lambda-vault-lint-policy"
  role = aws_iam_role.lambda_vault_lint.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = aws_secretsmanager_secret.tuxo.arn
      },
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

resource "aws_lambda_function" "vault_lint" {
  function_name    = "${var.project_name}-vault-lint"
  filename         = data.archive_file.lambda_vault_lint.output_path
  source_code_hash = data.archive_file.lambda_vault_lint.output_base64sha256
  role             = aws_iam_role.lambda_vault_lint.arn
  handler          = "lambda_vault_lint.handler"
  runtime          = "python3.12"
  timeout          = 60

  environment {
    variables = {
      SECRET_ID = aws_secretsmanager_secret.tuxo.name
    }
  }
}

resource "aws_scheduler_schedule" "vault_lint" {
  name       = "${var.project_name}-vault-lint"
  group_name = "default"

  flexible_time_window { mode = "OFF" }
  schedule_expression          = "cron(0 12 ? * MON *)"
  schedule_expression_timezone = "America/Sao_Paulo"

  target {
    arn      = aws_lambda_function.vault_lint.arn
    role_arn = aws_iam_role.scheduler_invoke.arn
  }
}

resource "aws_iam_role" "scheduler_invoke" {
  name = "${var.project_name}-scheduler-invoke"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRole"
      Principal = { Service = "scheduler.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "scheduler_invoke" {
  name = "${var.project_name}-scheduler-invoke-policy"
  role = aws_iam_role.scheduler_invoke.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "lambda:InvokeFunction"
      Resource = [aws_lambda_function.vault_lint.arn]
    }]
  })
}
