"""Ferramentas expostas ao agente Tuxo para interagir com o vault."""

from __future__ import annotations

from pathlib import Path

from ..logger import get_logger
from ..vault.repo import VaultRepo

log = get_logger(__name__)

WEB_SEARCH_TOOL = {"type": "web_search_20250305", "name": "web_search"}

TOOLS = [
    WEB_SEARCH_TOOL,
    {
        "name": "vault_read",
        "description": "Lê o conteúdo de uma nota do vault Obsidian. Use para responder perguntas sobre informações já armazenadas.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Caminho relativo da nota, ex: Música/bandas-favoritas.md"}
            },
            "required": ["path"],
        },
    },
    {
        "name": "vault_write",
        "description": "Cria ou atualiza uma nota no vault Obsidian e faz commit+push para o GitHub. Use para armazenar informações que o dono quer guardar.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Caminho relativo da nota, ex: Música/bandas-favoritas.md"},
                "content": {"type": "string", "description": "Conteúdo completo da nota em Markdown"},
                "commit_msg": {"type": "string", "description": "Mensagem de commit git curta descrevendo a mudança"},
            },
            "required": ["path", "content", "commit_msg"],
        },
    },
    {
        "name": "vault_list",
        "description": "Lista todas as notas existentes no vault (ou em uma subpasta). Use para descobrir o que já está armazenado antes de criar uma nota nova.",
        "input_schema": {
            "type": "object",
            "properties": {
                "subfolder": {"type": "string", "description": "Subpasta para filtrar, ex: 'Música'. Deixe vazio para listar tudo."}
            },
            "required": [],
        },
    },
]


def execute_tool(name: str, inputs: dict, vault: VaultRepo) -> str:
    try:
        if name == "vault_read":
            content = vault.read(inputs["path"])
            return content if content is not None else f"Nota não encontrada: {inputs['path']}"

        if name == "vault_write":
            vault.pull()
            vault.write(inputs["path"], inputs["content"], inputs["commit_msg"])
            folder = str(Path(inputs["path"]).parent)
            vault.update_moc("" if folder == "." else folder)
            return f"Nota salva: {inputs['path']}"

        if name == "vault_list":
            files = vault.list_files(inputs.get("subfolder", ""))
            if not files:
                return "Nenhuma nota encontrada."
            return "\n".join(files)

        return f"Ferramenta desconhecida: {name}"
    except Exception as e:
        log.exception("Erro na ferramenta %s", name)
        return f"Erro ao executar {name}: {e}"
