"""
XlsxToPdfEngine — converts XLSX files to PDF using LibreOffice in headless mode.

Reuses shared LibreOffice execution orchestration from libreoffice.py.
"""

import logging
from pathlib import Path

from apps.conversions.engines.base import BaseConversionEngine, ConversionError
from apps.conversions.engines.libreoffice import run_libreoffice_pdf_conversion
from apps.conversions.engines.validators import validate_xlsx_signature

logger = logging.getLogger(__name__)


class XlsxToPdfEngine(BaseConversionEngine):
    """
    Conversion engine for XLSX → PDF using LibreOffice headless mode.
    """

    source_format = "xlsx"
    target_format = "pdf"

    def convert(self, input_path: str, output_path: str) -> str | None:
        """
        Convert XLSX file to PDF.

        Parameters
        ----------
        input_path : str
            Absolute path to input XLSX file.
        output_path : str
            Absolute destination path for converted PDF.

        Returns
        -------
        str | None
            None, indicating output_path was used directly.
        """
        # 1. Validate XLSX signature
        validate_xlsx_signature(input_path)

        # 2. Perform conversion via shared LibreOffice helper
        run_libreoffice_pdf_conversion(input_path, output_path, format_label="XLSX")
        return None
