"""
Centralized security and resource limits for VELTO Conversion.

All limits are configurable via Django settings or environment variables.
Sensible production defaults are provided for all parameters.
"""

import os
from django.conf import settings


def _get_setting(name: str, default: int | float) -> int | float:
    """Helper to fetch limit setting from Django settings or env var, falling back to default."""
    val = getattr(settings, name, os.environ.get(name))
    if val is not None:
        try:
            if isinstance(default, float):
                return float(val)
            return int(val)
        except (ValueError, TypeError):
            pass
    return default


# ── File and Upload Limits ───────────────────────────────────────────────────
MAX_UPLOAD_SIZE = int(_get_setting("MAX_UPLOAD_SIZE", 52_428_800))             # 50 MB
MAX_SINGLE_FILE_SIZE = int(_get_setting("MAX_SINGLE_FILE_SIZE", 52_428_800))     # 50 MB
MAX_COMBINED_REQUEST_SIZE = int(_get_setting("MAX_COMBINED_REQUEST_SIZE", 209_715_200)) # 200 MB
MAX_OUTPUT_SIZE = int(_get_setting("MAX_OUTPUT_SIZE", 104_857_600))             # 100 MB
MAX_FILES_PER_REQUEST = int(_get_setting("MAX_FILES_PER_REQUEST", 100))

# ── Image Limits ─────────────────────────────────────────────────────────────
MAX_IMAGE_PIXELS = int(_get_setting("MAX_IMAGE_PIXELS", 80_000_000))            # 80 Megapixels
MAX_IMAGE_DIM = int(_get_setting("MAX_IMAGE_DIM", 12_000))                     # 12,000 x 12,000 px

# ── PDF Limits ───────────────────────────────────────────────────────────────
MAX_PDF_PAGES = int(_get_setting("MAX_PDF_PAGES", 1_000))
MAX_PDF_TOTAL_PAGES = int(_get_setting("MAX_PDF_TOTAL_PAGES", 2_000))
MAX_PDF_SPLIT_OUTPUTS = int(_get_setting("MAX_PDF_SPLIT_OUTPUTS", 500))

# ── Spreadsheet & Document Limits ─────────────────────────────────────────────
MAX_SPREADSHEET_ROWS = int(_get_setting("MAX_SPREADSHEET_ROWS", 100_000))
MAX_SPREADSHEET_CELLS = int(_get_setting("MAX_SPREADSHEET_CELLS", 1_000_000))
MAX_TEXT_LENGTH = int(_get_setting("MAX_TEXT_LENGTH", 10_000_000))               # 10M characters

# ── Archive Safety Limits ─────────────────────────────────────────────────────
MAX_ARCHIVE_MEMBERS = int(_get_setting("MAX_ARCHIVE_MEMBERS", 500))
MAX_ARCHIVE_EXPANDED_SIZE = int(_get_setting("MAX_ARCHIVE_EXPANDED_SIZE", 209_715_200)) # 200 MB
MAX_ARCHIVE_RATIO = float(_get_setting("MAX_ARCHIVE_RATIO", 100.0))             # Max compression ratio 100:1

# ── OCR Safety Limits ─────────────────────────────────────────────────────────
MAX_OCR_PAGES = int(_get_setting("MAX_OCR_PAGES", 100))
MAX_OCR_OUTPUT_SIZE = int(_get_setting("MAX_OCR_OUTPUT_SIZE", 26_214_400))       # 25 MB

# ── Abuse & Timeout Limits ────────────────────────────────────────────────────
MAX_CONCURRENT_JOBS_PER_OWNER = int(_get_setting("MAX_CONCURRENT_JOBS_PER_OWNER", 5))
MAX_JOB_PROCESSING_TIMEOUT = int(_get_setting("MAX_JOB_PROCESSING_TIMEOUT", 120)) # 120 seconds
