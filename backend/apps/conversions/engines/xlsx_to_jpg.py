"""
XlsxToJpgEngine — convert XLSX files to JPG images.

Pipeline:
  XLSX → XlsxToPdfEngine → Intermediate PDF → PdfToJpgEngine → Image(s) / ZIP

Reuses existing conversion engines:
  1. XlsxToPdfEngine: Converts XLSX → intermediate PDF via LibreOffice headless mode.
  2. PdfToJpgEngine: Renders PDF → single image or ZIP archive using PyMuPDF.

All temporary intermediate files and profiles are safely managed and cleaned up in an isolated directory.
"""

import logging
import tempfile
from pathlib import Path

from apps.conversions.engines.base import BaseConversionEngine
from apps.conversions.engines.pdf_to_image import PdfToJpgEngine, PdfToPngEngine
from apps.conversions.engines.xlsx_to_pdf import XlsxToPdfEngine
from apps.conversions.engines.validators import validate_xlsx_signature

logger = logging.getLogger(__name__)


def convert_xlsx_to_image(
    input_path: str, output_path: str, target_format: str
) -> str | None:
    """
    Shared orchestration logic for XLSX → JPG / PNG conversion.

    Parameters
    ----------
    input_path : str
        Path to input XLSX file.
    output_path : str
        Target output path provided by ConversionService.
    target_format : str
        "jpg" or "png".

    Returns
    -------
    str | None
        The actual output file path (e.g. .jpg, .png, or .zip), or None.
    """
    # 1. Validate XLSX signature prior to conversion
    validate_xlsx_signature(input_path)

    # 2. Create isolated temporary working directory for intermediate PDF
    with tempfile.TemporaryDirectory(prefix="velto_xlsx_img_") as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        intermediate_pdf = tmp_dir / "intermediate.pdf"

        # Step A: XLSX → Intermediate PDF using existing XlsxToPdfEngine
        pdf_engine = XlsxToPdfEngine()
        pdf_engine.convert(input_path, str(intermediate_pdf))

        # Step B: Intermediate PDF → JPG or PNG using existing image engines
        fmt = target_format.lower()
        if fmt in ("jpg", "jpeg"):
            image_engine = PdfToJpgEngine()
        else:
            image_engine = PdfToPngEngine()

        result_path = image_engine.convert(str(intermediate_pdf), output_path)
        return result_path


class XlsxToJpgEngine(BaseConversionEngine):
    """
    Converts an XLSX file to JPG images using composed XlsxToPdfEngine and PdfToJpgEngine.

    - 1-page output → .jpg image.
    - Multi-page output → .zip archive containing page-001.jpg, page-002.jpg, ...
    """

    source_format = "xlsx"
    target_format = "jpg"

    def convert(self, input_path: str, output_path: str) -> str | None:
        return convert_xlsx_to_image(input_path, output_path, "jpg")
