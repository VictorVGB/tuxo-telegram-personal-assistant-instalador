output "ecr_repository_url" {
  description = "URL do repositório ECR para push da imagem"
  value       = aws_ecr_repository.tuxo.repository_url
}

output "ecs_cluster_name" {
  description = "Nome do cluster ECS"
  value       = aws_ecs_cluster.tuxo.name
}

output "ecs_service_name" {
  description = "Nome do serviço ECS"
  value       = aws_ecs_service.tuxo.name
}

output "secret_arn" {
  description = "ARN do segredo no Secrets Manager"
  value       = aws_secretsmanager_secret.tuxo.arn
}
