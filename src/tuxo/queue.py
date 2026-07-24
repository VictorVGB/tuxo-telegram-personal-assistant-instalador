"""Fila serial baseada em asyncio.

Garante que as mensagens (e qualquer operação que escreva no vault) sejam
processadas UMA DE CADA VEZ, evitando conflitos de git no vault. Como o Xo é
mono-usuário, uma fila simples com um único worker é suficiente.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from .logger import get_logger

log = get_logger(__name__)


class SerialQueue:
    def __init__(self) -> None:
        self._queue: asyncio.Queue[Callable[[], Awaitable[None]]] = asyncio.Queue()
        self._worker: asyncio.Task[None] | None = None

    def start(self) -> None:
        if self._worker is None:
            self._worker = asyncio.create_task(self._run())

    async def _run(self) -> None:
        while True:
            task = await self._queue.get()
            try:
                await task()
            except Exception:  # noqa: BLE001 — um erro não pode derrubar a fila
                log.exception("Erro ao processar tarefa da fila")
            finally:
                self._queue.task_done()

    def enqueue(self, task: Callable[[], Awaitable[None]]) -> None:
        self._queue.put_nowait(task)


message_queue = SerialQueue()
