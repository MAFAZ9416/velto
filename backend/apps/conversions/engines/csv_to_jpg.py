"""
CsvToJpgEngine — converts CSV files to JPG images or ZIP archives of JPG pages.

Pipeline:
  CSV → CsvToPdfEngine → Intermediate PDF → PdfToJpgEngine → JPG Image(s) / ZIP

Reuses existing conversion engines:
  1. CsvToPdfEngine: Converts CSV → intermediate PDF via CsvToXlsxEngine & LibreOffice.
  2. PdfToJpgEngine: Renders PDF → single JPG or ZIP archive using PyMuPDF.

All temporary intermediate files are safely managed and cleaned up in an isolated directory.
"""

import logging
import tempfile
from pathlib import Path

from apps.conversions.engines.base import BaseConversionEngine
from apps.conversions.engines.csv_to_pdf import CsvToPdfEngine
from apps.conversions.engines.pdf_to_image import PdfToJpgEngine
from apps.conversions.engines.validators import validate_csv_signature

logger = logging.getLogger(__name__)


class CsvToJpgEngine(BaseConversionEngine):
    """
    Converts a CSV file to JPG image(s) using composed CsvToPdfEngine and PdfToJpgEngine.

    - 1-page output → .jpg image.
    - Multi-page output → .zip archive containing page-001.jpg, page-002.jpg, ...
    """

    source_format = "csv"
    target_format = "jpg"

    def convert(self, input_path: str, output_path: str) -> str | None:
        """
        Convert CSV file to JPG image or ZIP archive.

        Parameters
        ----------
        input_path : str
            Absolute path to input CSV file.
        output_path : str
            Target output path provided by ConversionService.

        Returns
        -------
        str | None
            The actual output file path (e.g. .jpg or .zip), or None.
        """
        # 1. Validate CSV signature prior to conversion
        validate_csv_signature(input_path)

        # 2. Create isolated temporary working directory for intermediate PDF
        with tempfile.TemporaryDirectory(prefix="velto_csv_img_") as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            intermediate_pdf = tmp_dir / "intermediate.pdf"

            # Step A: CSV → Intermediate PDF using CsvToPdfEngine
            csv_pdf_engine = CsvToPdfEngine()
            csv_pdf_engine.convert(input_path, str(intermediate_pdf))

            # Step B: Intermediate PDF → JPG using PdfToJpgEngine
            jpg_engine = PdfToJpgEngine()
            result_path = jpg_engine.convert(str(intermediate_pdf), output_path)

            logger.info("CsvToJpgEngine: successfully converted CSV to JPG/ZIP: %s", result_path or output_path)
            return result_path
