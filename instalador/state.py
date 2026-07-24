"""Persistência do progresso do instalador entre execuções."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

STATE_FILE = Path(__file__).parent / ".instalador-estado.json"


@dataclass
class InstallerData:
    bot_name: str = ""
    project_name: str = ""
    telegram_bot_token: str = ""
    owner_telegram_chat_id: str = ""
    github_token: str = ""
    vault_repo_url: str = ""
    aws_account_id: str = ""
    aws_region: str = "us-east-1"
    alert_email: str = ""
    budget_limit_usd: int = 10
    anthropic_api_key: str = ""
    tf_state_bucket: str = ""


@dataclass
class InstallerState:
    completed_steps: list[str] = field(default_factory=list)
    data: InstallerData = field(default_factory=InstallerData)

    def is_done(self, step: str) -> bool:
        return step in self.completed_steps

    def mark_done(self, step: str) -> None:
        if step not in self.completed_steps:
            self.completed_steps.append(step)


def load(path: Path = STATE_FILE) -> InstallerState:
    if not path.exists():
        return InstallerState()
    raw = json.loads(path.read_text(encoding="utf-8"))
    data = InstallerData(**raw.get("data", {}))
    return InstallerState(completed_steps=raw.get("completed_steps", []), data=data)


def save(state: InstallerState, path: Path = STATE_FILE) -> None:
    payload = {"completed_steps": state.completed_steps, "data": asdict(state.data)}
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
