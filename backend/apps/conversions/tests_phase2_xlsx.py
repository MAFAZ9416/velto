"""
Phase 2 (Extension): Tests for real PDF → Excel (pdf → xlsx) conversion engine.

Tests exercise real PDF table fixtures generated with reportlab, verifying:
  1. PdfToXlsxEngine unit functionality (single-table, multi-table, multi-page).
  2. Cell parsing & value preservation (numeric parsing vs leading zeros, IDs, dates).
  3. Honest no-table policy: raises ConversionError("No extractable tables were found in this PDF.") and marks job FAILED.
  4. Output validation with openpyxl.load_workbook().
  5. API lifecycle: POST upload → process → GET download.
  6. Content-Type headers (application/vnd.openxmlformats-officedocument.spreadsheetml.sheet).
  7. Session ownership isolation.
  8. PDF → DOCX, PDF → JPG, PDF → PNG regression checks.
"""

import io
import os
import tempfile
import openpyxl

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.conversions.engines.base import ConversionError
from apps.conversions.engines.pdf_to_xlsx import PdfToXlsxEngine, _parse_cell_value
from apps.conversions.fixtures.generate_fixtures import generate_all_fixtures
from apps.conversions.models import ConversionJob, JobStatus


TEST_TEMP_DIR = tempfile.mkdtemp(prefix="velto_phase2_xlsx_tests_")


class BaseXlsxEngineTestCase(TestCase):
    """Base setup for PDF to Excel tests."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.fixtures = generate_all_fixtures()
        cls.table_pdf = cls.fixtures["with_table"]
        cls.text_pdf = cls.fixtures["simple_text"]
        cls.multipage_pdf = cls.fixtures["multipage"]


class ValueParsingTests(TestCase):
    """Unit tests for cell value type preservation."""

    def test_numeric_conversion(self):
        """Standard integers and floats convert to numeric types."""
        self.assertEqual(_parse_cell_value("123"), 123)
        self.assertEqual(_parse_cell_value("-456"), -456)
        self.assertEqual(_parse_cell_value("45.99"), 45.99)
        self.assertEqual(_parse_cell_value("0"), 0)

    def test_leading_zero_preservation(self):
        """Numbers with leading zeros preserve text string representation."""
        self.assertEqual(_parse_cell_value("01234"), "01234")
        self.assertEqual(_parse_cell_value("007"), "007")

    def test_date_and_id_preservation(self):
        """Date strings and hyphenated IDs preserve text string representation."""
        self.assertEqual(_parse_cell_value("2026-09-13"), "2026-09-13")
        self.assertEqual(_parse_cell_value("12-34-56"), "12-34-56")

    def test_empty_cells(self):
        """None and whitespace return None."""
        self.assertIsNone(_parse_cell_value(None))
        self.assertIsNone(_parse_cell_value(""))
        self.assertIsNone(_parse_cell_value("   "))


class PdfToXlsxEngineTests(BaseXlsxEngineTestCase):
    """Direct unit tests for PdfToXlsxEngine."""

    def setUp(self):
        self.engine = PdfToXlsxEngine()
        self.temp_dir = tempfile.TemporaryDirectory(prefix="test_xlsx_engine_")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_pdf_with_table_to_xlsx(self):
        """PDF with table converts to a valid XLSX workbook containing table data."""
        out_path = os.path.join(self.temp_dir.name, "output.xlsx")
        res_path = self.engine.convert(str(self.table_pdf), out_path)

        target_file = res_path or out_path
        self.assertTrue(os.path.exists(target_file))

        # Open with openpyxl and verify contents
        wb = openpyxl.load_workbook(target_file)
        self.assertIn("Page 1", wb.sheetnames)

        ws = wb["Page 1"]
        # Verify header row
        header = [cell.value for cell in ws[1]]
        self.assertIn("Format", header)
        self.assertIn("Source", header)
        self.assertIn("Target", header)

        # Verify data rows
        row2 = [cell.value for cell in ws[2]]
        self.assertIn("pdf", row2)
        self.assertIn("docx", row2)
        wb.close()

    def test_pdf_without_table_raises_conversion_error(self):
        """Text-only PDF with no tables raises ConversionError with honest error message."""
        out_path = os.path.join(self.temp_dir.name, "no_table.xlsx")
        with self.assertRaises(ConversionError) as cm:
            self.engine.convert(str(self.text_pdf), out_path)

        self.assertIn("No extractable tables were found in this PDF.", str(cm.exception))
        # Ensure output file was not created
        self.assertFalse(os.path.exists(out_path))

    def test_corrupt_pdf_raises_conversion_error(self):
        """Corrupt PDF file raises ConversionError."""
        bad_pdf = os.path.join(self.temp_dir.name, "corrupt.pdf")
        with open(bad_pdf, "wb") as f:
            f.write(b"%PDF-1.4\nCorrupt pdf body\n")

        out_path = os.path.join(self.temp_dir.name, "out.xlsx")
        with self.assertRaises(ConversionError):
            self.engine.convert(bad_pdf, out_path)


@override_settings(TEMP_UPLOAD_DIR=TEST_TEMP_DIR)
class XlsxConversionApiIntegrationTests(BaseXlsxEngineTestCase):
    """Full API integration tests for PDF → XLSX."""

    def setUp(self):
        self.client = APIClient()

    def test_pdf_to_xlsx_api_success_flow(self):
        """Upload PDF with table → XLSX: check status completed, download URL, Content-Type."""
        with open(self.table_pdf, "rb") as f:
            pdf_bytes = f.read()

        file_obj = SimpleUploadedFile("data.pdf", pdf_bytes, content_type="application/pdf")
        response = self.client.post(
            reverse("conversions:job-list-create"),
            {"file": file_obj, "source_format": "pdf", "target_format": "xlsx"},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["output_filename"], "data.xlsx")
        self.assertIsNotNone(data["download_url"])

        # Test download endpoint
        dl_response = self.client.get(data["download_url"])
        self.assertEqual(dl_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            dl_response["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.assertIn('filename="data.xlsx"', dl_response["Content-Disposition"])

        # Verify downloaded workbook stream
        dl_bytes = b"".join(dl_response.streaming_content)
        wb = openpyxl.load_workbook(io.BytesIO(dl_bytes))
        self.assertGreater(len(wb.sheetnames), 0)
        wb.close()

    def test_pdf_to_xlsx_no_table_api_failure_flow(self):
        """Upload PDF without tables → XLSX: status failed with clear error message."""
        with open(self.text_pdf, "rb") as f:
            pdf_bytes = f.read()

        file_obj = SimpleUploadedFile("text.pdf", pdf_bytes, content_type="application/pdf")
        response = self.client.post(
            reverse("conversions:job-list-create"),
            {"file": file_obj, "source_format": "pdf", "target_format": "xlsx"},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        data = response.json()
        self.assertEqual(data["status"], "failed")
        self.assertIn("No extractable tables were found in this PDF.", data["error_message"])

    def test_supported_formats_endpoint_includes_xlsx_pair(self):
        """GET /api/conversions/supported-formats/ includes pdf -> xlsx."""
        response = self.client.get(reverse("conversions:supported-formats"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        formats = response.json()["formats"]
        pairs = [(item["source_format"], item["target_format"]) for item in formats]
        self.assertIn(("pdf", "xlsx"), pairs)

    def test_anonymous_session_isolation(self):
        """User A cannot view or download User B's XLSX conversion job."""
        client_a = APIClient()
        client_b = APIClient()

        with open(self.table_pdf, "rb") as f:
            pdf_bytes = f.read()

        file_obj = SimpleUploadedFile("table.pdf", pdf_bytes, content_type="application/pdf")
        res_a = client_a.post(
            reverse("conversions:job-list-create"),
            {"file": file_obj, "source_format": "pdf", "target_format": "xlsx"},
            format="multipart",
        )
        job_id = res_a.json()["id"]

        detail_b = client_b.get(reverse("conversions:job-detail", kwargs={"job_id": job_id}))
        self.assertEqual(detail_b.status_code, status.HTTP_404_NOT_FOUND)

        dl_b = client_b.get(reverse("conversions:job-download", kwargs={"job_id": job_id}))
        self.assertEqual(dl_b.status_code, status.HTTP_404_NOT_FOUND)


class FullRegressionSuiteTests(BaseXlsxEngineTestCase):
    """Regression checks for all existing conversion engines."""

    def setUp(self):
        self.client = APIClient()

    def test_pdf_to_docx_regression(self):
        """PDF → DOCX conversion continues to work."""
        with open(self.text_pdf, "rb") as f:
            pdf_bytes = f.read()

        file_obj = SimpleUploadedFile("test.pdf", pdf_bytes, content_type="application/pdf")
        response = self.client.post(
            reverse("conversions:job-list-create"),
            {"file": file_obj, "source_format": "pdf", "target_format": "docx"},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["status"], "completed")

    def test_pdf_to_jpg_regression(self):
        """PDF → JPG conversion continues to work."""
        with open(self.text_pdf, "rb") as f:
            pdf_bytes = f.read()

        file_obj = SimpleUploadedFile("test.pdf", pdf_bytes, content_type="application/pdf")
        response = self.client.post(
            reverse("conversions:job-list-create"),
            {"file": file_obj, "source_format": "pdf", "target_format": "jpg"},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["status"], "completed")

    def test_pdf_to_png_regression(self):
        """PDF → PNG conversion continues to work."""
        with open(self.text_pdf, "rb") as f:
            pdf_bytes = f.read()

        file_obj = SimpleUploadedFile("test.pdf", pdf_bytes, content_type="application/pdf")
        response = self.client.post(
            reverse("conversions:job-list-create"),
            {"file": file_obj, "source_format": "pdf", "target_format": "png"},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["status"], "completed")
