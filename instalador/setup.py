"""Wizard principal do instalador do Tuxo."""

from __future__ import annotations

import argparse
import platform
import subprocess
import sys
from pathlib import Path

from .state import STATE_FILE, InstallerState, load, save
from .steps import aws_bootstrap, bot_identity, claude_auth, deploy, github, prereqs, telegram, verify, write_config

STATE_PATH = STATE_FILE
PROJECT_ROOT = Path(__file__).parent.parent
INFRA_DIR = Path(__file__).parent / "infra"
ENV_LOCAL_PATH = PROJECT_ROOT / ".env.local"
RESUMO_PATH = Path(__file__).parent / "RESUMO.md"

STEP_ORDER = [
    "bot_identity",
    "prereqs",
    "telegram",
    "github",
    "aws_credentials",
    "aws_bucket",
    "claude_auth",
    "write_config",
    "terraform_apply",
    "deploy_image",
    "verify",
    "resumo",
]


def _ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value or default


def _run_with_retry(step_name: str, action) -> bool:
    """Executa `action`; em erro, oferece tentar de novo / pular / abortar.

    Retorna True se o passo deve ser marcado como concluído.
    """
    while True:
        try:
            action()
            return True
        except Exception as exc:  # noqa: BLE001 — decisão fica com quem está instalando, não crash
            print(f"\nErro em '{step_name}': {exc}")
            choice = input("Tentar de novo (r) / pular (s) / abortar (a)? [r]: ").strip().lower() or "r"
            if choice == "s":
                return False
            if choice == "a":
                raise SystemExit(1)


def _step_bot_identity(state: InstallerState) -> None:
    def action():
        state.data.bot_name = _ask("Qual nome você quer dar pro seu assistente?", state.data.bot_name or "Tuxo")
        slug = bot_identity.slugify(state.data.bot_name)
        confirmed = _ask("Nome técnico dos recursos AWS (pode editar)", slug)
        if not bot_identity.is_valid_slug(confirmed):
            raise ValueError(f"'{confirmed}' não é um slug válido (use minúsculas, números e hífen)")
        state.data.project_name = confirmed

    if _run_with_retry("bot_identity", action):
        state.mark_done("bot_identity")
        save(state, STATE_PATH)


def _step_prereqs(state: InstallerState) -> None:
    def action():
        os_name = {"Darwin": "darwin", "Windows": "windows", "Linux": "linux"}[platform.system()]
        checks = prereqs.check_tools(os_name)
        for check in checks:
            if not check.found:
                raise RuntimeError(f"'{check.name}' não encontrado. Instale em: {check.install_url}")
            if not check.version_ok:
                raise RuntimeError(
                    f"'{check.name}' está desatualizado. Instale a versão mais recente: {check.install_url}"
                )

    if _run_with_retry("prereqs", action):
        state.mark_done("prereqs")
        save(state, STATE_PATH)


def _step_telegram(state: InstallerState) -> None:
    def action():
        print(f"\nCrie seu bot conversando com {telegram.BOTFATHER_URL} e use /newbot.")
        token = _ask("Cole aqui o token do bot")
        if not telegram.validate_bot_token(token):
            raise ValueError("Token inválido — a Telegram API rejeitou o getMe")
        state.data.telegram_bot_token = token
        input("\nAgora manda qualquer mensagem pro seu bot novo no Telegram e aperta Enter aqui...")
        chat_id = telegram.discover_chat_id(token)
        if not chat_id:
            raise ValueError("Não encontrei nenhuma mensagem — manda uma mensagem pro bot e tenta de novo")
        state.data.owner_telegram_chat_id = chat_id

    if _run_with_retry("telegram", action):
        state.mark_done("telegram")
        save(state, STATE_PATH)


def _step_github(state: InstallerState) -> None:
    def action():
        if not github.is_authenticated():
            print("\nFaça login no GitHub CLI:")
            subprocess.run(["gh", "auth", "login"], check=True)
        github.ensure_repo_scope()
        repo_name = _ask("Nome do repositório do vault", f"{state.data.project_name}-vault")
        github.create_private_repo(repo_name)
        state.data.vault_repo_url = github.repo_url(repo_name)
        state.data.github_token = github.get_token()

    if _run_with_retry("github", action):
        state.mark_done("github")
        save(state, STATE_PATH)


def _step_aws_credentials(state: InstallerState) -> None:
    def action():
        state.data.aws_account_id = aws_bootstrap.get_account_id()
        state.data.aws_region = _ask("Região AWS", state.data.aws_region or "us-east-1")
        state.data.alert_email = _ask("E-mail para alertas de orçamento", state.data.alert_email)
        budget = _ask("Limite mensal de orçamento em USD", str(state.data.budget_limit_usd or 10))
        state.data.budget_limit_usd = int(budget)

    if _run_with_retry("aws_credentials", action):
        state.mark_done("aws_credentials")
        save(state, STATE_PATH)


def _step_aws_bucket(state: InstallerState) -> None:
    def action():
        bucket = aws_bootstrap.terraform_state_bucket_name(state.data.project_name, state.data.aws_account_id)
        aws_bootstrap.ensure_state_bucket(bucket, state.data.aws_region)
        state.data.tf_state_bucket = bucket

    if _run_with_retry("aws_bucket", action):
        state.mark_done("aws_bucket")
        save(state, STATE_PATH)


def _step_claude_auth(state: InstallerState) -> None:
    def action():
        print(
            "\nGere uma API key em https://console.anthropic.com/settings/keys "
            "(cobrada por crédito, não é a assinatura Claude Pro/Max)."
        )
        key = _ask("Cole aqui sua API key (sk-ant-api03-...)")
        claude_auth.validate_api_key(key)
        state.data.anthropic_api_key = key

    if _run_with_retry("claude_auth", action):
        state.mark_done("claude_auth")
        save(state, STATE_PATH)


def _step_write_config(state: InstallerState) -> None:
    def action():
        write_config.write_all(state.data, INFRA_DIR, ENV_LOCAL_PATH)

    if _run_with_retry("write_config", action):
        state.mark_done("write_config")
        save(state, STATE_PATH)


def _step_terraform_apply(state: InstallerState) -> None:
    def action():
        deploy.terraform_init(cwd=INFRA_DIR)
        deploy.terraform_apply(cwd=INFRA_DIR)

    if _run_with_retry("terraform_apply", action):
        state.mark_done("terraform_apply")
        save(state, STATE_PATH)


def _step_deploy_image(state: InstallerState) -> None:
    def action():
        ecr_url = deploy.terraform_output("ecr_repository_url", cwd=INFRA_DIR)
        deploy.build_and_push_image(ecr_url, PROJECT_ROOT, state.data.aws_region)
        cluster = deploy.terraform_output("ecs_cluster_name", cwd=INFRA_DIR)
        service = deploy.terraform_output("ecs_service_name", cwd=INFRA_DIR)
        deploy.force_new_deployment(cluster, service, state.data.aws_region)

    if _run_with_retry("deploy_image", action):
        state.mark_done("deploy_image")
        save(state, STATE_PATH)


def _step_verify(state: InstallerState) -> None:
    def action():
        cluster = deploy.terraform_output("ecs_cluster_name", cwd=INFRA_DIR)
        service = deploy.terraform_output("ecs_service_name", cwd=INFRA_DIR)
        verify.wait_for_running(cluster, service, state.data.aws_region)
        input(
            f"\nManda uma mensagem de verdade pro seu bot ({state.data.bot_name}) no Telegram. "
            "Ele respondeu? Aperta Enter pra confirmar..."
        )

    if _run_with_retry("verify", action):
        state.mark_done("verify")
        save(state, STATE_PATH)


def _step_resumo(state: InstallerState) -> None:
    def action():
        ecr_url = deploy.terraform_output("ecr_repository_url", cwd=INFRA_DIR)
        cluster = deploy.terraform_output("ecs_cluster_name", cwd=INFRA_DIR)
        service = deploy.terraform_output("ecs_service_name", cwd=INFRA_DIR)
        write_config.write_resumo(state.data, RESUMO_PATH, ecr_url, cluster, service)
        print(f"\nTudo pronto! Resumo salvo em {RESUMO_PATH}")

    if _run_with_retry("resumo", action):
        state.mark_done("resumo")
        save(state, STATE_PATH)


_STEP_HANDLERS = {
    "bot_identity": _step_bot_identity,
    "prereqs": _step_prereqs,
    "telegram": _step_telegram,
    "github": _step_github,
    "aws_credentials": _step_aws_credentials,
    "aws_bucket": _step_aws_bucket,
    "claude_auth": _step_claude_auth,
    "write_config": _step_write_config,
    "terraform_apply": _step_terraform_apply,
    "deploy_image": _step_deploy_image,
    "verify": _step_verify,
    "resumo": _step_resumo,
}


def _dry_run(state: InstallerState) -> None:
    print("=== MODO DRY-RUN — nenhum comando externo será executado ===")
    for step in STEP_ORDER:
        status = "já concluída" if state.is_done(step) else "pendente"
        print(f"- {step}: {status}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Instalador do Tuxo")
    parser.add_argument("--dry-run", action="store_true", help="Mostra o que seria feito, sem executar nada")
    args = parser.parse_args(argv)

    state = load(STATE_PATH)

    if args.dry_run:
        _dry_run(state)
        return 0

    for step in STEP_ORDER:
        if state.is_done(step):
            continue
        _STEP_HANDLERS[step](state)

    return 0


if __name__ == "__main__":
    sys.exit(main())
