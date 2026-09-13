"""
Base storage adapter interface for VELTO Conversion.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional
import uuid

from apps.conversions.security import sanitize_filename, generate_internal_filename, resolve_safe_path, PathTraversalAttempt


class BaseStorageAdapter(ABC):
    """
    Abstract Base Class for VELTO Object Storage Adapters.
    """

    @staticmethod
    def generate_object_key(owner_identity: str, job_uuid: str, category: str, filename: str) -> str:
        """
        Generate a secure, non-guessable object key.

        Structure:
          users/{user_id}/jobs/{job_uuid}/{category}/{random_name}
          or
          sessions/{session_key}/jobs/{job_uuid}/{category}/{random_name}
        """
        safe_base = sanitize_filename(filename)
        random_name = generate_internal_filename(safe_base)
        category_clean = "input" if category in ("input", "inputs") else "output"

        owner_prefix = (
            f"users/{owner_identity}"
            if owner_identity.startswith("usr_") or owner_identity.isdigit()
            else f"sessions/{owner_identity}"
        )
        key = f"{owner_prefix}/jobs/{job_uuid}/{category_clean}/{random_name}"

        # Ensure no path traversal in object keys
        if ".." in key or key.startswith("/"):
            raise PathTraversalAttempt(f"Invalid object key structure generated: '{key}'")
        return key

    @abstractmethod
    def upload_file(self, local_path: str, object_key: str, content_type: Optional[str] = None) -> str:
        """Upload a local file to the storage provider and return the object_key."""
        pass

    @abstractmethod
    def download_file(self, object_key: str, local_dest_path: str) -> str:
        """Download an object from the storage provider to a local destination path."""
        pass

    @abstractmethod
    def generate_presigned_upload_url(
        self,
        object_key: str,
        content_type: Optional[str] = None,
        max_size: Optional[int] = None,
        expires_in: int = 900,
    ) -> Dict[str, Any]:
        """Generate a short-lived presigned upload URL or POST dictionary."""
        pass

    @abstractmethod
    def generate_presigned_download_url(
        self,
        object_key: str,
        filename: Optional[str] = None,
        expires_in: int = 900,
    ) -> str:
        """Generate a short-lived presigned download URL."""
        pass

    @abstractmethod
    def object_exists(self, object_key: str) -> bool:
        """Return True if the object exists in storage."""
        pass

    @abstractmethod
    def get_object_metadata(self, object_key: str) -> Dict[str, Any]:
        """Return metadata dict (size, content_type, last_modified)."""
        pass

    @abstractmethod
    def delete_object(self, object_key: str) -> bool:
        """Delete an object from storage cleanly. Return True if successful."""
        pass

    @abstractmethod
    def get_stored_size(self, object_key: str) -> int:
        """Return object size in bytes, or 0 if missing/error."""
        pass
