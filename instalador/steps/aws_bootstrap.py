"""Bootstrap de conta AWS: descoberta da conta e bucket de state do Terraform."""

from __future__ import annotations

import boto3


def get_account_id(session: boto3.Session | None = None) -> str:
    session = session or boto3.Session()
    sts = session.client("sts")
    return sts.get_caller_identity()["Account"]


def terraform_state_bucket_name(project_name: str, account_id: str) -> str:
    return f"{project_name}-terraform-state-{account_id}"


def ensure_state_bucket(bucket_name: str, region: str, session: boto3.Session | None = None) -> None:
    session = session or boto3.Session()
    s3 = session.client("s3", region_name=region)
    existing = s3.list_buckets()["Buckets"]
    if any(b["Name"] == bucket_name for b in existing):
        return
    if region == "us-east-1":
        s3.create_bucket(Bucket=bucket_name)
    else:
        s3.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={"LocationConstraint": region})
    s3.put_bucket_versioning(Bucket=bucket_name, VersioningConfiguration={"Status": "Enabled"})
    s3.put_bucket_encryption(
        Bucket=bucket_name,
        ServerSideEncryptionConfiguration={
            "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
        },
    )
    s3.put_public_access_block(
        Bucket=bucket_name,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": True,
            "RestrictPublicBuckets": True,
        },
    )
