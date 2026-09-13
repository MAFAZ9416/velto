"""
XlsxToPngEngine — convert XLSX files to PNG images.

Pipeline:
  XLSX → XlsxToPdfEngine → Intermediate PDF → PdfToPngEngine → Image(s) / ZIP

Reuses existing conversion engines:
  1. XlsxToPdfEngine: Converts XLSX → intermediate PDF via LibreOffice headless mode.
  2. PdfToPngEngine: Renders PDF → single image or ZIP archive using PyMuPDF.

All temporary intermediate files and profiles are safely managed and cleaned up in an isolated directory.
"""

import logging

from apps.conversions.engines.base import BaseConversionEngine
from apps.conversions.engines.xlsx_to_jpg import convert_xlsx_to_image

logger = logging.getLogger(__name__)


class XlsxToPngEngine(BaseConversionEngine):
    """
    Converts an XLSX file to PNG images using composed XlsxToPdfEngine and PdfToPngEngine.

    - 1-page output → .png image.
    - Multi-page output → .zip archive containing page-001.png, page-002.png, ...
    """

    source_format = "xlsx"
    target_format = "png"

    def convert(self, input_path: str, output_path: str) -> str | None:
        return convert_xlsx_to_image(input_path, output_path, "png")
