"""
OCR Discovery and Diagnostic Utilities for VELTO Conversion.

Provides:
  - Automatic discovery of Tesseract OCR executable across PATH and Windows default paths.
  - OCR engine availability and language pack diagnostic functions.
  - Validation of user-requested OCR language options (including Tamil 'tam').
"""

import logging
import os
from pathlib import Path
import shutil
from typing import TypedDict

from django.conf import settings
from apps.conversions.engines.base import ConversionError

logger = logging.getLogger(__name__)

# Standard Windows installation paths for Tesseract OCR
WIN_TESSERACT_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
]


class OCREngineInfo(TypedDict):
    available: bool
    tesseract_cmd: str | None
    version: str | None
    languages: list[str]
    has_tamil: bool
    error: str | None


def discover_tesseract_cmd() -> str | None:
    """
    Find the Tesseract OCR executable on the system.

    Checks:
    1. Environment variable TESSERACT_CMD
    2. Django setting TESSERACT_CMD
    3. System PATH via shutil.which('tesseract')
    4. Common Windows installation directories
    """
    # 1. Environment variable
    env_cmd = os.environ.get("TESSERACT_CMD")
    if env_cmd and Path(env_cmd).exists():
        return env_cmd

    # 2. Django settings
    settings_cmd = getattr(settings, "TESSERACT_CMD", None)
    if settings_cmd and Path(settings_cmd).exists():
        return settings_cmd

    # 3. PATH discovery
    path_cmd = shutil.which("tesseract")
    if path_cmd:
        return path_cmd

    # 4. Standard Windows locations
    for win_path in WIN_TESSERACT_PATHS:
        if Path(win_path).exists():
            return win_path

    return None


def configure_pytesseract() -> str | None:
    """
    Configure pytesseract's tesseract_cmd setting.
    Returns the resolved tesseract_cmd path or None.
    """
    cmd_path = discover_tesseract_cmd()
    if cmd_path:
        try:
            import pytesseract
            pytesseract.pytesseract.tesseract_cmd = cmd_path
        except ImportError:
            pass
    return cmd_path


def get_ocr_engine_info() -> OCREngineInfo:
    """
    Query the system for OCR engine availability and language packs.
    """
    cmd_path = configure_pytesseract()

    try:
        import pytesseract
    except ImportError:
        return {
            "available": False,
            "tesseract_cmd": None,
            "version": None,
            "languages": [],
            "has_tamil": False,
            "error": "ocr_wrapper_missing: Python library 'pytesseract' is not installed.",
        }

    if not cmd_path:
        return {
            "available": False,
            "tesseract_cmd": None,
            "version": None,
            "languages": [],
            "has_tamil": False,
            "error": (
                "ocr_engine_unavailable: Tesseract OCR executable was not found on the system. "
                "Please install Tesseract OCR and add it to PATH or set TESSERACT_CMD."
            ),
        }

    try:
        version_str = str(pytesseract.get_tesseract_version()).strip()
        installed_langs = pytesseract.get_languages(config="")
        has_tamil = "tam" in installed_langs
        return {
            "available": True,
            "tesseract_cmd": cmd_path,
            "version": version_str,
            "languages": installed_langs,
            "has_tamil": has_tamil,
            "error": None,
        }
    except Exception as exc:
        logger.warning("Failed to query Tesseract OCR engine info: %s", exc)
        return {
            "available": False,
            "tesseract_cmd": cmd_path,
            "version": None,
            "languages": [],
            "has_tamil": False,
            "error": f"ocr_engine_error: Failed to query Tesseract executable ({exc}).",
        }


def validate_ocr_language(requested_lang: str | None = None) -> str:
    """
    Validate that the requested language code(s) (e.g., 'eng', 'tam', 'eng+tam')
    are installed and available in the local Tesseract OCR engine.

    Raises
    ------
    ConversionError
        If Tesseract is unavailable or requested language data is missing.
    """
    engine_info = get_ocr_engine_info()
    if not engine_info["available"]:
        raise ConversionError(
            engine_info["error"]
            or "ocr_engine_unavailable: OCR engine (Tesseract) is not installed or accessible in this environment."
        )

    if not requested_lang:
        lang_str = "eng"
    else:
        lang_str = str(requested_lang).strip().lower()

    if not lang_str:
        lang_str = "eng"

    installed_langs = set(engine_info["languages"])
    requested_parts = [p.strip() for p in lang_str.split("+") if p.strip()]

    for part in requested_parts:
        if part not in installed_langs:
            if part == "tam":
                raise ConversionError(
                    "ocr_language_unavailable: Tamil OCR language pack ('tam') is not installed in Tesseract. "
                    "Please install the Tamil traineddata language pack (tam.traineddata) or select 'eng'."
                )
            raise ConversionError(
                f"ocr_language_unavailable: Requested OCR language pack '{part}' is not installed in Tesseract OCR."
            )

    return "+".join(requested_parts)
