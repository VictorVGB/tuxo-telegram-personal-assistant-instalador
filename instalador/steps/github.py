"""Wrapper de linha de comando pro GitHub CLI (gh)."""

from __future__ import annotations

import subprocess


class GhError(RuntimeError):
    pass


def _run(args: list[str], run=subprocess.run) -> subprocess.CompletedProcess:
    result = run(["gh", *args], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise GhError(result.stderr.strip() or result.stdout.strip())
    return result


def is_authenticated(run=subprocess.run) -> bool:
    result = run(["gh", "auth", "status"], capture_output=True, text=True, check=False)
    return result.returncode == 0


def has_repo_scope(run=subprocess.run) -> bool:
    result = run(["gh", "auth", "status"], capture_output=True, text=True, check=False)
    output = result.stdout + result.stderr
    return result.returncode == 0 and "'repo'" in output


def repo_exists(name: str, run=subprocess.run) -> bool:
    result = run(["gh", "repo", "view", name], capture_output=True, text=True, check=False)
    return result.returncode == 0


def create_private_repo(name: str, run=subprocess.run) -> None:
    if repo_exists(name, run=run):
        return
    _run(["repo", "create", name, "--private", "--confirm"], run=run)


def ensure_repo_scope(run=subprocess.run) -> None:
    if has_repo_scope(run=run):
        return
    # Interactive device-code flow — must inherit the terminal's stdio so the
    # user can see and respond to the prompt, unlike the other gh calls here.
    result = run(["gh", "auth", "refresh", "-h", "github.com", "-s", "repo"], check=False)
    if result.returncode != 0:
        raise GhError("gh auth refresh failed")


def get_token(run=subprocess.run) -> str:
    result = _run(["auth", "token"], run=run)
    return result.stdout.strip()


def repo_url(name: str, run=subprocess.run) -> str:
    result = _run(["repo", "view", name, "--json", "url", "-q", ".url"], run=run)
    return result.stdout.strip() + ".git"
