"""
Centralized MIME type validation service.

Cross-validates declared browser Content-Type, detected file content MIME type,
filename extension, and magic byte signature against allowed format mappings.
"""

import logging
from pathlib import Path

from apps.conversions.security.exceptions import InvalidMimeType
from apps.conversions.security.signatures import validate_file_signature

logger = logging.getLogger(__name__)

# Map format identifiers to acceptable MIME types (including legitimate aliases)
ALLOWED_MIME_TYPES = {
    "pdf": {"application/pdf", "application/x-pdf"},
    "png": {"image/png", "image/x-png"},
    "jpg": {"image/jpeg", "image/jpg", "image/pjpeg"},
    "jpeg": {"image/jpeg", "image/jpg", "image/pjpeg"},
    "webp": {"image/webp"},
    "bmp": {"image/bmp", "image/x-bmp", "image/x-ms-bmp"},
    "gif": {"image/gif"},
    "tiff": {"image/tiff", "image/x-tiff"},
    "docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/zip",
        "application/x-zip-compressed",
    },
    "xlsx": {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/zip",
        "application/x-zip-compressed",
    },
    "pptx": {
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/zip",
        "application/x-zip-compressed",
    },
    "csv": {
        "text/csv",
        "text/plain",
        "application/csv",
        "text/x-csv",
        "application/x-csv",
        "text/comma-separated-values",
        "text/x-comma-separated-values",
    },
    "txt": {"text/plain", "text/ascii", "text/utf-8"},
    "html": {"text/html", "application/xhtml+xml", "text/plain"},
    "md": {"text/markdown", "text/plain", "text/x-markdown"},
    "markdown": {"text/markdown", "text/plain", "text/x-markdown"},
    "zip": {"application/zip", "application/x-zip-compressed", "application/x-zip"},
}


def detect_file_mime_type(path: str | Path) -> str | None:
    """Detect MIME type from content using python-magic, filetype, or signature fallback."""
    p = Path(path)
    if not p.exists():
        return None

    # Try python-magic if available
    try:
        import magic
        return magic.from_file(str(p), mime=True)
    except Exception:
        pass

    # Try filetype if available
    try:
        import filetype
        kind = filetype.guess(str(p))
        if kind is not None:
            return kind.mime
    except Exception:
        pass

    # Header signature fallback
    try:
        with open(p, "rb") as f:
            header = f.read(16)
        if header.startswith(b"%PDF"):
            return "application/pdf"
        elif header.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        elif header.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        elif header.startswith(b"GIF8"):
            return "image/gif"
        elif header.startswith(b"BM"):
            return "image/bmp"
        elif header.startswith(b"PK\x03\x04"):
            return "application/zip"
    except Exception:
        pass

    return None


def validate_mime_type(
    path: str | Path,
    declared_mime: str | None = None,
    expected_format: str | None = None,
) -> None:
    """
    Validate that the file at path matches the allowed MIME type for expected_format.

    Cross-checks:
    1. Magic byte file signature via validate_file_signature.
    2. Content-based detected MIME type (if available).
    3. Declared browser MIME type vs allowed aliases.

    Raises
    ------
    InvalidMimeType
        If validation fails or file contains suspicious executable/mismatched content.
    """
    p = Path(path)
    fmt = (expected_format or p.suffix.lstrip(".")).lower()
    if fmt == "jpeg":
        fmt = "jpg"

    # Always enforce signature validation first
    if fmt in ALLOWED_MIME_TYPES or fmt in ("txt", "csv", "html", "md", "markdown"):
        try:
            validate_file_signature(path, fmt)
        except Exception as exc:
            raise InvalidMimeType(str(exc)) from exc

    allowed = ALLOWED_MIME_TYPES.get(fmt)
    if not allowed:
        # Unknown format mapping — rely on signature validator
        return

    detected_mime = detect_file_mime_type(path)

    # If detected MIME is an executable binary or shell script, reject immediately
    if detected_mime in (
        "application/x-msdownload",
        "application/x-executable",
        "application/x-dosexec",
        "application/x-sh",
        "application/x-csh",
    ):
        raise InvalidMimeType(f"File '{p.name}' contains dangerous executable content.")

    # Check detected MIME against allowed set if detected
    if detected_mime and fmt not in ("txt", "csv", "html", "md", "markdown"):
        # For Office files, ZIP container MIME is expected
        if detected_mime not in allowed and not (
            fmt in ("docx", "xlsx", "pptx") and detected_mime in ("application/zip", "application/x-zip-compressed")
        ):
            logger.warning(
                "MIME mismatch for %s: detected %s, expected one of %s",
                p.name,
                detected_mime,
                allowed,
            )
            raise InvalidMimeType(
                f"File '{p.name}' content MIME type ({detected_mime}) does not match expected format '{fmt}'."
            )

    # Check browser-declared MIME if provided
    if declared_mime:
        norm_declared = declared_mime.lower().split(";")[0].strip()
        # Accept generic octet-stream for text files or Office files if signature passed
        if norm_declared == "application/octet-stream" and fmt in ("txt", "csv", "docx", "xlsx", "pptx"):
            return
        if norm_declared not in allowed:
            # If signature passed, log warning; if binary format mismatch, reject
            if fmt in ("pdf", "png", "jpg", "gif", "bmp") and norm_declared not in allowed:
                raise InvalidMimeType(
                    f"Declared Content-Type '{declared_mime}' is not permitted for {fmt.upper()} files."
                )
