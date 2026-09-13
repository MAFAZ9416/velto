"""
PdfToJpgEngine & PdfToPngEngine — render PDF pages into JPG or PNG image files.

Uses PyMuPDF (pymupdf) for reliable, high-performance rendering:
  - Renders every page of the PDF preserving page order.
  - Renders pages at 2x scale (~144 DPI) for crisp text and graphics.
  - For 1-page PDFs: returns a single image file (.jpg or .png).
  - For multi-page PDFs: returns a ZIP archive containing page-001.jpg, page-002.jpg, etc.
  - Validates output images and ZIP archives before reporting success.
  - Uses isolated working directories to prevent overwriting files across concurrent jobs.

This engine contains NO HTTP, Django, or database code.
All I/O and lifecycle management lives in ConversionService.
"""

import logging
import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Optional

from apps.conversions.engines.base import BaseConversionEngine, ConversionError
from apps.conversions.engines.validators import (
    validate_image_file,
    validate_pdf_signature,
    validate_zip_archive,
)

logger = logging.getLogger(__name__)


def _render_pdf_to_images(
    input_path: str, output_path: str, target_format: str
) -> str:
    """
    Core implementation for converting PDF to JPG or PNG images.

    Parameters
    ----------
    input_path : str
        Path to input PDF file.
    output_path : str
        Target output path provided by ConversionService (e.g., /tmp/.../uuid_output.jpg).
    target_format : str
        "jpg" or "png".

    Returns
    -------
    str
        The final output file path (may end with .zip if multi-page).
    """
    # ── Step 1: Validate input PDF signature ──────────────────────────────────
    validate_pdf_signature(input_path)

    # ── Step 2: Import PyMuPDF ────────────────────────────────────────────────
    try:
        import pymupdf
    except ImportError as exc:
        raise ConversionError(
            "PyMuPDF (pymupdf) is not installed. Run: pip install pymupdf"
        ) from exc

    # ── Step 3: Open PDF document ─────────────────────────────────────────────
    doc = None
    try:
        doc = pymupdf.open(input_path)
    except Exception as exc:
        raise ConversionError(
            f"Failed to open PDF document. The file may be corrupt: {exc}"
        ) from exc

    try:
        # Check encryption
        if doc.is_encrypted:
            if not doc.authenticate(""):
                raise ConversionError(
                    "The PDF is password-protected or encrypted. Please provide an unlocked PDF."
                )

        page_count = len(doc)
        if page_count == 0:
            raise ConversionError("The PDF contains no pages (0 pages).")

        # ── Step 4: Setup isolated temporary work directory ───────────────────
        # Prevents file collisions and ensures clean teardown.
        with tempfile.TemporaryDirectory(prefix="velto_pdf_img_") as tmp_dir:
            tmp_path = Path(tmp_dir)

            # PyMuPDF zoom matrix: 2.0x = ~144 DPI for crisp readable text/images
            matrix = pymupdf.Matrix(2.0, 2.0)
            fmt = target_format.lower()
            ext = ".jpg" if fmt in ("jpg", "jpeg") else ".png"
            image_ext_label = "jpg" if fmt in ("jpg", "jpeg") else "png"

            # ── Single-page PDF ───────────────────────────────────────────────
            if page_count == 1:
                page = doc.load_page(0)
                # For JPG, alpha must be False (JPEG has no transparency support)
                alpha_channel = False if fmt in ("jpg", "jpeg") else True
                pix = page.get_pixmap(matrix=matrix, alpha=alpha_channel)

                # Ensure output directory exists
                out_p = Path(output_path)
                out_p.parent.mkdir(parents=True, exist_ok=True)

                pix.save(str(out_p))

                # Validate single image file
                validate_image_file(str(out_p), expected_format="JPEG" if fmt in ("jpg", "jpeg") else "PNG")
                logger.info(
                    "PdfToImageEngine: converted 1-page PDF to %s: %s",
                    target_format.upper(),
                    out_p,
                )
                return str(out_p)

            # ── Multi-page PDF → ZIP archive ─────────────────────────────────
            page_files = []
            for page_index in range(page_count):
                page = doc.load_page(page_index)
                alpha_channel = False if fmt in ("jpg", "jpeg") else True
                pix = page.get_pixmap(matrix=matrix, alpha=alpha_channel)

                page_fname = f"page-{page_index + 1:03d}{ext}"
                page_img_path = tmp_path / page_fname
                pix.save(str(page_img_path))
                page_files.append((page_fname, page_img_path))

            # Determine final zip output path
            out_p = Path(output_path)
            zip_output_path = out_p.with_suffix(".zip")
            zip_output_path.parent.mkdir(parents=True, exist_ok=True)

            # Create ZIP archive
            with zipfile.ZipFile(zip_output_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for page_fname, page_img_path in page_files:
                    zf.write(page_img_path, arcname=page_fname)

            # Validate ZIP archive & every contained page image
            validate_zip_archive(
                str(zip_output_path),
                expected_count=page_count,
                expected_ext=ext,
            )

            logger.info(
                "PdfToImageEngine: converted %d-page PDF to ZIP (%s): %s",
                page_count,
                target_format.upper(),
                zip_output_path,
            )
            return str(zip_output_path)

    finally:
        if doc is not None:
            try:
                doc.close()
            except Exception:  # noqa: BLE001
                pass


class PdfToJpgEngine(BaseConversionEngine):
    """
    Converts a PDF file to JPG images using PyMuPDF.

    - 1-page PDF → .jpg image.
    - Multi-page PDF → .zip archive containing page-001.jpg, page-002.jpg, ...
    """

    source_format = "pdf"
    target_format = "jpg"

    def convert(self, input_path: str, output_path: str) -> str | None:
        return _render_pdf_to_images(input_path, output_path, "jpg")


class PdfToPngEngine(BaseConversionEngine):
    """
    Converts a PDF file to PNG images using PyMuPDF.

    - 1-page PDF → .png image.
    - Multi-page PDF → .zip archive containing page-001.png, page-002.png, ...
    """

    source_format = "pdf"
    target_format = "png"

    def convert(self, input_path: str, output_path: str) -> str | None:
        return _render_pdf_to_images(input_path, output_path, "png")
