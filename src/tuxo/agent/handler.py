"""Turno do agente Tuxo via Anthropic SDK, autenticado com API key de crédito (console.anthropic.com)."""

from __future__ import annotations

import base64
import re

import anthropic

from ..config import Config
from ..logger import get_logger
from ..telegram.client import IncomingMessage, TelegramClient
from ..vault.repo import VaultRepo
from .history import ConversationHistory
from .system_prompt import build_system_prompt
from .tools import TOOLS, execute_tool

log = get_logger(__name__)

_MODEL = "claude-sonnet-4-6"


def _make_client(cfg: Config) -> anthropic.Anthropic:
    # cfg.anthropic_api_key holds a real Anthropic API key (console.anthropic.com),
    # billed via API credits — not the Pro/Max subscription OAuth token, which
    # Anthropic throttles hard for non-Claude-Code clients.
    return anthropic.Anthropic(api_key=cfg.anthropic_api_key)


async def _ingest_media(
    msg: IncomingMessage, tg: TelegramClient, cfg: Config, vault: VaultRepo,
) -> str:
    """vault-ingest: baixa mídia do Telegram, salva no vault e gera nota via visão."""
    data, mime = await tg.download_file(msg.media_id)  # type: ignore[arg-type]

    ext = mime.split("/")[-1].replace("jpeg", "jpg")
    raw_name = (msg.filename or f"media_{msg.message_id}").rsplit(".", 1)[0]
    safe_name = re.sub(r"[^\w\-]", "_", raw_name).lower()
    file_rel = f"Fontes da Verdade/{safe_name}.{ext}"

    vault.pull()
    vault.write_bytes(file_rel, data, f"vault-ingest: {safe_name}")
    log.info("vault-ingest: %s salvo", file_rel)

    note_content: str | None = None
    if mime.startswith("image/") or mime == "application/pdf":
        client = _make_client(cfg)
        if mime.startswith("image/"):
            media_block: dict = {
                "type": "image",
                "source": {"type": "base64", "media_type": mime,
                           "data": base64.standard_b64encode(data).decode()},
            }
        else:
            media_block = {
                "type": "document",
                "source": {"type": "base64", "media_type": "application/pdf",
                           "data": base64.standard_b64encode(data).decode()},
            }
        response = client.messages.create(
            model=_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": [
                media_block,
                {"type": "text", "text": (
                    "Crie uma nota Obsidian sobre o conteúdo deste arquivo.\n"
                    f"Inclua frontmatter YAML com: tags, tipo, fonte (valor: '{file_rel}').\n"
                    "Escreva em português. Seja conciso."
                )},
            ]}],
        )
        if response.content:
            note_content = response.content[0].text  # type: ignore[union-attr]

    if note_content:
        note_rel = f"Fontes da Verdade/{safe_name}.md"
        vault.write(note_rel, note_content, f"vault-ingest: nota de {safe_name}")
        vault.update_moc("Fontes da Verdade")
        return f"Salvo em `{file_rel}` e nota criada em `{note_rel}`."

    return f"Arquivo salvo em `{file_rel}`. Tipo `{mime}` não gera nota automática."


async def handle_message(
    msg: IncomingMessage, tg: TelegramClient, cfg: Config, vault: VaultRepo,
    history: ConversationHistory,
) -> None:
    """Processa UMA mensagem (já dentro da fila serial)."""
    if msg.sender != cfg.owner_telegram_chat_id:
        log.warning("Mensagem de chat não autorizado (%s) — ignorada", msg.sender)
        return

    if msg.type not in ("text", "unsupported") and msg.media_id:
        try:
            result = await _ingest_media(msg, tg, cfg, vault)
            await tg.send_text(msg.sender, result)
        except Exception:
            log.exception("vault-ingest: erro ao processar mídia")
            await tg.send_text(msg.sender, "Não consegui processar esse arquivo. Pode tentar de novo?")
        return

    if msg.type == "unsupported":
        await tg.send_text(msg.sender, "Esse tipo de mensagem ainda não é suportado.")
        return

    try:
        reply = await run_agent(msg.text or "", cfg, vault, history)
        await tg.send_text(msg.sender, reply)
    except anthropic.RateLimitError:
        log.warning("Rate limit Anthropic (429)")
        await tg.send_text(msg.sender, "Muitas requisições ao Claude agora. Tenta de novo em alguns minutos.")
    except Exception:
        log.exception("Erro no turno do agente")
        await tg.send_text(msg.sender, "Tive um problema ao processar isso. Pode tentar de novo?")


async def run_agent(
    user_text: str, cfg: Config, vault: VaultRepo, history: ConversationHistory
) -> str:
    """Executa um turno do agente Tuxo com loop de tool use e retorna o texto de resposta."""
    client = _make_client(cfg)
    system = build_system_prompt(cfg.owner_telegram_chat_id, cfg.timezone, cfg.bot_name)

    user_msg: dict = {"role": "user", "content": user_text}
    messages: list[dict] = history.get() + [user_msg]
    new_messages: list[dict] = [user_msg]

    while True:
        response = client.messages.create(
            model=_MODEL,
            max_tokens=1024,
            system=system,
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            text_blocks = [b.text for b in response.content if hasattr(b, "text")]
            reply = "\n".join(text_blocks) or "..."
            # Filtra tool_use orphans (ex: web_search server-side) que não têm tool_result par
            text_content = [b for b in response.content if getattr(b, "type", None) == "text"]
            new_messages.append({"role": "assistant", "content": text_content or reply})
            history.extend(new_messages)
            return reply

        if response.stop_reason == "tool_use":
            assistant_msg: dict = {"role": "assistant", "content": response.content}
            messages.append(assistant_msg)
            new_messages.append(assistant_msg)

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = execute_tool(block.name, block.input, vault)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(result),
                    })
            tool_msg: dict = {"role": "user", "content": tool_results}
            messages.append(tool_msg)
            new_messages.append(tool_msg)
            continue

        # stop_reason inesperado
        text_blocks = [b.text for b in response.content if hasattr(b, "text")]
        reply = "\n".join(text_blocks) or "..."
        text_content = [b for b in response.content if getattr(b, "type", None) == "text"]
        new_messages.append({"role": "assistant", "content": text_content or reply})
        history.extend(new_messages)
        return reply
