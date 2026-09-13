"""
Secure filename sanitization and generation utilities.

Ensures client-provided filenames can never trigger path traversal, null-byte injection,
reserved OS collisions (e.g. Windows CON/NUL/PRN), or dangerous execution.
"""

import os
import re
import unicodedata
import uuid
from pathlib import Path

from apps.conversions.security.exceptions import UnsafeFilename

# Reserved names in Windows (case-insensitive, with or without extensions)
WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
}


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """
    Sanitize a user-supplied filename to produce a safe display or output filename.

    Rules:
    - Reject null bytes.
    - Remove path components (slash, backslash).
    - Remove control characters (ASCII 0-31, 127).
    - Normalize Unicode using NFKC format.
    - Prevent Windows reserved names (CON, NUL, AUX, PRN, COM1..9, LPT1..9).
    - Strip leading/trailing whitespace and dots.
    - Truncate stem while preserving extension if length > max_length.

    Returns
    -------
    str
        Safe filename suitable for user display or Content-Disposition headers.
    """
    if not filename:
        return "unnamed_file"

    if "\x00" in filename:
        raise UnsafeFilename("Filename contains invalid null byte character.")

    # Convert path separators to space/underscore or strip them
    clean_name = os.path.basename(filename.replace("\\", "/"))

    # Remove control characters
    clean_name = "".join(ch for ch in clean_name if ord(ch) >= 32 and ord(ch) != 127)

    # Normalize Unicode (NFKC)
    clean_name = unicodedata.normalize("NFKC", clean_name)

    # Strip whitespace, dots, and trailing separators
    clean_name = clean_name.strip(" .")

    if not clean_name:
        return "unnamed_file"

    p = Path(clean_name)
    stem = p.stem.strip(" .")
    ext = p.suffix

    # Check for Windows reserved names
    if stem.upper() in WINDOWS_RESERVED_NAMES:
        stem = f"safe_{stem}"
        clean_name = f"{stem}{ext}"

    # Re-validate length constraint
    if len(clean_name) > max_length:
        allowed_stem_len = max_length - len(ext) - 1
        if allowed_stem_len > 0:
            stem = stem[:allowed_stem_len]
            clean_name = f"{stem}{ext}"
        else:
            clean_name = clean_name[:max_length]

    return clean_name or "unnamed_file"


def generate_internal_filename(original_filename: str, prefix: str | None = None) -> str:
    """
    Generate a collision-resistant internal storage filename.

    Uses a UUID4 prefix + sanitized basename so raw user filenames
    are NEVER used as actual filesystem paths.
    """
    safe_name = sanitize_filename(original_filename)
    unique_id = prefix or uuid.uuid4().hex
    return f"{unique_id}_{safe_name}"
