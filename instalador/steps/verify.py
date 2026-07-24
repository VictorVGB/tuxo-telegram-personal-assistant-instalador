"""Espera o serviço ECS ficar RUNNING."""

from __future__ import annotations

import time

import boto3


class DeploymentTimeout(RuntimeError):
    pass


def wait_for_running(
    cluster: str,
    service: str,
    region: str,
    session: boto3.Session | None = None,
    timeout_s: int = 300,
    sleep=time.sleep,
) -> None:
    session = session or boto3.Session()
    ecs = session.client("ecs", region_name=region)
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        resp = ecs.describe_services(cluster=cluster, services=[service])
        svc = resp["services"][0]
        if svc["runningCount"] >= 1 and svc["desiredCount"] >= 1:
            return
        sleep(5)
    raise DeploymentTimeout(f"Serviço {service} não ficou RUNNING em {timeout_s}s")
