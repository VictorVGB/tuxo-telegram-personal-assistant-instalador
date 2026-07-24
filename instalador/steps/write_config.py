"""Gera os arquivos de configuração finais a partir dos dados coletados."""

from __future__ import annotations

from pathlib import Path

from ..state import InstallerData


def _reject_newlines(value: str) -> None:
    """Reject values containing newlines or carriage returns (injection attack prevention)."""
    if "\n" in value or "\r" in value:
        raise ValueError(f"valor não pode conter quebra de linha: {value!r}")


def _hcl_escape(value: str) -> str:
    """Escape a string value for safe embedding in HCL double-quoted strings.
    
    Raises ValueError if the value contains newline or carriage return characters.
    Otherwise escapes backslashes and double quotes for HCL string literals.
    """
    _reject_newlines(value)
    # Escape backslashes first to avoid double-escaping the quote's backslash
    value = value.replace("\\", "\\\\")
    # Then escape double quotes
    value = value.replace('"', '\\"')
    return value


def render_backend_hcl(bucket: str, region: str) -> str:
    escaped_bucket = _hcl_escape(bucket)
    escaped_region = _hcl_escape(region)
    return f'bucket = "{escaped_bucket}"\nregion = "{escaped_region}"\n'


def render_tfvars(data: InstallerData) -> str:
    return (
        f'aws_region = "{_hcl_escape(data.aws_region)}"\n'
        f'project_name = "{_hcl_escape(data.project_name)}"\n'
        f'bot_name = "{_hcl_escape(data.bot_name)}"\n'
        f'telegram_bot_token = "{_hcl_escape(data.telegram_bot_token)}"\n'
        f'owner_telegram_chat_id = "{_hcl_escape(data.owner_telegram_chat_id)}"\n'
        f'anthropic_api_key = "{_hcl_escape(data.anthropic_api_key)}"\n'
        f'vault_repo_url = "{_hcl_escape(data.vault_repo_url)}"\n'
        f'github_token = "{_hcl_escape(data.github_token)}"\n'
        f'budget_limit_usd = {data.budget_limit_usd}\n'
        f'alert_email = "{_hcl_escape(data.alert_email)}"\n'
    )


def render_env_local(data: InstallerData) -> str:
    # Env files don't need quote escaping, but still need newline rejection
    _reject_newlines(data.telegram_bot_token)
    _reject_newlines(data.owner_telegram_chat_id)
    _reject_newlines(data.bot_name)
    _reject_newlines(data.anthropic_api_key)
    _reject_newlines(data.vault_repo_url)
    _reject_newlines(data.github_token)
    
    return (
        f'TELEGRAM_BOT_TOKEN={data.telegram_bot_token}\n'
        f'OWNER_TELEGRAM_CHAT_ID={data.owner_telegram_chat_id}\n'
        f'BOT_NAME={data.bot_name}\n'
        f'ANTHROPIC_API_KEY={data.anthropic_api_key}\n'
        f'VAULT_REPO_URL={data.vault_repo_url}\n'
        f'GITHUB_TOKEN={data.github_token}\n'
    )


def write_all(data: InstallerData, infra_dir: Path, env_local_path: Path) -> None:
    (infra_dir / "backend.hcl").write_text(render_backend_hcl(data.tf_state_bucket, data.aws_region), encoding="utf-8")
    (infra_dir / "terraform.tfvars").write_text(render_tfvars(data), encoding="utf-8")
    env_local_path.write_text(render_env_local(data), encoding="utf-8")


def render_resumo(data: InstallerData, ecr_url: str, ecs_cluster: str, ecs_service: str) -> str:
    return (
        f"# Resumo da instalação — {data.bot_name}\n\n"
        f"- Nome do bot: {data.bot_name}\n"
        f"- Vault (GitHub): {data.vault_repo_url}\n"
        f"- Chat ID do dono: {data.owner_telegram_chat_id}\n"
        f"- Região AWS: {data.aws_region}\n"
        f"- Cluster ECS: {ecs_cluster}\n"
        f"- Serviço ECS: {ecs_service}\n"
        f"- Repositório ECR: {ecr_url}\n"
        f"- Bucket de state do Terraform: {data.tf_state_bucket}\n\n"
        f"## Comandos úteis\n\n"
        f"Ver logs:\n"
        f"```\naws logs tail /ecs/{ecs_cluster} --follow --region {data.aws_region}\n```\n\n"
        f"Forçar novo deploy:\n"
        f"```\naws ecs update-service --cluster {ecs_cluster} --service {ecs_service} "
        f"--force-new-deployment --region {data.aws_region}\n```\n"
    )


def write_resumo(
    data: InstallerData, resumo_path: Path, ecr_url: str, ecs_cluster: str, ecs_service: str
) -> None:
    resumo_path.write_text(render_resumo(data, ecr_url, ecs_cluster, ecs_service), encoding="utf-8")
