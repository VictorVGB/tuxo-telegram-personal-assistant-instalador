"""Valida a API key da Anthropic Console fornecida pela pessoa que está instalando."""

from __future__ import annotations

import httpx

_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
_MODEL = "claude-sonnet-4-6"


class ClaudeAuthError(RuntimeError):
    pass


def validate_api_key(api_key: str, client: httpx.Client | None = None) -> None:
    """Confirma que `api_key` é uma API key válida da Anthropic Console (não um token OAuth)."""
    if not api_key.startswith("sk-ant-api"):
        raise ClaudeAuthError(
            "Isso não parece uma API key da Anthropic Console — deveria começar com "
            "'sk-ant-api...'. Gere uma em https://console.anthropic.com/settings/keys"
        )

    client = client or httpx.Client(timeout=15)
    resp = client.post(
        _MESSAGES_URL,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={"model": _MODEL, "max_tokens": 1, "messages": [{"role": "user", "content": "hi"}]},
    )
    if resp.status_code == 401:
        raise ClaudeAuthError("A Anthropic rejeitou essa API key (401) — confira se copiou certo")
    if resp.status_code == 429:
        # Rate-limited, mas isso só acontece depois de autenticar — a key é válida.
        return
    if resp.status_code >= 400:
        raise ClaudeAuthError(f"Erro inesperado validando a API key: {resp.status_code} {resp.text}")
