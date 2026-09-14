"""
Single source of truth for format specifications in VELTO Conversion.

Centralizes:
  - Format identifiers and canonical extensions
  - Primary MIME types and acceptable aliases
  - Magic byte signatures
  - Maximum size and page limits
  - Animation and multi-frame rules
  - Format spec lookup and resolution
"""

from dataclasses import dataclass, field
from typing import Callable, Any, Optional, Set, Tuple
from pathlib import Path

from apps.conversions.security.limits import (
    MAX_SINGLE_FILE_SIZE,
    MAX_OUTPUT_SIZE,
    MAX_PDF_PAGES,
    MAX_OCR_PAGES,
)


@dataclass(frozen=True)
class FormatSpec:
    """Specification rules for a single file format."""

    format_name: str
    extension: str
    allowed_extensions: Tuple[str, ...]
    primary_mime_type: str
    allowed_mime_types: Set[str]
    magic_bytes: Optional[bytes] = None
    max_file_size: int = MAX_OUTPUT_SIZE
    max_page_count: Optional[int] = None
    supports_animation: bool = False


FORMAT_SPECIFICATIONS: dict[str, FormatSpec] = {
    "pdf": FormatSpec(
        format_name="pdf",
        extension=".pdf",
        allowed_extensions=(".pdf",),
        primary_mime_type="application/pdf",
        allowed_mime_types={"application/pdf", "application/x-pdf"},
        magic_bytes=b"%PDF",
        max_file_size=MAX_OUTPUT_SIZE,
        max_page_count=MAX_PDF_PAGES,
    ),
    "docx": FormatSpec(
        format_name="docx",
        extension=".docx",
        allowed_extensions=(".docx", ".doc"),
        primary_mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        allowed_mime_types={
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
            "application/zip",
            "application/x-zip-compressed",
        },
        magic_bytes=b"PK\x03\x04",
        max_file_size=MAX_OUTPUT_SIZE,
    ),
    "xlsx": FormatSpec(
        format_name="xlsx",
        extension=".xlsx",
        allowed_extensions=(".xlsx", ".xls"),
        primary_mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        allowed_mime_types={
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-excel",
            "application/zip",
            "application/x-zip-compressed",
        },
        magic_bytes=b"PK\x03\x04",
        max_file_size=MAX_OUTPUT_SIZE,
    ),
    "pptx": FormatSpec(
        format_name="pptx",
        extension=".pptx",
        allowed_extensions=(".pptx", ".ppt"),
        primary_mime_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        allowed_mime_types={
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "application/vnd.ms-powerpoint",
            "application/zip",
            "application/x-zip-compressed",
        },
        magic_bytes=b"PK\x03\x04",
        max_file_size=MAX_OUTPUT_SIZE,
    ),
    "jpg": FormatSpec(
        format_name="jpg",
        extension=".jpg",
        allowed_extensions=(".jpg", ".jpeg"),
        primary_mime_type="image/jpeg",
        allowed_mime_types={"image/jpeg", "image/jpg", "image/pjpeg"},
        magic_bytes=b"\xff\xd8\xff",
        max_file_size=MAX_OUTPUT_SIZE,
    ),
    "jpeg": FormatSpec(
        format_name="jpeg",
        extension=".jpg",
        allowed_extensions=(".jpg", ".jpeg"),
        primary_mime_type="image/jpeg",
        allowed_mime_types={"image/jpeg", "image/jpg", "image/pjpeg"},
        magic_bytes=b"\xff\xd8\xff",
        max_file_size=MAX_OUTPUT_SIZE,
    ),
    "png": FormatSpec(
        format_name="png",
        extension=".png",
        allowed_extensions=(".png",),
        primary_mime_type="image/png",
        allowed_mime_types={"image/png", "image/x-png"},
        magic_bytes=b"\x89PNG\r\n\x1a\n",
        max_file_size=MAX_OUTPUT_SIZE,
    ),
    "webp": FormatSpec(
        format_name="webp",
        extension=".webp",
        allowed_extensions=(".webp",),
        primary_mime_type="image/webp",
        allowed_mime_types={"image/webp"},
        magic_bytes=b"RIFF",
        max_file_size=MAX_OUTPUT_SIZE,
    ),
    "bmp": FormatSpec(
        format_name="bmp",
        extension=".bmp",
        allowed_extensions=(".bmp",),
        primary_mime_type="image/bmp",
        allowed_mime_types={"image/bmp", "image/x-bmp", "image/x-ms-bmp"},
        magic_bytes=b"BM",
        max_file_size=MAX_OUTPUT_SIZE,
    ),
    "tiff": FormatSpec(
        format_name="tiff",
        extension=".tiff",
        allowed_extensions=(".tiff", ".tif"),
        primary_mime_type="image/tiff",
        allowed_mime_types={"image/tiff", "image/x-tiff"},
        magic_bytes=b"II*\x00",
        max_file_size=MAX_OUTPUT_SIZE,
    ),
    "gif": FormatSpec(
        format_name="gif",
        extension=".gif",
        allowed_extensions=(".gif",),
        primary_mime_type="image/gif",
        allowed_mime_types={"image/gif"},
        magic_bytes=b"GIF8",
        max_file_size=MAX_OUTPUT_SIZE,
        supports_animation=True,
    ),
    "zip": FormatSpec(
        format_name="zip",
        extension=".zip",
        allowed_extensions=(".zip",),
        primary_mime_type="application/zip",
        allowed_mime_types={"application/zip", "application/x-zip-compressed", "application/x-zip"},
        magic_bytes=b"PK\x03\x04",
        max_file_size=MAX_OUTPUT_SIZE,
    ),
    "txt": FormatSpec(
        format_name="txt",
        extension=".txt",
        allowed_extensions=(".txt",),
        primary_mime_type="text/plain",
        allowed_mime_types={"text/plain", "text/ascii", "text/utf-8"},
        max_file_size=MAX_OUTPUT_SIZE,
    ),
    "csv": FormatSpec(
        format_name="csv",
        extension=".csv",
        allowed_extensions=(".csv",),
        primary_mime_type="text/csv",
        allowed_mime_types={
            "text/csv",
            "text/plain",
            "application/csv",
            "text/x-csv",
            "application/x-csv",
            "text/comma-separated-values",
        },
        max_file_size=MAX_OUTPUT_SIZE,
    ),
    "html": FormatSpec(
        format_name="html",
        extension=".html",
        allowed_extensions=(".html", ".htm"),
        primary_mime_type="text/html",
        allowed_mime_types={"text/html", "application/xhtml+xml", "text/plain"},
        max_file_size=MAX_OUTPUT_SIZE,
    ),
    "md": FormatSpec(
        format_name="md",
        extension=".md",
        allowed_extensions=(".md", ".markdown"),
        primary_mime_type="text/markdown",
        allowed_mime_types={"text/markdown", "text/plain", "text/x-markdown"},
        max_file_size=MAX_OUTPUT_SIZE,
    ),
}


def get_format_spec(format_name: str) -> FormatSpec:
    """
    Look up the FormatSpec for a format identifier.

    Raises KeyError if format_name is unknown.
    """
    key = format_name.lower().strip()
    if key in FORMAT_SPECIFICATIONS:
        return FORMAT_SPECIFICATIONS[key]
    raise KeyError(f"Unknown format specification key: '{format_name}'")
