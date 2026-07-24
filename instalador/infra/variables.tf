variable "aws_region" {
  description = "Região AWS"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Slug técnico usado para nomear os recursos AWS (derivado do nome do bot)"
  type        = string
}

variable "bot_name" {
  description = "Nome de exibição do bot (persona no Telegram)"
  type        = string
  default     = "Tuxo"
}

variable "telegram_bot_token" {
  description = "Token do bot Telegram (@BotFather)"
  type        = string
  sensitive   = true
}

variable "owner_telegram_chat_id" {
  description = "Chat ID do dono no Telegram"
  type        = string
}

variable "anthropic_api_key" {
  description = "API key da Anthropic Console, cobrada por crédito (sk-ant-api03-...)"
  type        = string
  sensitive   = true
}

variable "vault_repo_url" {
  description = "URL do repositório do vault Obsidian"
  type        = string
}

variable "github_token" {
  description = "GitHub PAT com escopo repo para o vault"
  type        = string
  sensitive   = true
}

variable "budget_limit_usd" {
  description = "Limite mensal de custo AWS em USD para alerta"
  type        = number
  default     = 10
}

variable "alert_email" {
  description = "E-mail para receber alertas de orçamento"
  type        = string
}
