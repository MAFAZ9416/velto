"""
CsvToPngEngine — converts CSV files to PNG images or ZIP archives of PNG pages.

Pipeline:
  CSV → CsvToPdfEngine → Intermediate PDF → PdfToPngEngine → PNG Image(s) / ZIP

Reuses existing conversion engines:
  1. CsvToPdfEngine: Converts CSV → intermediate PDF via CsvToXlsxEngine & LibreOffice.
  2. PdfToPngEngine: Renders PDF → single PNG or ZIP archive using PyMuPDF.

All temporary intermediate files are safely managed and cleaned up in an isolated directory.
"""

import logging
import tempfile
from pathlib import Path

from apps.conversions.engines.base import BaseConversionEngine
from apps.conversions.engines.csv_to_pdf import CsvToPdfEngine
from apps.conversions.engines.pdf_to_image import PdfToPngEngine
from apps.conversions.engines.validators import validate_csv_signature

logger = logging.getLogger(__name__)


class CsvToPngEngine(BaseConversionEngine):
    """
    Converts a CSV file to PNG image(s) using composed CsvToPdfEngine and PdfToPngEngine.

    - 1-page output → .png image.
    - Multi-page output → .zip archive containing page-001.png, page-002.png, ...
    """

    source_format = "csv"
    target_format = "png"

    def convert(self, input_path: str, output_path: str) -> str | None:
        """
        Convert CSV file to PNG image or ZIP archive.

        Parameters
        ----------
        input_path : str
            Absolute path to input CSV file.
        output_path : str
            Target output path provided by ConversionService.

        Returns
        -------
        str | None
            The actual output file path (e.g. .png or .zip), or None.
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

            # Step B: Intermediate PDF → PNG using PdfToPngEngine
            png_engine = PdfToPngEngine()
            result_path = png_engine.convert(str(intermediate_pdf), output_path)

            logger.info("CsvToPngEngine: successfully converted CSV to PNG/ZIP: %s", result_path or output_path)
            return result_path
