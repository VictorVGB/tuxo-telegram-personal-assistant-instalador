"""Configuração do Tuxo.

Os mesmos campos podem vir de duas fontes:
  - Em produção: de um segredo JSON no AWS Secrets Manager (SECRETS_MANAGER_SECRET_ID).
  - Em dev local: das variáveis de ambiente (.env.local).
Secrets Manager tem prioridade quando configurado.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache

from pydantic import BaseModel, Field

from .logger import get_logger

log = get_logger(__name__)


class Config(BaseModel):
    port: int = 8080
    timezone: str = "America/Sao_Paulo"
    bot_name: str = "Tuxo"

    telegram_bot_token: str = Field(min_length=1)
    owner_telegram_chat_id: str = Field(min_length=1)
    # Token secreto opcional enviado pelo Telegram no header X-Telegram-Bot-Api-Secret-Token
    telegram_webhook_secret: str = ""

    anthropic_api_key: str = Field(min_length=1)

    vault_repo_url: str = Field(min_length=1)
    github_token: str = Field(min_length=1)
    vault_local_path: str = "./.vault-cache"


def _from_env() -> dict[str, object]:
    raw = {
        "port": os.getenv("PORT"),
        "timezone": os.getenv("TZ"),
        "bot_name": os.getenv("BOT_NAME"),
        "telegram_bot_token": os.getenv("TELEGRAM_BOT_TOKEN"),
        "owner_telegram_chat_id": os.getenv("OWNER_TELEGRAM_CHAT_ID"),
        "telegram_webhook_secret": os.getenv("TELEGRAM_WEBHOOK_SECRET", ""),
        "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY"),
        "vault_repo_url": os.getenv("VAULT_REPO_URL"),
        "github_token": os.getenv("GITHUB_TOKEN"),
        "vault_local_path": os.getenv("VAULT_LOCAL_PATH"),
    }
    return {k: v for k, v in raw.items() if v is not None}


def _from_secrets_manager(secret_id: str) -> dict[str, object]:
    import boto3

    client = boto3.client("secretsmanager", region_name=os.getenv("AWS_REGION", "us-east-1"))
    resp = client.get_secret_value(SecretId=secret_id)
    secret_string = resp.get("SecretString")
    if not secret_string:
        raise RuntimeError(f"Segredo {secret_id} não contém SecretString")
    log.info("Segredos carregados do Secrets Manager: %s", secret_id)
    return json.loads(secret_string)


@lru_cache(maxsize=1)
def load_config() -> Config:
    values = _from_env()
    secret_id = os.getenv("SECRETS_MANAGER_SECRET_ID")
    if secret_id:
        values = {**values, **_from_secrets_manager(secret_id)}
    return Config(**values)
