resource "aws_ecr_repository" "tuxo" {
  name                 = "${var.project_name}-bot"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "tuxo" {
  repository = aws_ecr_repository.tuxo.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Manter apenas as 5 imagens mais recentes"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 5
      }
      action = { type = "expire" }
    }]
  })
}
