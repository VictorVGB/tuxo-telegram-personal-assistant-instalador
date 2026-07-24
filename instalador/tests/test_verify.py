import boto3
from botocore.stub import Stubber

from instalador.steps.verify import DeploymentTimeout, wait_for_running


def _session():
    return boto3.Session(region_name="us-east-1", aws_access_key_id="x", aws_secret_access_key="y")


def test_wait_for_running_succeeds_immediately():
    session = _session()
    ecs = session.client("ecs")
    stubber = Stubber(ecs)
    stubber.add_response(
        "describe_services",
        {"services": [{"runningCount": 1, "desiredCount": 1}], "failures": []},
        {"cluster": "nina", "services": ["nina"]},
    )
    stubber.activate()
    session.client = lambda *a, **kw: ecs
    wait_for_running("nina", "nina", "us-east-1", session=session, sleep=lambda s: None)
    stubber.assert_no_pending_responses()


def test_wait_for_running_times_out_immediately():
    session = _session()
    ecs = session.client("ecs")
    session.client = lambda *a, **kw: ecs
    try:
        wait_for_running("nina", "nina", "us-east-1", session=session, timeout_s=-1, sleep=lambda s: None)
        assert False, "deveria ter estourado o timeout"
    except DeploymentTimeout:
        pass


def test_wait_for_running_succeeds_after_one_retry():
    """Verifies multi-iteration polling: first poll returns not ready, second poll succeeds."""
    session = _session()
    ecs = session.client("ecs")
    stubber = Stubber(ecs)

    # First poll: not ready yet
    stubber.add_response(
        "describe_services",
        {"services": [{"runningCount": 0, "desiredCount": 1}], "failures": []},
        {"cluster": "nina", "services": ["nina"]},
    )

    # Second poll: now ready
    stubber.add_response(
        "describe_services",
        {"services": [{"runningCount": 1, "desiredCount": 1}], "failures": []},
        {"cluster": "nina", "services": ["nina"]},
    )

    stubber.activate()
    session.client = lambda *a, **kw: ecs

    # Track sleep calls to verify the loop actually slept between polls
    sleep_calls = []
    wait_for_running("nina", "nina", "us-east-1", session=session, sleep=lambda s: sleep_calls.append(s))

    # Verify both stubbed responses were consumed (proving two polls happened)
    stubber.assert_no_pending_responses()

    # Verify sleep was called once with the hardcoded 5-second interval
    assert sleep_calls == [5]
