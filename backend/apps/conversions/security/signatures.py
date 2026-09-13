"""
File signature and magic-byte validation routines.

Verifies actual binary and structural content signatures before processing
to prevent format spoofing, executable upload renaming, and corruption.
"""

import io
import logging
import zipfile
from pathlib import Path

from apps.conversions.security.exceptions import InvalidFileSignature

logger = logging.getLogger(__name__)

# Known binary file header signatures
SIGNATURES = {
    "pdf": [b"%PDF"],
    "png": [b"\x89PNG\r\n\x1a\n"],
    "jpg": [b"\xff\xd8\xff"],
    "jpeg": [b"\xff\xd8\xff"],
    "gif": [b"GIF87a", b"GIF89a"],
    "tiff": [b"II*\x00", b"MM\x00*"],
    "bmp": [b"BM"],
    "zip": [b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"],
    "webp": [b"RIFF"],
}


def validate_file_signature(path: str | Path, expected_format: str) -> None:
    """
    Validate that the file at path matches the magic byte signature or structure of expected_format.

    Supported formats:
    - pdf, png, jpg/jpeg, gif, tiff, bmp, webp, zip
    - docx, xlsx, pptx (Office Open XML ZIP packages)
    - txt, csv, html, md/markdown (text-based formats)

    Raises
    ------
    InvalidFileSignature
        If validation fails or magic bytes mismatch.
    """
    p = Path(path)
    if not p.exists() or not p.is_file():
        raise InvalidFileSignature(f"File '{p.name}' does not exist.")

    if p.stat().st_size == 0:
        raise InvalidFileSignature(f"File '{p.name}' is empty (0 bytes).")

    fmt = expected_format.lower().strip(".")
    if fmt == "jpeg":
        fmt = "jpg"

    # ── Text formats ─────────────────────────────────────────────────────────
    if fmt in ("txt", "csv", "html", "htm", "md", "markdown"):
        validate_text_signature(path)
        return

    # ── Office Open XML ZIP containers ───────────────────────────────────────
    if fmt in ("docx", "xlsx", "pptx"):
        validate_office_zip_signature(path, fmt)
        return

    # ── Binary magic byte checks ─────────────────────────────────────────────
    expected_magics = SIGNATURES.get(fmt)
    if not expected_magics:
        # Fallback: check if we can open via PIL for image types
        if fmt in ("webp", "tif"):
            _validate_image_pil_signature(path)
            return
        return

    try:
        with open(p, "rb") as f:
            header = f.read(16)
    except OSError as exc:
        raise InvalidFileSignature(f"Cannot read file header: {exc}") from exc

    matches = any(header.startswith(m) for m in expected_magics)
    if not matches:
        if fmt == "pdf":
            raise InvalidFileSignature(
                "The uploaded file does not appear to be a valid PDF. "
                "Expected file header '%PDF' was not found."
            )
        raise InvalidFileSignature(
            f"File '{p.name}' magic byte signature does not match expected format '{fmt}'."
        )

    # WebP extra verification (RIFF + WEBP)
    if fmt == "webp":
        if len(header) < 12 or header[8:12] != b"WEBP":
            raise InvalidFileSignature(f"File '{p.name}' is not a valid WEBP image.")


def validate_office_zip_signature(path: str | Path, fmt: str) -> None:
    """Validate DOCX, XLSX, or PPTX ZIP package structure."""
    p = Path(path)
    fmt_upper = fmt.upper()
    try:
        with zipfile.ZipFile(p, "r") as zf:
            if zf.testzip() is not None:
                raise InvalidFileSignature(f"The uploaded file does not appear to be a valid {fmt_upper} document.")
            namelist = zf.namelist()
            if fmt == "docx" and "word/document.xml" not in namelist:
                raise InvalidFileSignature(f"The uploaded file does not appear to be a valid DOCX document.")
            elif fmt == "xlsx" and "xl/workbook.xml" not in namelist:
                raise InvalidFileSignature(f"The uploaded file does not appear to be a valid XLSX document.")
            elif fmt == "pptx" and "ppt/presentation.xml" not in namelist:
                raise InvalidFileSignature(f"The uploaded file does not appear to be a valid PPTX document.")
    except InvalidFileSignature:
        raise
    except Exception as exc:
        raise InvalidFileSignature(f"The uploaded file does not appear to be a valid {fmt_upper} document.") from exc


def validate_text_signature(path: str | Path) -> None:
    """Validate plain text files (TXT, CSV, HTML, Markdown)."""
    p = Path(path)
    try:
        with open(p, "rb") as f:
            sample = f.read(8192)

        # Ensure no null bytes (binary marker)
        if b"\x00" in sample:
            raise InvalidFileSignature(f"File '{p.name}' contains binary null bytes.")

        decoded = False
        for encoding in ("utf-8-sig", "utf-8", "utf-16", "latin-1"):
            try:
                sample.decode(encoding)
                decoded = True
                break
            except UnicodeDecodeError:
                continue

        if not decoded:
            raise InvalidFileSignature(f"File '{p.name}' could not be decoded as text.")
    except InvalidFileSignature:
        raise
    except Exception as exc:
        raise InvalidFileSignature(f"Text signature validation failed: {exc}") from exc


def _validate_image_pil_signature(path: str | Path) -> None:
    """Fallback PIL image verification."""
    from PIL import Image
    try:
        with Image.open(path) as img:
            img.verify()
    except Exception as exc:
        raise InvalidFileSignature(f"File '{Path(path).name}' is not a valid image: {exc}") from exc
