"""
Storage service factory and utilities for VELTO Conversion.
"""

import logging
from typing import Optional, Dict, Any
from django.conf import settings

from apps.conversions.storage.base import BaseStorageAdapter
from apps.conversions.storage.local_adapter import LocalStorageAdapter
from apps.conversions.storage.s3_adapter import S3StorageAdapter

logger = logging.getLogger(__name__)


def get_storage_service(backend_override: Optional[str] = None) -> BaseStorageAdapter:
    """
    Return the active BaseStorageAdapter instance based on Django settings or override.
    """
    backend = (backend_override or getattr(settings, "STORAGE_BACKEND", "local")).lower()

    if backend in ("s3", "aws", "minio", "r2"):
        try:
            return S3StorageAdapter()
        except Exception as exc:
            logger.warning("Failed to initialize S3StorageAdapter (%s); falling back to LocalStorageAdapter", exc)
            return LocalStorageAdapter()

    return LocalStorageAdapter()


def get_active_storage_backend() -> str:
    """Return the name of the active storage backend."""
    return getattr(settings, "STORAGE_BACKEND", "local").lower()


def get_storage_diagnostics() -> Dict[str, Any]:
    """Return non-sensitive metadata on storage backend configuration."""
    backend = get_active_storage_backend()
    quota_mb = getattr(settings, "STORAGE_QUOTA_BYTES", 524_288_000) // (1024 * 1024)
    retention_hrs = getattr(settings, "STORAGE_RETENTION_HOURS", 24)

    info = {
        "storage_backend": backend,
        "quota_limit_mb": quota_mb,
        "retention_hours": retention_hrs,
        "presigned_upload_expiry_sec": getattr(settings, "S3_PRESIGNED_UPLOAD_EXPIRY", 900),
        "presigned_download_expiry_sec": getattr(settings, "S3_PRESIGNED_DOWNLOAD_EXPIRY", 900),
    }

    if backend in ("s3", "aws", "minio", "r2"):
        info.update({
            "bucket_configured": bool(getattr(settings, "S3_BUCKET_NAME", None)),
            "region": getattr(settings, "S3_REGION", "us-east-1"),
            "custom_endpoint": bool(getattr(settings, "S3_ENDPOINT_URL", None)),
        })

    return info
