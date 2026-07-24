"""Guia a criação do bot no Telegram e descobre o chat_id automaticamente."""

from __future__ import annotations

import httpx

BOTFATHER_URL = "https://t.me/BotFather"


def validate_bot_token(token: str, client: httpx.Client | None = None) -> bool:
    client = client or httpx.Client(timeout=10)
    resp = client.get(f"https://api.telegram.org/bot{token}/getMe")
    return resp.status_code == 200 and resp.json().get("ok", False)


def discover_chat_id(token: str, client: httpx.Client | None = None) -> str | None:
    client = client or httpx.Client(timeout=10)
    resp = client.get(f"https://api.telegram.org/bot{token}/getUpdates")
    resp.raise_for_status()
    updates = resp.json().get("result", [])
    for update in reversed(updates):
        msg = update.get("message")
        if msg and "chat" in msg:
            return str(msg["chat"]["id"])
    return None
