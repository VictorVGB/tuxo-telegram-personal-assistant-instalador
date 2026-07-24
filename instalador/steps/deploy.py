"""Terraform apply + build/push da imagem Docker + deploy no ECS."""

from __future__ import annotations

import subprocess
from pathlib import Path

INFRA_DIR = Path(__file__).parent.parent / "infra"


def terraform_init(cwd: Path = INFRA_DIR, run=subprocess.run) -> None:
    run(["terraform", "init", "-backend-config=backend.hcl"], cwd=cwd, check=True)


def terraform_apply(cwd: Path = INFRA_DIR, run=subprocess.run) -> None:
    run(["terraform", "apply", "-auto-approve"], cwd=cwd, check=True)


def terraform_output(name: str, cwd: Path = INFRA_DIR, run=subprocess.run) -> str:
    result = run(["terraform", "output", "-raw", name], cwd=cwd, capture_output=True, text=True, check=True)
    return result.stdout.strip()


def build_and_push_image(ecr_url: str, project_root: Path, region: str, run=subprocess.run) -> None:
    registry = ecr_url.split("/", 1)[0]
    login_result = run(
        ["aws", "ecr", "get-login-password", "--region", region],
        capture_output=True,
        text=True,
        check=True,
    )
    password = login_result.stdout.strip()
    run(
        ["docker", "login", "--username", "AWS", "--password-stdin", registry],
        input=password,
        capture_output=True,
        text=True,
        check=True,
    )
    run(["docker", "build", "--platform", "linux/amd64", "-t", f"{ecr_url}:latest", str(project_root)], check=True)
    run(["docker", "push", f"{ecr_url}:latest"], check=True)


def force_new_deployment(cluster: str, service: str, region: str, session=None) -> None:
    import boto3

    session = session or boto3.Session()
    ecs = session.client("ecs", region_name=region)
    ecs.update_service(cluster=cluster, service=service, forceNewDeployment=True, desiredCount=1)
