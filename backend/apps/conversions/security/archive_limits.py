"""
Archive protection and zip-bomb validation service.

Inspects archive structure, compression ratio, member count, uncompressed size,
and entry paths before extraction to prevent decompression bombs and ZIP path traversal exploits.
"""

import logging
import zipfile
from pathlib import Path

from apps.conversions.security.antivirus import scan_file_security
from apps.conversions.security.exceptions import ArchiveLimitExceeded
from apps.conversions.security.limits import (
    MAX_ARCHIVE_EXPANDED_SIZE,
    MAX_ARCHIVE_MEMBERS,
    MAX_ARCHIVE_RATIO,
)
from apps.conversions.security.paths import resolve_safe_path

logger = logging.getLogger(__name__)


def validate_zip_archive_security(
    zip_path: str | Path,
    extract_dir: str | Path | None = None,
    scan_members: bool = True,
) -> list[Path]:
    """
    Validate ZIP archive safety before and during extraction.

    Checks:
    - Member count <= MAX_ARCHIVE_MEMBERS.
    - Total uncompressed size <= MAX_ARCHIVE_EXPANDED_SIZE.
    - Overall compression ratio <= MAX_ARCHIVE_RATIO.
    - Path traversal in member names (reject ../, ..\\, absolute paths, drive letters, null bytes).
    - If extract_dir is provided: safely extracts members into isolated directory and scans extracted files.

    Returns
    -------
    list[Path]
        List of extracted file Paths (if extract_dir was provided), else empty list.

    Raises
    ------
    ArchiveLimitExceeded
        If any archive safety rule is violated.
    """
    p = Path(zip_path)
    if not p.exists() or not p.is_file():
        raise ArchiveLimitExceeded(f"Archive file '{p.name}' does not exist.")

    try:
        with zipfile.ZipFile(p, "r") as zf:
            infolist = zf.infolist()

            if len(infolist) > MAX_ARCHIVE_MEMBERS:
                raise ArchiveLimitExceeded(
                    f"Archive contains {len(infolist)} files, exceeding maximum allowed limit of {MAX_ARCHIVE_MEMBERS}."
                )

            total_uncompressed = 0
            total_compressed = 0

            for info in infolist:
                fname = info.filename

                # Path traversal check on zip entry name
                if "\x00" in fname:
                    raise ArchiveLimitExceeded(f"Archive entry '{fname}' contains null bytes.")
                if fname.startswith(("/", "\\")) or ".." in fname.replace("\\", "/").split("/"):
                    raise ArchiveLimitExceeded(
                        f"Archive entry '{fname}' contains illegal path traversal components."
                    )
                if len(fname) > 2 and fname[1] == ":":
                    raise ArchiveLimitExceeded(
                        f"Archive entry '{fname}' contains absolute drive letter specifications."
                    )

                total_uncompressed += info.file_size
                total_compressed += info.compress_size

            if total_uncompressed > MAX_ARCHIVE_EXPANDED_SIZE:
                raise ArchiveLimitExceeded(
                    f"Archive uncompressed size ({total_uncompressed // (1024*1024)} MB) "
                    f"exceeds limit of {MAX_ARCHIVE_EXPANDED_SIZE // (1024*1024)} MB."
                )

            # Compression ratio check (only for non-empty uncompressed totals > 1MB)
            if total_compressed > 0 and total_uncompressed > 1_048_576:
                ratio = total_uncompressed / total_compressed
                if ratio > MAX_ARCHIVE_RATIO:
                    raise ArchiveLimitExceeded(
                        f"Decompression bomb detected: archive compression ratio ({ratio:.1f}:1) "
                        f"exceeds maximum allowed ratio of {MAX_ARCHIVE_RATIO:.0f}:1."
                    )

            if not extract_dir:
                return []

            target_dir = Path(extract_dir).resolve()
            extracted_paths = []

            for info in infolist:
                if info.is_dir():
                    continue

                safe_target = resolve_safe_path(target_dir, info.filename)
                safe_target.parent.mkdir(parents=True, exist_ok=True)

                with zf.open(info) as src, open(safe_target, "wb") as dst:
                    chunk = src.read(65536)
                    while chunk:
                        dst.write(chunk)
                        chunk = src.read(65536)

                if scan_members:
                    scan_file_security(safe_target)

                extracted_paths.append(safe_target)

            return extracted_paths

    except ArchiveLimitExceeded:
        raise
    except Exception as exc:
        raise ArchiveLimitExceeded(f"Failed to inspect or extract archive safely: {exc}") from exc
