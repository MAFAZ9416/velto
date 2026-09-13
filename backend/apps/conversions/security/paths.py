"""
Path traversal protection and canonical path resolution utilities.

Ensures all file operations remain strictly contained within approved workspace directories.
"""

import os
from pathlib import Path
from apps.conversions.security.exceptions import PathTraversalAttempt


def resolve_safe_path(base_dir: str | Path, target_path: str | Path) -> Path:
    """
    Resolve target_path relative to base_dir and verify containment.

    Checks:
    - Null bytes in input path strings.
    - UNC network paths (\\\\server\\share).
    - Relative traversal escape attempts (../, ..\\).
    - Absolute path overrides.
    - Symlink / junction point escapes outside base_dir.

    Returns
    -------
    Path
        Canonical resolved absolute Path inside base_dir.

    Raises
    ------
    PathTraversalAttempt
        If target_path attempts to break out of base_dir.
    """
    target_str = str(target_path)
    if "\x00" in target_str:
        raise PathTraversalAttempt("Path string contains invalid null byte character.")

    # Check UNC network paths
    if target_str.startswith(("\\\\", "//")):
        raise PathTraversalAttempt("UNC network paths are prohibited.")

    base_resolved = Path(base_dir).resolve()

    # Handle join if target_path is relative, or resolve directly if absolute
    try:
        p = Path(target_path)
        if not p.is_absolute():
            resolved = (base_resolved / p).resolve()
        else:
            resolved = p.resolve()
    except Exception as exc:
        raise PathTraversalAttempt(f"Failed to resolve target path safely: {exc}") from exc

    # Enforce containment check via relative_to
    try:
        resolved.relative_to(base_resolved)
    except ValueError:
        raise PathTraversalAttempt(
            f"Path '{target_str}' escapes the authorized directory '{base_resolved}'."
        )

    return resolved


def validate_path_containment(path: str | Path, allowed_dir: str | Path) -> Path:
    """
    Verify that an existing path resides strictly within allowed_dir.

    Returns
    -------
    Path
        Canonical resolved path.

    Raises
    ------
    PathTraversalAttempt
        If path is not inside allowed_dir.
    """
    return resolve_safe_path(allowed_dir, path)
