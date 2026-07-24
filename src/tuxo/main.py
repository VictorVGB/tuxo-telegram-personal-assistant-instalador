"""Servidor Tuxo: polling do Telegram + health-check HTTP."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .agent.handler import handle_message
from .agent.history import ConversationHistory
from .config import load_config
from .logger import get_logger
from .queue import message_queue
from .telegram.client import TelegramClient, parse_incoming
from .vault.repo import VaultRepo

log = get_logger(__name__)


async def _polling_loop(tg: TelegramClient, cfg, vault: VaultRepo, history: ConversationHistory) -> None:
    await tg.delete_webhook()
    offset = 0
    log.info("Polling Telegram iniciado")
    while True:
        try:
            updates = await tg.get_updates(offset=offset, timeout=30)
            for update in updates:
                offset = update["update_id"] + 1
                for msg in parse_incoming(update):
                    message_queue.enqueue(lambda m=msg: handle_message(m, tg, cfg, vault, history))
        except asyncio.CancelledError:
            log.info("Polling encerrado")
            return
        except Exception:
            log.exception("Erro no polling — aguardando 5s")
            await asyncio.sleep(5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    cfg = load_config()
    tg = TelegramClient(cfg.telegram_bot_token)
    vault = VaultRepo(cfg.vault_local_path, cfg.vault_repo_url, cfg.github_token)
    history = ConversationHistory()
    await asyncio.get_event_loop().run_in_executor(None, vault.ensure_cloned)
    app.state.cfg = cfg
    app.state.vault = vault
    message_queue.start()
    poll_task = asyncio.create_task(_polling_loop(tg, cfg, vault, history))
    log.info("Tuxo no ar (porta %s)", cfg.port)
    yield
    poll_task.cancel()
    await asyncio.gather(poll_task, return_exceptions=True)


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    cfg = app.state.cfg
    return {"status": "ok", "claude_auth": "present" if cfg.anthropic_api_key else "missing"}
