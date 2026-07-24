from unittest.mock import MagicMock, call

import boto3
from botocore.stub import Stubber

from instalador.steps.deploy import (
    build_and_push_image,
    force_new_deployment,
    terraform_apply,
    terraform_init,
    terraform_output,
)


def test_terraform_init_calls_correct_command(tmp_path):
    run = MagicMock()
    terraform_init(cwd=tmp_path, run=run)
    run.assert_called_once_with(["terraform", "init", "-backend-config=backend.hcl"], cwd=tmp_path, check=True)


def test_terraform_apply_calls_correct_command(tmp_path):
    run = MagicMock()
    terraform_apply(cwd=tmp_path, run=run)
    run.assert_called_once_with(["terraform", "apply", "-auto-approve"], cwd=tmp_path, check=True)


def test_terraform_output_returns_stripped_stdout(tmp_path):
    run = MagicMock(return_value=MagicMock(stdout="  abc123  \n"))
    result = terraform_output("ecr_repository_url", cwd=tmp_path, run=run)
    assert result == "abc123"


def test_build_and_push_image_calls_docker(tmp_path):
    run = MagicMock(return_value=MagicMock(stdout="fake-password\n"))
    ecr_url = "123.dkr.ecr.us-east-1.amazonaws.com/nina-bot"
    build_and_push_image(ecr_url, tmp_path, "us-east-1", run=run)
    assert run.call_args_list == [
        call(
            ["aws", "ecr", "get-login-password", "--region", "us-east-1"],
            capture_output=True,
            text=True,
            check=True,
        ),
        call(
            ["docker", "login", "--username", "AWS", "--password-stdin", "123.dkr.ecr.us-east-1.amazonaws.com"],
            input="fake-password",
            capture_output=True,
            text=True,
            check=True,
        ),
        call(
            ["docker", "build", "--platform", "linux/amd64", "-t", f"{ecr_url}:latest", str(tmp_path)],
            check=True,
        ),
        call(["docker", "push", f"{ecr_url}:latest"], check=True),
    ]


def test_force_new_deployment_calls_ecs_update_service():
    session = boto3.Session(region_name="us-east-1", aws_access_key_id="x", aws_secret_access_key="y")
    ecs = session.client("ecs")
    stubber = Stubber(ecs)
    stubber.add_response(
        "update_service",
        {},
        {"cluster": "nina", "service": "nina", "forceNewDeployment": True, "desiredCount": 1},
    )
    stubber.activate()
    session.client = lambda *a, **kw: ecs
    force_new_deployment("nina", "nina", "us-east-1", session=session)
    stubber.assert_no_pending_responses()
