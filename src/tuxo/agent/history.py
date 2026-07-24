"""Histórico de conversa em memória por chat_id."""

from __future__ import annotations

_MAX_MESSAGES = 40  # ~20 pares user/assistant


class ConversationHistory:
    def __init__(self) -> None:
        self._messages: list[dict] = []

    def get(self) -> list[dict]:
        return list(self._messages)

    def extend(self, new_messages: list[dict]) -> None:
        self._messages.extend(new_messages)
        self._trim()

    def _trim(self) -> None:
        while len(self._messages) > _MAX_MESSAGES:
            self._messages.pop(0)
        # A API exige que a primeira mensagem seja do usuário
        while self._messages and self._messages[0]["role"] != "user":
            self._messages.pop(0)
