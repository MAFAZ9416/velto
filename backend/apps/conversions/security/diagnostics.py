"""
Internal security diagnostics service.

Provides non-sensitive status information about active security controls,
limits, antivirus status, sandbox capabilities, and path protections.
"""

import os
from django.conf import settings

from apps.conversions.security.antivirus import get_antivirus_provider
from apps.conversions.security.limits import (
    MAX_ARCHIVE_EXPANDED_SIZE,
    MAX_ARCHIVE_MEMBERS,
    MAX_ARCHIVE_RATIO,
    MAX_CONCURRENT_JOBS_PER_OWNER,
    MAX_IMAGE_DIM,
    MAX_IMAGE_PIXELS,
    MAX_JOB_PROCESSING_TIMEOUT,
    MAX_OUTPUT_SIZE,
    MAX_PDF_PAGES,
    MAX_SINGLE_FILE_SIZE,
    MAX_UPLOAD_SIZE,
)
from apps.conversions.security.sandbox import get_sandbox_status


def get_security_diagnostics() -> dict:
    """
    Generate non-sensitive internal security diagnostics dictionary.

    Returns
    -------
    dict
        Safe report of active security controls.
    """
    av_mode = getattr(settings, "ANTIVIRUS_MODE", os.environ.get("ANTIVIRUS_MODE", "disabled")).lower()
    av_provider = get_antivirus_provider()

    return {
        "status": "healthy",
        "controls": {
            "mime_validation": True,
            "signature_validation": True,
            "filename_sanitization": True,
            "path_traversal_protection": True,
            "isolated_workspaces": True,
            "ownership_authorization": True,
            "archive_protection": True,
        },
        "limits": {
            "max_upload_size_bytes": MAX_UPLOAD_SIZE,
            "max_single_file_bytes": MAX_SINGLE_FILE_SIZE,
            "max_output_size_bytes": MAX_OUTPUT_SIZE,
            "max_image_pixels": MAX_IMAGE_PIXELS,
            "max_image_dim": MAX_IMAGE_DIM,
            "max_pdf_pages": MAX_PDF_PAGES,
            "max_archive_members": MAX_ARCHIVE_MEMBERS,
            "max_archive_expanded_bytes": MAX_ARCHIVE_EXPANDED_SIZE,
            "max_archive_ratio": MAX_ARCHIVE_RATIO,
            "max_concurrent_jobs_per_owner": MAX_CONCURRENT_JOBS_PER_OWNER,
            "max_job_processing_timeout_sec": MAX_JOB_PROCESSING_TIMEOUT,
        },
        "antivirus": {
            "mode": av_mode,
            "provider": av_provider.name,
            "available": av_provider.is_available(),
        },
        "sandbox": get_sandbox_status(),
    }
