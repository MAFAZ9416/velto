"""
S3-compatible object storage adapter — supports AWS S3, MinIO, Cloudflare R2, and S3-compatible providers.
"""

import logging
from typing import Dict, Any, Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, BotoCoreError
from django.conf import settings

from apps.conversions.storage.base import BaseStorageAdapter

logger = logging.getLogger(__name__)


class S3StorageAdapter(BaseStorageAdapter):
    """
    S3 implementation of BaseStorageAdapter using boto3.
    """

    def __init__(
        self,
        bucket_name: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        region_name: Optional[str] = None,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
    ):
        self.bucket_name = bucket_name or getattr(settings, "S3_BUCKET_NAME", "velto-storage")
        self.endpoint_url = endpoint_url or getattr(settings, "S3_ENDPOINT_URL", None)
        self.region_name = region_name or getattr(settings, "S3_REGION", "us-east-1")
        self.access_key_id = access_key_id or getattr(settings, "S3_ACCESS_KEY_ID", "")
        self.secret_access_key = secret_access_key or getattr(settings, "S3_SECRET_ACCESS_KEY", "")

        client_kwargs = {
            "service_name": "s3",
            "region_name": self.region_name,
            "config": Config(signature_version="s3v4", retries={"max_attempts": 3, "mode": "standard"}),
        }

        if self.endpoint_url:
            client_kwargs["endpoint_url"] = self.endpoint_url
        if self.access_key_id and self.secret_access_key:
            client_kwargs["aws_access_key_id"] = self.access_key_id
            client_kwargs["aws_secret_access_key"] = self.secret_access_key

        self._s3_client = boto3.client(**client_kwargs)

    @property
    def client(self):
        return self._s3_client

    def upload_file(self, local_path: str, object_key: str, content_type: Optional[str] = None) -> str:
        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type

        try:
            self.client.upload_file(local_path, self.bucket_name, object_key, ExtraArgs=extra_args if extra_args else None)
            logger.info("S3StorageAdapter: Uploaded %s → s3://%s/%s", local_path, self.bucket_name, object_key)
            return object_key
        except (ClientError, BotoCoreError) as exc:
            logger.error("S3StorageAdapter upload_file failed for key '%s': %s", object_key, exc)
            raise IOError("Storage provider upload failed.") from exc

    def download_file(self, object_key: str, local_dest_path: str) -> str:
        try:
            self.client.download_file(self.bucket_name, object_key, local_dest_path)
            logger.info("S3StorageAdapter: Downloaded s3://%s/%s → %s", self.bucket_name, object_key, local_dest_path)
            return local_dest_path
        except (ClientError, BotoCoreError) as exc:
            logger.error("S3StorageAdapter download_file failed for key '%s': %s", object_key, exc)
            raise IOError("Storage provider download failed.") from exc

    def generate_presigned_upload_url(
        self,
        object_key: str,
        content_type: Optional[str] = None,
        max_size: Optional[int] = None,
        expires_in: int = 900,
    ) -> Dict[str, Any]:
        conditions = []
        fields = {}

        if content_type:
            fields["Content-Type"] = content_type
            conditions.append({"Content-Type": content_type})

        max_limit = max_size or getattr(settings, "MAX_UPLOAD_SIZE", 52_428_800)
        conditions.append(["content-length-range", 1, max_limit])

        try:
            presigned_post = self.client.generate_presigned_post(
                Bucket=self.bucket_name,
                Key=object_key,
                Fields=fields,
                Conditions=conditions,
                ExpiresIn=expires_in,
            )
            return {
                "url": presigned_post["url"],
                "fields": presigned_post["fields"],
                "expires_in": expires_in,
                "max_file_size": max_limit,
                "object_key": object_key,
                "backend": "s3",
            }
        except (ClientError, BotoCoreError) as exc:
            logger.error("S3StorageAdapter generate_presigned_upload_url failed for key '%s': %s", object_key, exc)
            raise IOError("Failed to generate presigned upload URL.") from exc

    def generate_presigned_download_url(
        self,
        object_key: str,
        filename: Optional[str] = None,
        expires_in: int = 900,
    ) -> str:
        params = {"Bucket": self.bucket_name, "Key": object_key}
        if filename:
            params["ResponseContentDisposition"] = f'attachment; filename="{filename}"'

        try:
            url = self.client.generate_presigned_url(
                "get_object",
                Params=params,
                ExpiresIn=expires_in,
            )
            return url
        except (ClientError, BotoCoreError) as exc:
            logger.error("S3StorageAdapter generate_presigned_download_url failed for key '%s': %s", object_key, exc)
            raise IOError("Failed to generate presigned download URL.") from exc

    def object_exists(self, object_key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=object_key)
            return True
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in ("404", "NoSuchKey", "NotFound"):
                return False
            logger.warning("S3StorageAdapter head_object returned client error for key '%s': %s", object_key, exc)
            return False
        except Exception as exc:
            logger.warning("S3StorageAdapter head_object unexpected error for key '%s': %s", object_key, exc)
            return False

    def get_object_metadata(self, object_key: str) -> Dict[str, Any]:
        try:
            res = self.client.head_object(Bucket=self.bucket_name, Key=object_key)
            return {
                "size": res.get("ContentLength", 0),
                "last_modified": res.get("LastModified"),
                "content_type": res.get("ContentType", "application/octet-stream"),
            }
        except (ClientError, BotoCoreError) as exc:
            logger.error("S3StorageAdapter get_object_metadata failed for key '%s': %s", object_key, exc)
            raise FileNotFoundError(f"Storage object '{object_key}' not found.") from exc

    def delete_object(self, object_key: str) -> bool:
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=object_key)
            logger.info("S3StorageAdapter: Deleted s3://%s/%s", self.bucket_name, object_key)
            return True
        except (ClientError, BotoCoreError) as exc:
            logger.warning("S3StorageAdapter delete_object failed for key '%s': %s", object_key, exc)
            return False

    def get_stored_size(self, object_key: str) -> int:
        try:
            meta = self.get_object_metadata(object_key)
            return meta.get("size", 0)
        except Exception:
            return 0
