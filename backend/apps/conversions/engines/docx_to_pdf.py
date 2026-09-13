"""
DocxToPdfEngine — converts DOCX files to PDF using LibreOffice in headless mode.

Reuses shared LibreOffice execution orchestration from libreoffice.py.
"""

import logging
from pathlib import Path

from apps.conversions.engines.base import BaseConversionEngine, ConversionError
from apps.conversions.engines.libreoffice import (
    find_libreoffice_executable,
    run_libreoffice_pdf_conversion,
)
from apps.conversions.engines.validators import (
    validate_docx_signature,
    validate_pdf_output,
)


logger = logging.getLogger(__name__)


class DocxToPdfEngine(BaseConversionEngine):
    """
    Conversion engine for DOCX → PDF using LibreOffice headless mode.
    """

    source_format = "docx"
    target_format = "pdf"

    def convert(self, input_path: str, output_path: str) -> str | None:
        """
        Convert DOCX file to PDF.

        Parameters
        ----------
        input_path : str
            Absolute path to input DOCX file.
        output_path : str
            Absolute destination path for converted PDF.

        Returns
        -------
        str | None
            None, indicating output_path was used directly.
        """
        # 1. Validate DOCX signature
        validate_docx_signature(input_path)

        # 2. Perform conversion via shared LibreOffice helper
        run_libreoffice_pdf_conversion(input_path, output_path, format_label="DOCX")
        return None
