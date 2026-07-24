"""Checagem de pré-requisitos de linha de comando do instalador."""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass

_MIN_TERRAFORM_VERSION = (1, 10)

_INSTALL_LINKS = {
    "darwin": {
        "git": "https://git-scm.com/download/mac",
        "docker": "https://docs.docker.com/desktop/install/mac-install/",
        "terraform": "https://developer.hashicorp.com/terraform/install",
        "aws": "https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html",
        "gh": "https://cli.github.com/",
    },
    "windows": {
        "git": "https://git-scm.com/download/win",
        "docker": "https://docs.docker.com/desktop/install/windows-install/",
        "terraform": "https://developer.hashicorp.com/terraform/install",
        "aws": "https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html",
        "gh": "https://cli.github.com/",
    },
    "linux": {
        "git": "https://git-scm.com/download/linux",
        "docker": "https://docs.docker.com/desktop/install/linux/",
        "terraform": "https://developer.hashicorp.com/terraform/install",
        "aws": "https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html",
        "gh": "https://cli.github.com/",
    },
}

_TOOLS = ("git", "docker", "terraform", "aws", "gh")


@dataclass
class ToolCheck:
    name: str
    found: bool
    version_ok: bool = True
    install_url: str = ""


def _terraform_version_ok(run) -> bool:
    result = run(["terraform", "version", "-json"], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return False
    match = re.search(r'"terraform_version":\s*"(\d+)\.(\d+)', result.stdout)
    if not match:
        return False
    major, minor = int(match.group(1)), int(match.group(2))
    return (major, minor) >= _MIN_TERRAFORM_VERSION


def check_tools(os_name: str, which=shutil.which, run=subprocess.run) -> list[ToolCheck]:
    links = _INSTALL_LINKS[os_name]
    checks = []
    for tool in _TOOLS:
        found = which(tool) is not None
        version_ok = True
        if tool == "terraform" and found:
            version_ok = _terraform_version_ok(run)
        checks.append(ToolCheck(name=tool, found=found, version_ok=version_ok, install_url=links[tool]))
    return checks


def all_ok(checks: list[ToolCheck]) -> bool:
    return all(c.found and c.version_ok for c in checks)
