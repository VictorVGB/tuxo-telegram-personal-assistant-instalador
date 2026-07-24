resource "aws_ecs_cluster" "tuxo" {
  name = var.project_name

  setting {
    name  = "containerInsights"
    value = "disabled"
  }
}

resource "aws_cloudwatch_log_group" "tuxo" {
  name              = "/ecs/${var.project_name}"
  retention_in_days = 14
}

resource "aws_ecs_task_definition" "tuxo" {
  family                   = var.project_name
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name  = var.project_name
    image = "${aws_ecr_repository.tuxo.repository_url}:latest"

    environment = [
      { name = "PORT", value = "8080" },
      { name = "BOT_NAME", value = var.bot_name }
    ]

    secrets = [
      { name = "TELEGRAM_BOT_TOKEN",     valueFrom = "${aws_secretsmanager_secret.tuxo.arn}:TELEGRAM_BOT_TOKEN::" },
      { name = "OWNER_TELEGRAM_CHAT_ID", valueFrom = "${aws_secretsmanager_secret.tuxo.arn}:OWNER_TELEGRAM_CHAT_ID::" },
      { name = "ANTHROPIC_API_KEY",      valueFrom = "${aws_secretsmanager_secret.tuxo.arn}:ANTHROPIC_API_KEY::" },
      { name = "VAULT_REPO_URL",         valueFrom = "${aws_secretsmanager_secret.tuxo.arn}:VAULT_REPO_URL::" },
      { name = "GITHUB_TOKEN",           valueFrom = "${aws_secretsmanager_secret.tuxo.arn}:GITHUB_TOKEN::" },
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.tuxo.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "ecs"
      }
    }

    essential = true
  }])
}

resource "aws_ecs_service" "tuxo" {
  name            = var.project_name
  cluster         = aws_ecs_cluster.tuxo.id
  task_definition = aws_ecs_task_definition.tuxo.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = [aws_subnet.public.id]
    security_groups  = [aws_security_group.tuxo.id]
    assign_public_ip = true
  }

  deployment_minimum_healthy_percent = 0
  deployment_maximum_percent         = 100

  lifecycle {
    ignore_changes = [task_definition]
  }
}
