"""Gerencia o repositório Git do vault Obsidian."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse, urlunparse

import git
import yaml

from ..logger import get_logger

log = get_logger(__name__)


def _authenticated_url(repo_url: str, github_token: str) -> str:
    """Injeta o token no URL do repositório para autenticação HTTPS."""
    parsed = urlparse(repo_url)
    netloc = f"oauth2:{github_token}@{parsed.hostname}"
    return urlunparse(parsed._replace(netloc=netloc))


class VaultRepo:
    def __init__(self, local_path: str, repo_url: str, github_token: str) -> None:
        self._path = Path(local_path)
        self._url = _authenticated_url(repo_url, github_token)
        self._repo: git.Repo | None = None

    def ensure_cloned(self) -> None:
        """Clona o vault se ainda não existe, ou verifica se é um repo válido."""
        if self._path.exists() and (self._path / ".git").exists():
            log.info("Vault já clonado em %s", self._path)
            self._repo = git.Repo(self._path)
            return

        log.info("Clonando vault em %s ...", self._path)
        self._path.mkdir(parents=True, exist_ok=True)
        self._repo = git.Repo.clone_from(self._url, self._path)
        log.info("Vault clonado com sucesso")

    def _repo_checked(self) -> git.Repo:
        if self._repo is None:
            raise RuntimeError("VaultRepo.ensure_cloned() não foi chamado")
        return self._repo

    def read(self, rel_path: str) -> str | None:
        """Lê um arquivo do vault. Retorna None se não existir."""
        full = self._path / rel_path
        if not full.exists():
            return None
        return full.read_text(encoding="utf-8")

    def write(self, rel_path: str, content: str, commit_msg: str) -> None:
        """Escreve/atualiza um arquivo e faz commit+push."""
        repo = self._repo_checked()
        full = self._path / rel_path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content, encoding="utf-8")

        repo.index.add([str(full.relative_to(self._path))])
        repo.index.commit(commit_msg)
        self._push(repo)
        log.info("Vault: %s salvo e enviado", rel_path)

    def list_files(self, subfolder: str = "") -> list[str]:
        """Lista arquivos .md no vault (ou em uma subpasta)."""
        base = self._path / subfolder if subfolder else self._path
        if not base.exists():
            return []
        return [
            str(p.relative_to(self._path))
            for p in base.rglob("*.md")
            if ".git" not in p.parts
        ]

    def pull(self) -> None:
        """Faz pull com rebase para sincronizar antes de escrever."""
        repo = self._repo_checked()
        origin = repo.remotes.origin
        origin.set_url(self._url)
        origin.pull(rebase=True)
        log.debug("Vault: pull concluído")

    def write_bytes(self, rel_path: str, data: bytes, commit_msg: str) -> None:
        """Escreve um arquivo binário e faz commit+push (usado pelo vault-ingest)."""
        repo = self._repo_checked()
        full = self._path / rel_path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_bytes(data)
        repo.index.add([str(full.relative_to(self._path))])
        repo.index.commit(commit_msg)
        self._push(repo)
        log.info("Vault: %s salvo (binário)", rel_path)

    def update_moc(self, folder: str = "") -> None:
        """vault-crossref: regenera MOC.md da pasta com base nos .md existentes."""
        folder_path = self._path / folder if folder else self._path
        if not folder_path.is_dir():
            return

        notes = []
        for f in sorted(folder_path.glob("*.md")):
            if f.name == "MOC.md":
                continue
            content = f.read_text(encoding="utf-8")
            fm: dict = {}
            if content.startswith("---"):
                try:
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        fm = yaml.safe_load(parts[1]) or {}
                except Exception:
                    pass
            notes.append({
                "stem": f.stem,
                "tipo": str(fm.get("tipo", "")),
                "bairro": str(fm.get("bairro", "")),
            })

        if not notes:
            return

        groups: dict[str, list] = {}
        for note in notes:
            group = note["tipo"].split("/")[0].strip() or "Notas"
            groups.setdefault(group, []).append(note)

        folder_title = Path(folder).name.replace("-", " ").replace("_", " ").title() if folder else "Vault"
        lines = ["---", "tags: [moc]", "tipo: MOC", "---", "", f"# MOC — {folder_title}", ""]
        for group in sorted(groups):
            lines.append(f"## {group}")
            for note in sorted(groups[group], key=lambda n: n["stem"]):
                suffix = f" — {note['bairro']}" if note["bairro"] else ""
                lines.append(f"- [[{note['stem']}]]{suffix}")
            lines.append("")
        moc_content = "\n".join(lines)

        moc_path = folder_path / "MOC.md"
        if moc_path.exists() and moc_path.read_text(encoding="utf-8") == moc_content:
            return  # sem mudança, não commita

        moc_path.write_text(moc_content, encoding="utf-8")
        repo = self._repo_checked()
        repo.index.add([str(moc_path.relative_to(self._path))])
        repo.index.commit(f"chore: vault-crossref — MOC atualizado em {folder or 'raiz'}")
        self._push(repo)
        log.info("vault-crossref: MOC atualizado em %s/", folder or "raiz")

    def _push(self, repo: git.Repo) -> None:
        origin = repo.remotes.origin
        origin.set_url(self._url)
        origin.push()
