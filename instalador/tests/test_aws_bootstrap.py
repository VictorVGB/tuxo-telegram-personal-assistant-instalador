import boto3
from botocore.stub import Stubber

from instalador.steps.aws_bootstrap import ensure_state_bucket, get_account_id, terraform_state_bucket_name


def _session():
    return boto3.Session(region_name="us-east-1", aws_access_key_id="x", aws_secret_access_key="y")


def test_get_account_id():
    session = _session()
    sts = session.client("sts")
    stubber = Stubber(sts)
    stubber.add_response(
        "get_caller_identity",
        {"Account": "123456789012", "Arn": "arn:aws:iam::123456789012:user/x", "UserId": "AID"},
    )
    stubber.activate()
    session.client = lambda *a, **kw: sts
    assert get_account_id(session=session) == "123456789012"


def test_terraform_state_bucket_name():
    assert terraform_state_bucket_name("nina", "123456789012") == "nina-terraform-state-123456789012"


def test_ensure_state_bucket_skips_if_exists():
    session = _session()
    s3 = session.client("s3")
    stubber = Stubber(s3)
    stubber.add_response(
        "list_buckets",
        {"Buckets": [{"Name": "nina-terraform-state-123456789012", "CreationDate": __import__("datetime").datetime.now()}]},
    )
    stubber.activate()
    session.client = lambda *a, **kw: s3
    ensure_state_bucket("nina-terraform-state-123456789012", "us-east-1", session=session)
    stubber.assert_no_pending_responses()


def test_ensure_state_bucket_creates_when_missing():
    session = _session()
    s3 = session.client("s3")
    stubber = Stubber(s3)
    bucket = "nina-terraform-state-123456789012"
    stubber.add_response("list_buckets", {"Buckets": []})
    stubber.add_response("create_bucket", {}, {"Bucket": bucket})
    stubber.add_response(
        "put_bucket_versioning", {}, {"Bucket": bucket, "VersioningConfiguration": {"Status": "Enabled"}}
    )
    stubber.add_response(
        "put_bucket_encryption",
        {},
        {
            "Bucket": bucket,
            "ServerSideEncryptionConfiguration": {
                "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
            },
        },
    )
    stubber.add_response(
        "put_public_access_block",
        {},
        {
            "Bucket": bucket,
            "PublicAccessBlockConfiguration": {
                "BlockPublicAcls": True,
                "IgnorePublicAcls": True,
                "BlockPublicPolicy": True,
                "RestrictPublicBuckets": True,
            },
        },
    )
    stubber.activate()
    session.client = lambda *a, **kw: s3
    ensure_state_bucket(bucket, "us-east-1", session=session)
    stubber.assert_no_pending_responses()
