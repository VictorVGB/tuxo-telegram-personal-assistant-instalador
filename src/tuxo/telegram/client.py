"""Integração com a Telegram Bot API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import httpx

from ..logger import get_logger

log = get_logger(__name__)

MsgType = Literal["text", "image", "document", "audio", "video", "unsupported"]

_MIME_BY_EXT = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
    "gif": "image/gif", "pdf": "application/pdf",
    "mp3": "audio/mpeg", "ogg": "audio/ogg", "mp4": "video/mp4",
}


@dataclass
class IncomingMessage:
    sender: str       # chat_id (str) — usado para responder
    message_id: str
    type: MsgType
    text: str | None = None
    media_id: str | None = None   # file_id do Telegram
    filename: str | None = None
    mime_type: str | None = None


def parse_incoming(body: dict[str, Any]) -> list[IncomingMessage]:
    """Extrai mensagens de um update do Telegram."""
    msg = body.get("message") or body.get("edited_message")
    if not msg:
        return []

    chat_id = str(msg["chat"]["id"])
    mid = str(msg["message_id"])

    if "text" in msg:
        return [IncomingMessage(chat_id, mid, "text", text=msg["text"])]

    if "document" in msg:
        doc = msg["document"]
        return [IncomingMessage(chat_id, mid, "document",
                                media_id=doc["file_id"],
                                filename=doc.get("file_name"),
                                mime_type=doc.get("mime_type"))]
    if "photo" in msg:
        photo = msg["photo"][-1]  # maior resolução
        return [IncomingMessage(chat_id, mid, "image", media_id=photo["file_id"])]

    if "audio" in msg:
        a = msg["audio"]
        return [IncomingMessage(chat_id, mid, "audio",
                                media_id=a["file_id"], mime_type=a.get("mime_type"))]

    if "voice" in msg:
        v = msg["voice"]
        return [IncomingMessage(chat_id, mid, "audio",
                                media_id=v["file_id"], mime_type=v.get("mime_type", "audio/ogg"))]

    if "video" in msg:
        v = msg["video"]
        return [IncomingMessage(chat_id, mid, "video",
                                media_id=v["file_id"], mime_type=v.get("mime_type"))]

    return [IncomingMessage(chat_id, mid, "unsupported")]


class TelegramClient:
    def __init__(self, token: str) -> None:
        self._base = f"https://api.telegram.org/bot{token}"
        self._token = token

    async def send_text(self, chat_id: str, text: str) -> None:
        from .md_to_html import md_to_html
        html = md_to_html(text)
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{self._base}/sendMessage", json={
                "chat_id": chat_id,
                "text": html[:4096],
                "parse_mode": "HTML",
            })
        if resp.status_code == 400:
            log.warning("HTML inválido no Telegram, reenviando sem formatação")
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(f"{self._base}/sendMessage", json={
                    "chat_id": chat_id,
                    "text": text[:4096],
                })
        if resp.status_code >= 400:
            log.error("Falha ao enviar mensagem Telegram (%s): %s", resp.status_code, resp.text)
            resp.raise_for_status()

    async def download_file(self, file_id: str) -> tuple[bytes, str]:
        """Baixa um arquivo pelo file_id. Retorna (bytes, mime_type)."""
        async with httpx.AsyncClient(timeout=60) as client:
            meta = (await client.get(f"{self._base}/getFile",
                                     params={"file_id": file_id})).json()
            file_path = meta["result"]["file_path"]
            ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""
            mime = _MIME_BY_EXT.get(ext, "application/octet-stream")
            content = (await client.get(
                f"https://api.telegram.org/file/bot{self._token}/{file_path}"
            )).content
        return content, mime

    async def set_webhook(self, url: str, secret_token: str = "") -> None:
        payload: dict[str, Any] = {"url": url}
        if secret_token:
            payload["secret_token"] = secret_token
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{self._base}/setWebhook", json=payload)
        resp.raise_for_status()
        log.info("Webhook Telegram registrado: %s", url)

    async def delete_webhook(self) -> None:
        async with httpx.AsyncClient(timeout=30) as client:
            await client.post(f"{self._base}/deleteWebhook")

    async def get_updates(self, offset: int = 0, timeout: int = 30) -> list[dict]:
        """Long-polling: bloqueia até `timeout` segundos aguardando updates."""
        async with httpx.AsyncClient(timeout=timeout + 5) as client:
            resp = await client.get(f"{self._base}/getUpdates", params={
                "offset": offset,
                "timeout": timeout,
                "allowed_updates": ["message"],
            })
        resp.raise_for_status()
        return resp.json().get("result", [])
