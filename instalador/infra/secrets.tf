resource "aws_secretsmanager_secret" "tuxo" {
  name                    = "${var.project_name}/config"
  description             = "Configuração do bot ${var.project_name}"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "tuxo" {
  secret_id = aws_secretsmanager_secret.tuxo.id
  secret_string = jsonencode({
    TELEGRAM_BOT_TOKEN     = var.telegram_bot_token
    OWNER_TELEGRAM_CHAT_ID = var.owner_telegram_chat_id
    ANTHROPIC_API_KEY      = var.anthropic_api_key
    VAULT_REPO_URL         = var.vault_repo_url
    GITHUB_TOKEN           = var.github_token
  })
}
