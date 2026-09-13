"""
CsvToPdfEngine — converts CSV files to PDF documents.

Pipeline:
  Uploaded CSV → validate_csv_signature → CsvToXlsxEngine → Temporary XLSX → XlsxToPdfEngine (LibreOffice) → PDF Output
"""

import logging
import os
import tempfile
from pathlib import Path

from apps.conversions.engines.base import BaseConversionEngine, ConversionError
from apps.conversions.engines.csv_to_xlsx import CsvToXlsxEngine
from apps.conversions.engines.xlsx_to_pdf import XlsxToPdfEngine
from apps.conversions.engines.validators import validate_csv_signature, validate_pdf_output

logger = logging.getLogger(__name__)


class CsvToPdfEngine(BaseConversionEngine):
    """
    Conversion engine for CSV → PDF.

    Reuses CsvToXlsxEngine for robust CSV parsing & workbook styling,
    and XlsxToPdfEngine for high-fidelity PDF rendering via LibreOffice.
    """

    source_format = "csv"
    target_format = "pdf"

    def convert(self, input_path: str, output_path: str) -> str | None:
        """
        Convert CSV file to PDF document.

        Parameters
        ----------
        input_path : str
            Absolute path to input CSV file.
        output_path : str
            Absolute destination path for converted PDF file.

        Returns
        -------
        str | None
            None, indicating output_path was used directly.
        """
        # 1. Validate CSV input file signature
        validate_csv_signature(input_path)

        # 2. Prepare temporary directory for intermediate XLSX file
        with tempfile.TemporaryDirectory(prefix="velto_csv2pdf_") as temp_dir:
            temp_xlsx = os.path.join(temp_dir, "intermediate.xlsx")

            # 3. Convert CSV → XLSX using CsvToXlsxEngine
            csv_engine = CsvToXlsxEngine()
            csv_engine.convert(input_path, temp_xlsx)

            # 4. Convert intermediate XLSX → PDF using XlsxToPdfEngine
            xlsx_engine = XlsxToPdfEngine()
            xlsx_engine.convert(temp_xlsx, output_path)

            # 5. Validate final PDF output
            validate_pdf_output(output_path)

            logger.info("CsvToPdfEngine: successfully converted CSV to PDF: %s", output_path)
            return None
