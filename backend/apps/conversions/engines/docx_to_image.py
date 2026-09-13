"""
DocxToJpgEngine & DocxToPngEngine — convert DOCX files to JPG or PNG images.

Pipeline:
  DOCX → DocxToPdfEngine → Intermediate PDF → PdfToJpgEngine/PdfToPngEngine → Image(s) / ZIP

Reuses existing conversion engines:
  1. DocxToPdfEngine: Converts DOCX → intermediate PDF via LibreOffice headless mode.
  2. PdfToJpgEngine / PdfToPngEngine: Renders PDF → single image or ZIP archive using PyMuPDF.

All temporary intermediate files and profiles are safely managed and cleaned up in an isolated directory.
"""

import logging
import tempfile
from pathlib import Path

from apps.conversions.engines.base import BaseConversionEngine, ConversionError
from apps.conversions.engines.docx_to_pdf import DocxToPdfEngine
from apps.conversions.engines.pdf_to_image import PdfToJpgEngine, PdfToPngEngine
from apps.conversions.engines.validators import validate_docx_signature

logger = logging.getLogger(__name__)


def _convert_docx_to_image(
    input_path: str, output_path: str, target_format: str
) -> str | None:
    """
    Shared orchestration logic for DOCX → JPG / PNG conversion.

    Parameters
    ----------
    input_path : str
        Path to input DOCX file.
    output_path : str
        Target output path provided by ConversionService.
    target_format : str
        "jpg" or "png".

    Returns
    -------
    str | None
        The actual output file path (e.g. .jpg, .png, or .zip), or None.
    """
    # 1. Validate DOCX signature prior to conversion
    validate_docx_signature(input_path)

    # 2. Create isolated temporary working directory for intermediate PDF
    with tempfile.TemporaryDirectory(prefix="velto_docx_img_") as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        intermediate_pdf = tmp_dir / "intermediate.pdf"

        # Step A: DOCX → Intermediate PDF using existing DocxToPdfEngine
        pdf_engine = DocxToPdfEngine()
        pdf_engine.convert(input_path, str(intermediate_pdf))

        # Step B: Intermediate PDF → JPG or PNG using existing image engines
        fmt = target_format.lower()
        if fmt in ("jpg", "jpeg"):
            image_engine = PdfToJpgEngine()
        else:
            image_engine = PdfToPngEngine()

        result_path = image_engine.convert(str(intermediate_pdf), output_path)
        return result_path


class DocxToJpgEngine(BaseConversionEngine):
    """
    Converts a DOCX file to JPG images using composed DocxToPdfEngine and PdfToJpgEngine.

    - 1-page DOCX → .jpg image.
    - Multi-page DOCX → .zip archive containing page-001.jpg, page-002.jpg, ...
    """

    source_format = "docx"
    target_format = "jpg"

    def convert(self, input_path: str, output_path: str) -> str | None:
        return _convert_docx_to_image(input_path, output_path, "jpg")


class DocxToPngEngine(BaseConversionEngine):
    """
    Converts a DOCX file to PNG images using composed DocxToPdfEngine and PdfToPngEngine.

    - 1-page DOCX → .png image.
    - Multi-page DOCX → .zip archive containing page-001.png, page-002.png, ...
    """

    source_format = "docx"
    target_format = "png"

    def convert(self, input_path: str, output_path: str) -> str | None:
        return _convert_docx_to_image(input_path, output_path, "png")
