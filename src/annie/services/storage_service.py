from __future__ import annotations

import uuid
from typing import BinaryIO

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from annie.env import get_settings


class StorageService:
    """S3-compatible object storage for uploads (MinIO in dev)."""

    def __init__(self) -> None:
        settings = get_settings()
        self.bucket = settings.s3_bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
            use_ssl=settings.s3_use_ssl,
            config=Config(signature_version="s3v4", retries={"max_attempts": 4, "mode": "standard"}),
        )
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        try:
            self._client.head_bucket(Bucket=self.bucket)
        except ClientError:
            self._client.create_bucket(Bucket=self.bucket)

    def upload(self, *, fileobj: BinaryIO, content_type: str, user_id: uuid.UUID) -> tuple[str, str]:
        object_key = f"users/{user_id}/{uuid.uuid4().hex}"
        self._client.upload_fileobj(
            fileobj,
            self.bucket,
            object_key,
            ExtraArgs={"ContentType": content_type},
        )
        return object_key, f"s3://{self.bucket}/{object_key}"

    def download(self, object_key: str) -> bytes:
        response = self._client.get_object(Bucket=self.bucket, Key=object_key)
        return response["Body"].read()

    def delete(self, object_key: str) -> None:
        self._client.delete_object(Bucket=self.bucket, Key=object_key)
