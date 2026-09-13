"""
Storage package for VELTO Conversion.
"""

from apps.conversions.storage.base import BaseStorageAdapter
from apps.conversions.storage.local_adapter import LocalStorageAdapter
from apps.conversions.storage.s3_adapter import S3StorageAdapter
from apps.conversions.storage.service import (
    get_storage_service,
    get_active_storage_backend,
    get_storage_diagnostics,
)

__all__ = [
    "BaseStorageAdapter",
    "LocalStorageAdapter",
    "S3StorageAdapter",
    "get_storage_service",
    "get_active_storage_backend",
    "get_storage_diagnostics",
]
