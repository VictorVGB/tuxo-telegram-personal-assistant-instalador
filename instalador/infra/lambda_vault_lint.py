"""vault-lint: Lambda semanal que verifica a estrutura do vault via GitHub API."""

from __future__ import annotations

import base64
import json
import os
import re
import urllib.request
from typing import Any


def _get_secret() -> dict[str, str]:
    import boto3
    client = boto3.client("secretsmanager")
    resp = client.get_secret_value(SecretId=os.environ["SECRET_ID"])
    return json.loads(resp["SecretString"])


def _gh_get(path: str, token: str) -> Any:
    url = f"https://api.github.com{path}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "tuxo-vault-lint/1.0",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def _parse_repo(vault_url: str) -> tuple[str, str]:
    """Extrai owner/repo de https://github.com/owner/repo."""
    m = re.match(r"https://github\.com/([^/]+)/([^/]+?)(?:\.git)?$", vault_url)
    if not m:
        raise ValueError(f"VAULT_REPO_URL inválido: {vault_url}")
    return m.group(1), m.group(2)


def _fetch_all_files(owner: str, repo: str, token: str) -> list[dict]:
    """Retorna lista de todos os arquivos no repo via Git Trees API."""
    ref = _gh_get(f"/repos/{owner}/{repo}/git/ref/heads/main", token)
    sha = ref["object"]["sha"]
    tree = _gh_get(f"/repos/{owner}/{repo}/git/trees/{sha}?recursive=1", token)
    return [item for item in tree.get("tree", []) if item["type"] == "blob"]


def _read_file(owner: str, repo: str, path: str, token: str) -> str:
    data = _gh_get(f"/repos/{owner}/{repo}/contents/{path}", token)
    return base64.b64decode(data["content"]).decode("utf-8", errors="replace")


def _parse_frontmatter(content: str) -> dict | None:
    """Parser mínimo de frontmatter YAML (só scalars e listas simples)."""
    if not content.startswith("---"):
        return None
    parts = content.split("---", 2)
    if len(parts) < 3:
        return None
    fm: dict = {}
    for line in parts[1].splitlines():
        m = re.match(r"^(\w[\w\-]*)\s*:\s*(.*)$", line)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        if val.startswith("["):
            fm[key] = [v.strip().strip("'\"") for v in val.strip("[]").split(",") if v.strip()]
        else:
            fm[key] = val
    return fm or {}


def _tg_send(token: str, chat_id: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": text[:4096],
                          "parse_mode": "Markdown"}).encode()
    req = urllib.request.Request(url, data=payload,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15):
        pass


def handler(event: Any, context: Any) -> dict:
    secret = _get_secret()
    token = secret["GITHUB_TOKEN"]
    vault_url = secret["VAULT_REPO_URL"]
    tg_token = secret["TELEGRAM_BOT_TOKEN"]
    chat_id = secret["OWNER_TELEGRAM_CHAT_ID"]

    owner, repo = _parse_repo(vault_url)
    files = _fetch_all_files(owner, repo, token)
    md_files = [f for f in files if f["path"].endswith(".md") and ".git" not in f["path"]]

    issues: list[str] = []
    moc_links: dict[str, list[str]] = {}  # moc_path -> [linked stems]
    all_stems = {f["path"].rsplit("/", 1)[-1].replace(".md", "") for f in md_files}

    for f in md_files:
        path = f["path"]
        is_moc = path.endswith("/MOC.md") or path == "MOC.md"

        try:
            content = _read_file(owner, repo, path, token)
        except Exception as e:
            issues.append(f"⚠️ Erro ao ler `{path}`: {e}")
            continue

        if is_moc:
            # Coleta links [[stem]] do MOC para verificar orphans
            links = re.findall(r"\[\[([^\]]+)\]\]", content)
            moc_links[path] = [lnk.split("/")[-1].split("|")[0] for lnk in links]
            continue

        fm = _parse_frontmatter(content)
        if fm is None:
            issues.append(f"❌ Sem frontmatter: `{path}`")
            continue

        missing = [field for field in ("tags", "tipo") if not fm.get(field)]
        if missing:
            issues.append(f"⚠️ Campos ausentes ({', '.join(missing)}): `{path}`")

        if len(content.strip()) < 50:
            issues.append(f"📝 Nota muito curta (<50 chars): `{path}`")

    # Verifica links quebrados nos MOCs
    for moc_path, links in moc_links.items():
        for stem in links:
            if stem not in all_stems:
                issues.append(f"🔗 Link quebrado em `{moc_path}`: [[{stem}]]")

    # Monta relatório
    total = len(md_files)
    moc_count = sum(1 for f in md_files if f["path"].endswith("MOC.md"))
    note_count = total - moc_count

    if issues:
        header = f"*vault-lint — relatório semanal*\n{note_count} notas, {moc_count} MOCs\n\n"
        body = "\n".join(issues[:30])
        if len(issues) > 30:
            body += f"\n...e mais {len(issues) - 30} ocorrências."
        msg = header + body
    else:
        msg = (f"*vault-lint ✅ — tudo certo*\n"
               f"{note_count} notas e {moc_count} MOCs sem problemas.")

    _tg_send(tg_token, chat_id, msg)
    return {"statusCode": 200, "issues": len(issues)}
