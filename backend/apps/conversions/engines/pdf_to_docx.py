"""
PdfToDocxEngine — converts a PDF file to an editable DOCX document.

Uses pdf2docx (https://github.com/ArtifexSoftware/pdf2docx) which:
  - Extracts text, layout, tables, and images from the PDF.
  - Reconstructs them as an editable Word document.
  - Is entirely local — no network calls, no cloud APIs.

Important limitations (honest):
  - Scanned PDFs (images-only, no embedded text) will produce a DOCX with
    embedded images rather than editable text. This is correct behaviour,
    not a bug. A future OCR pipeline will address this.
  - Complex multi-column layouts may not be preserved perfectly.
  - Embedded fonts not present on the host system may be substituted.
  - Password-protected PDFs are not supported and will raise ConversionError.

This engine contains NO HTTP, Django, or database code.
All I/O and lifecycle management lives in ConversionService.
"""

import logging
from pathlib import Path

from apps.conversions.engines.base import BaseConversionEngine, ConversionError
from apps.conversions.engines.validators import validate_output_file, validate_pdf_signature

logger = logging.getLogger(__name__)


class PdfToDocxEngine(BaseConversionEngine):
    """
    Converts a PDF file to an editable Word (.docx) document using pdf2docx.

    Attributes
    ----------
    source_format : str
        "pdf"
    target_format : str
        "docx"
    """

    source_format = "pdf"
    target_format = "docx"

    def convert(self, input_path: str, output_path: str) -> None:
        """
        Run the PDF → DOCX conversion.

        Parameters
        ----------
        input_path : str
            Absolute path to the staged PDF file.
        output_path : str
            Absolute path where the DOCX file should be written.

        Raises
        ------
        ConversionError
            For known, recoverable failures (bad PDF, encrypted PDF, etc.).
        Exception
            For unexpected library errors — ConversionService will catch these.
        """
        # ── Step 1: Validate input ─────────────────────────────────────────────
        validate_pdf_signature(input_path)

        # ── Step 2: Ensure output directory exists ─────────────────────────────
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            "PdfToDocxEngine: starting conversion %s → %s",
            input_path,
            output_path,
        )

        # ── Step 3: Run pdf2docx ───────────────────────────────────────────────
        # Import here so ImportError surfaces only if this engine is actually used.
        try:
            from pdf2docx import Converter
        except ImportError as exc:
            raise ConversionError(
                "pdf2docx is not installed. "
                "Run: pip install pdf2docx"
            ) from exc

        cv = None
        try:
            cv = Converter(input_path)
            cv.convert(output_path, start=0, end=None)
        except Exception as exc:
            # pdf2docx raises generic Exception subclasses for many error types.
            # Translate common patterns into ConversionError so the service
            # layer can store a clean message without leaking internal details.
            msg = str(exc).lower()

            if "password" in msg or "encrypted" in msg:
                raise ConversionError(
                    "The PDF is password-protected or encrypted. "
                    "Please provide an unlocked PDF."
                ) from exc

            if "no pages" in msg or "empty" in msg:
                raise ConversionError(
                    "The PDF contains no readable pages. "
                    "It may be corrupted or a scanned document without embedded text."
                ) from exc

            # Re-raise unknown exceptions — the service layer will catch them.
            raise

        finally:
            # ── Step 4: Always close the Converter to release file handles ─────
            if cv is not None:
                try:
                    cv.close()
                except Exception:  # noqa: BLE001
                    logger.warning(
                        "PdfToDocxEngine: failed to close Converter cleanly for %s",
                        input_path,
                    )

        # ── Step 5: Verify output ──────────────────────────────────────────────
        validate_output_file(output_path)

        output_size = Path(output_path).stat().st_size
        logger.info(
            "PdfToDocxEngine: conversion completed. Output: %s (%d bytes)",
            output_path,
            output_size,
        )
