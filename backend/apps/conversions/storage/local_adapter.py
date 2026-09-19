"""
Local filesystem storage adapter — explicit fallback for development and testing.
"""

import os
import shutil
import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional

from django.conf import settings
from apps.conversions.security import resolve_safe_path, PathTraversalAttempt
from apps.conversions.storage.base import BaseStorageAdapter
from apps.core.logging import log_event
from apps.core.metrics import record_storage_metrics, record_storage_failure

logger = logging.getLogger(__name__)


class LocalStorageAdapter(BaseStorageAdapter):
    """
    Local filesystem implementation of BaseStorageAdapter.

    Stores objects inside `settings.TEMP_UPLOAD_DIR / "object_store"` while enforcing
    path containment, presigned URL emulation, and lifecycle cleanup.
    """

    def __init__(self, root_dir: Optional[Path] = None):
        self.root_dir = (root_dir or (Path(settings.TEMP_UPLOAD_DIR) / "object_store")).resolve()
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_key_path(self, object_key: str) -> Path:
        """Resolve object_key to a local safe file path inside storage root."""
        clean_key = object_key.lstrip("/").replace("\\", "/")
        dest = self.root_dir / clean_key
        try:
            return resolve_safe_path(self.root_dir, dest)
        except PathTraversalAttempt as exc:
            logger.error("LocalStorageAdapter path containment violation for key '%s': %s", object_key, exc)
            raise

    def upload_file(self, local_path: str, object_key: str, content_type: Optional[str] = None) -> str:
        start_t = time.monotonic()
        src = Path(local_path).resolve()
        if not src.exists():
            record_storage_failure("upload")
            log_event("storage.upload.failed", service="storage", error_code="FILE_NOT_FOUND")
            raise FileNotFoundError(f"Source file for upload not found: {local_path}")

        try:
            dest = self._resolve_key_path(object_key)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            dur = time.monotonic() - start_t
            size = src.stat().st_size
            record_storage_metrics("upload", status="success", bytes_transferred=size, duration_seconds=dur)
            log_event("storage.upload.completed", service="storage", file_size_bytes=size, duration_ms=int(dur * 1000))
            logger.info("LocalStorageAdapter: Uploaded %s → key '%s'", local_path, object_key)
            return object_key
        except Exception as exc:
            record_storage_failure("upload")
            log_event("storage.upload.failed", service="storage", error_code=type(exc).__name__)
            raise

    def download_file(self, object_key: str, local_dest_path: str) -> str:
        start_t = time.monotonic()
        src = self._resolve_key_path(object_key)
        if not src.exists():
            record_storage_failure("download")
            raise FileNotFoundError(f"Storage object for key '{object_key}' not found.")

        try:
            dest = Path(local_dest_path).resolve()
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            dur = time.monotonic() - start_t
            size = src.stat().st_size
            record_storage_metrics("download", status="success", bytes_transferred=size, duration_seconds=dur)
            logger.info("LocalStorageAdapter: Downloaded key '%s' → %s", object_key, local_dest_path)
            return str(dest)
        except Exception:
            record_storage_failure("download")
            raise

    def generate_presigned_upload_url(
        self,
        object_key: str,
        content_type: Optional[str] = None,
        max_size: Optional[int] = None,
        expires_in: int = 900,
    ) -> Dict[str, Any]:
        """Emulate presigned upload URL for local backend."""
        dest = self._resolve_key_path(object_key)
        dest.parent.mkdir(parents=True, exist_ok=True)

        return {
            "url": f"/api/conversions/upload-url/local-mock-upload/?key={object_key}",
            "fields": {
                "key": object_key,
                "Content-Type": content_type or "application/octet-stream",
            },
            "expires_in": expires_in,
            "max_file_size": max_size or getattr(settings, "MAX_UPLOAD_SIZE", 52_428_800),
            "object_key": object_key,
            "backend": "local",
        }

    def generate_presigned_download_url(
        self,
        object_key: str,
        filename: Optional[str] = None,
        expires_in: int = 900,
    ) -> str:
        """Emulate presigned download URL for local backend."""
        dest = self._resolve_key_path(object_key)
        if not dest.exists():
            raise FileNotFoundError(f"Storage object '{object_key}' not found.")
        fn_param = f"&filename={filename}" if filename else ""
        return f"/api/conversions/download-url/local-mock-download/?key={object_key}{fn_param}"

    def object_exists(self, object_key: str) -> bool:
        try:
            p = self._resolve_key_path(object_key)
            return p.exists() and p.is_file()
        except Exception:
            return False

    def get_object_metadata(self, object_key: str) -> Dict[str, Any]:
        p = self._resolve_key_path(object_key)
        if not p.exists():
            raise FileNotFoundError(f"Object key '{object_key}' not found.")
        st = p.stat()
        return {
            "size": st.st_size,
            "last_modified": st.st_mtime,
            "content_type": "application/octet-stream",
        }

    def delete_object(self, object_key: str) -> bool:
        try:
            p = self._resolve_key_path(object_key)
            if p.exists():
                size = p.stat().st_size
                p.unlink()
                # Clean up parent directory if empty
                if p.parent != self.root_dir and not any(p.parent.iterdir()):
                    try:
                        p.parent.rmdir()
                    except Exception:
                        pass
                record_storage_metrics("delete", status="success", bytes_transferred=size)
                log_event("storage.deleted", service="storage")
                logger.info("LocalStorageAdapter: Deleted object key '%s'", object_key)
                return True
        except Exception as exc:
            record_storage_failure("delete")
            logger.warning("LocalStorageAdapter: Error deleting object key '%s': %s", object_key, exc)
        return False

    def get_stored_size(self, object_key: str) -> int:
        try:
            p = self._resolve_key_path(object_key)
            if p.exists() and p.is_file():
                return p.stat().st_size
        except Exception:
            pass
        return 0
