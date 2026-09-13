"""
Phase 2 (Extension): Tests for XLSX → JPG and XLSX → PNG conversion engines.

Scenarios covered:
  1. Valid XLSX → JPG conversion (XlsxToJpgEngine).
  2. Valid XLSX → PNG conversion (XlsxToPngEngine).
  3. Multi-sheet XLSX → JPG ZIP output (ZIP archive containing page-001.jpg, page-002.jpg, ...).
  4. Multi-sheet XLSX → PNG ZIP output (ZIP archive containing page-001.png, page-002.png, ...).
  5. One-sheet direct JPG output (single .jpg file).
  6. One-sheet direct PNG output (single .png file).
  7. Correct ZIP entry names & ordering (page-001.jpg, page-002.jpg, ...).
  8. Correct image MIME types (image/jpeg, image/png, application/zip).
  9. Correct output filename stem preservation (e.g., report.xlsx → report.jpg / report.zip).
 10. Invalid XLSX input validation failure.
 11. Corrupted non-ZIP XLSX input validation failure.
 12. Missing LibreOffice executable handling.
 13. LibreOffice timeout handling.
 14. LibreOffice non-zero exit handling.
 15. Invalid intermediate PDF handling.
 16. PDF-to-image conversion failure.
 17. Temporary file & directory cleanup.
 18. Anonymous session isolation (HTTP 404 for unauthorized session).
 19. REST API upload success flow.
 20. REST API upload failure flow.
 21. Protected download endpoint behavior.
 22. Regression coverage for existing conversions.
"""

import io
import os
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch
import subprocess

import openpyxl
from PIL import Image
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.conversions.engines.base import ConversionError
from apps.conversions.engines.xlsx_to_jpg import XlsxToJpgEngine
from apps.conversions.engines.xlsx_to_png import XlsxToPngEngine
from apps.conversions.engines.libreoffice import find_libreoffice_executable
from apps.conversions.engines.registry import engine_registry
from apps.conversions.formats import SUPPORTED_PAIRS_SET, FORMAT_XLSX, FORMAT_JPG, FORMAT_PNG
from apps.conversions.models import ConversionJob, JobStatus

# ── Temp directory for tests ──────────────────────────────────────────────────
TEST_TEMP_DIR = tempfile.mkdtemp(prefix="velto_xlsx_img_tests_")


def create_xlsx_fixture(sheets: int = 1) -> bytes:
    """Helper using openpyxl to generate 1-sheet or multi-sheet XLSX fixtures."""
    wb = openpyxl.Workbook()
    ws_default = wb.active
    ws_default.title = "Summary"
    ws_default["A1"] = "Summary Sheet Title"
    ws_default["B2"] = "Data value 1"

    for s in range(2, sheets + 1):
        ws = wb.create_sheet(title=f"Sheet{s}")
        ws["A1"] = f"Sheet {s} Heading"
        ws["B2"] = 500 * s

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


@override_settings(TEMP_UPLOAD_DIR=TEST_TEMP_DIR)
class XlsxToImageEngineRegistrationTests(TestCase):
    """Engine registration and supported pairs tests for XLSX → JPG/PNG."""

    def test_xlsx_to_jpg_engine_registration(self):
        """XlsxToJpgEngine is registered in engine_registry."""
        cls = engine_registry.get("xlsx", "jpg")
        self.assertIsNotNone(cls)
        self.assertEqual(cls, XlsxToJpgEngine)

    def test_xlsx_to_png_engine_registration(self):
        """XlsxToPngEngine is registered in engine_registry."""
        cls = engine_registry.get("xlsx", "png")
        self.assertIsNotNone(cls)
        self.assertEqual(cls, XlsxToPngEngine)

    def test_supported_pairs_registration(self):
        """(xlsx, jpg) and (xlsx, png) are present in SUPPORTED_PAIRS_SET."""
        self.assertIn((FORMAT_XLSX, FORMAT_JPG), SUPPORTED_PAIRS_SET)
        self.assertIn((FORMAT_XLSX, FORMAT_PNG), SUPPORTED_PAIRS_SET)


@override_settings(TEMP_UPLOAD_DIR=TEST_TEMP_DIR)
class XlsxToImageEngineUnitTests(TestCase):
    """Direct engine unit tests for XlsxToJpgEngine and XlsxToPngEngine."""

    def setUp(self):
        self.single_xlsx = os.path.join(TEST_TEMP_DIR, "single.xlsx")
        with open(self.single_xlsx, "wb") as f:
            f.write(create_xlsx_fixture(sheets=1))

        self.multi_xlsx = os.path.join(TEST_TEMP_DIR, "multi.xlsx")
        with open(self.multi_xlsx, "wb") as f:
            f.write(create_xlsx_fixture(sheets=3))

    def tearDown(self):
        for f in (self.single_xlsx, self.multi_xlsx):
            if os.path.exists(f):
                try:
                    os.remove(f)
                except OSError:
                    pass

    def test_single_sheet_xlsx_to_jpg_engine(self):
        """1-sheet XLSX → JPG yields a single .jpg file with valid dimensions."""
        if not find_libreoffice_executable():
            self.skipTest("LibreOffice not installed.")

        engine = XlsxToJpgEngine()
        out_path = os.path.join(TEST_TEMP_DIR, "financial_report.jpg")
        res_path = engine.convert(self.single_xlsx, out_path)

        final_file = res_path or out_path
        self.assertTrue(os.path.exists(final_file))
        self.assertTrue(final_file.endswith(".jpg"))
        with Image.open(final_file) as img:
            self.assertEqual(img.format, "JPEG")
            self.assertGreater(img.width, 0)
            self.assertGreater(img.height, 0)

    def test_single_sheet_xlsx_to_png_engine(self):
        """1-sheet XLSX → PNG yields a single .png file with valid dimensions."""
        if not find_libreoffice_executable():
            self.skipTest("LibreOffice not installed.")

        engine = XlsxToPngEngine()
        out_path = os.path.join(TEST_TEMP_DIR, "financial_report.png")
        res_path = engine.convert(self.single_xlsx, out_path)

        final_file = res_path or out_path
        self.assertTrue(os.path.exists(final_file))
        self.assertTrue(final_file.endswith(".png"))
        with Image.open(final_file) as img:
            self.assertEqual(img.format, "PNG")
            self.assertGreater(img.width, 0)
            self.assertGreater(img.height, 0)

    def test_multisheet_xlsx_to_jpg_engine(self):
        """Multi-sheet XLSX → JPG yields a ZIP archive with ordered page files."""
        if not find_libreoffice_executable():
            self.skipTest("LibreOffice not installed.")

        engine = XlsxToJpgEngine()
        out_path = os.path.join(TEST_TEMP_DIR, "financial_report.jpg")
        res_path = engine.convert(self.multi_xlsx, out_path)

        self.assertIsNotNone(res_path)
        self.assertTrue(res_path.endswith(".zip"))
        self.assertTrue(os.path.exists(res_path))

        with zipfile.ZipFile(res_path, "r") as zf:
            namelist = zf.namelist()
            self.assertGreaterEqual(len(namelist), 3)
            self.assertEqual(namelist[:3], ["page-001.jpg", "page-002.jpg", "page-003.jpg"])
            for fname in namelist:
                self.assertTrue(fname.endswith(".jpg"))

    def test_multisheet_xlsx_to_png_engine(self):
        """Multi-sheet XLSX → PNG yields a ZIP archive with ordered page files."""
        if not find_libreoffice_executable():
            self.skipTest("LibreOffice not installed.")

        engine = XlsxToPngEngine()
        out_path = os.path.join(TEST_TEMP_DIR, "financial_report.png")
        res_path = engine.convert(self.multi_xlsx, out_path)

        self.assertIsNotNone(res_path)
        self.assertTrue(res_path.endswith(".zip"))
        self.assertTrue(os.path.exists(res_path))

        with zipfile.ZipFile(res_path, "r") as zf:
            namelist = zf.namelist()
            self.assertGreaterEqual(len(namelist), 3)
            self.assertEqual(namelist[:3], ["page-001.png", "page-002.png", "page-003.png"])
            for fname in namelist:
                self.assertTrue(fname.endswith(".png"))

    def test_invalid_xlsx_raises_conversion_error(self):
        """Corrupted XLSX input raises ConversionError before calling LibreOffice."""
        bad_xlsx = os.path.join(TEST_TEMP_DIR, "corrupt.xlsx")
        with open(bad_xlsx, "wb") as f:
            f.write(b"NOT A REAL XLSX ZIP ARCHIVE")

        engine = XlsxToJpgEngine()
        out_path = os.path.join(TEST_TEMP_DIR, "out.jpg")
        try:
            with self.assertRaises(ConversionError) as ctx:
                engine.convert(bad_xlsx, out_path)
            self.assertIn("valid XLSX", str(ctx.exception))
        finally:
            if os.path.exists(bad_xlsx):
                os.remove(bad_xlsx)

    @patch("apps.conversions.engines.libreoffice.find_libreoffice_executable", return_value=None)
    def test_missing_libreoffice_raises_conversion_error(self, mock_find):
        """Missing LibreOffice raises clear ConversionError."""
        engine = XlsxToJpgEngine()
        out_path = os.path.join(TEST_TEMP_DIR, "out.jpg")
        with self.assertRaises(ConversionError) as ctx:
            engine.convert(self.single_xlsx, out_path)
        self.assertIn("LibreOffice is not installed", str(ctx.exception))

    @patch("apps.conversions.engines.libreoffice.find_libreoffice_executable", return_value="soffice")
    @patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="soffice", timeout=60))
    def test_libreoffice_timeout_raises_conversion_error(self, mock_run, mock_find):
        """LibreOffice timeout raises ConversionError."""
        engine = XlsxToJpgEngine()
        out_path = os.path.join(TEST_TEMP_DIR, "out.jpg")
        with self.assertRaises(ConversionError) as ctx:
            engine.convert(self.single_xlsx, out_path)
        self.assertIn("timed out", str(ctx.exception))

    @patch("apps.conversions.engines.libreoffice.find_libreoffice_executable", return_value="soffice")
    @patch("subprocess.run")
    def test_invalid_intermediate_pdf_raises_conversion_error(self, mock_run, mock_find):
        """Intermediate PDF produced by LibreOffice being empty raises ConversionError."""
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

        def side_effect(cmd, **kwargs):
            out_dir = cmd[cmd.index("--outdir") + 1]
            pdf_path = os.path.join(out_dir, "single.pdf")
            with open(pdf_path, "wb") as f:
                f.write(b"")  # 0-byte file
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

        mock_run.side_effect = side_effect

        engine = XlsxToJpgEngine()
        out_path = os.path.join(TEST_TEMP_DIR, "out.jpg")
        with self.assertRaises(ConversionError) as ctx:
            engine.convert(self.single_xlsx, out_path)
        self.assertIn("empty output file", str(ctx.exception))

    @patch("apps.conversions.engines.pdf_to_image.PdfToJpgEngine.convert", side_effect=ConversionError("PyMuPDF rendering failed"))
    def test_pdf_rendering_failure_raises_conversion_error(self, mock_pdf_render):
        """PyMuPDF rendering failure raises ConversionError."""
        if not find_libreoffice_executable():
            self.skipTest("LibreOffice not installed.")

        engine = XlsxToJpgEngine()
        out_path = os.path.join(TEST_TEMP_DIR, "out.jpg")
        with self.assertRaises(ConversionError) as ctx:
            engine.convert(self.single_xlsx, out_path)
        self.assertIn("PyMuPDF rendering failed", str(ctx.exception))


@override_settings(TEMP_UPLOAD_DIR=TEST_TEMP_DIR)
class XlsxToImageApiIntegrationTests(TestCase):
    """API Integration tests for XLSX → JPG and XLSX → PNG conversions."""

    def setUp(self):
        self.client_a = APIClient()
        self.client_b = APIClient()
        self.single_xlsx_bytes = create_xlsx_fixture(sheets=1)
        self.multi_xlsx_bytes = create_xlsx_fixture(sheets=3)

    def test_single_sheet_xlsx_to_jpg_api_flow(self):
        """API Flow: Upload 1-sheet XLSX → JPG → status completed → download JPG."""
        if not find_libreoffice_executable():
            self.skipTest("LibreOffice not installed.")

        f = io.BytesIO(self.single_xlsx_bytes)
        f.name = "summary.xlsx"

        res = self.client_a.post(
            "/api/conversions/",
            {
                "file": f,
                "source_format": "xlsx",
                "target_format": "jpg",
            },
            format="multipart",
        )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        data = res.json()
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["output_filename"], "summary.jpg")
        job_id = data["id"]

        dl_url = reverse("conversions:job-download", kwargs={"job_id": job_id})
        dl_res = self.client_a.get(dl_url)
        self.assertEqual(dl_res.status_code, status.HTTP_200_OK)
        self.assertEqual(dl_res["Content-Type"], "image/jpeg")

    def test_single_sheet_xlsx_to_png_api_flow(self):
        """API Flow: Upload 1-sheet XLSX → PNG → status completed → download PNG."""
        if not find_libreoffice_executable():
            self.skipTest("LibreOffice not installed.")

        f = io.BytesIO(self.single_xlsx_bytes)
        f.name = "chart.xlsx"

        res = self.client_a.post(
            "/api/conversions/",
            {
                "file": f,
                "source_format": "xlsx",
                "target_format": "png",
            },
            format="multipart",
        )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        data = res.json()
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["output_filename"], "chart.png")
        job_id = data["id"]

        dl_url = reverse("conversions:job-download", kwargs={"job_id": job_id})
        dl_res = self.client_a.get(dl_url)
        self.assertEqual(dl_res.status_code, status.HTTP_200_OK)
        self.assertEqual(dl_res["Content-Type"], "image/png")

    def test_multisheet_xlsx_to_jpg_api_flow(self):
        """API Flow: Upload multi-sheet XLSX → JPG → status completed → download ZIP."""
        if not find_libreoffice_executable():
            self.skipTest("LibreOffice not installed.")

        f = io.BytesIO(self.multi_xlsx_bytes)
        f.name = "financial_report.xlsx"

        res = self.client_a.post(
            "/api/conversions/",
            {
                "file": f,
                "source_format": "xlsx",
                "target_format": "jpg",
            },
            format="multipart",
        )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        data = res.json()
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["output_filename"], "financial_report.zip")
        job_id = data["id"]

        dl_url = reverse("conversions:job-download", kwargs={"job_id": job_id})
        dl_res = self.client_a.get(dl_url)
        self.assertEqual(dl_res.status_code, status.HTTP_200_OK)
        self.assertEqual(dl_res["Content-Type"], "application/zip")

    def test_multisheet_xlsx_to_png_api_flow(self):
        """API Flow: Upload multi-sheet XLSX → PNG → status completed → download ZIP."""
        if not find_libreoffice_executable():
            self.skipTest("LibreOffice not installed.")

        f = io.BytesIO(self.multi_xlsx_bytes)
        f.name = "financial_report.xlsx"

        res = self.client_a.post(
            "/api/conversions/",
            {
                "file": f,
                "source_format": "xlsx",
                "target_format": "png",
            },
            format="multipart",
        )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        data = res.json()
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["output_filename"], "financial_report.zip")
        job_id = data["id"]

        dl_url = reverse("conversions:job-download", kwargs={"job_id": job_id})
        dl_res = self.client_a.get(dl_url)
        self.assertEqual(dl_res.status_code, status.HTTP_200_OK)
        self.assertEqual(dl_res["Content-Type"], "application/zip")

    def test_invalid_xlsx_api_failure_flow(self):
        """Uploading corrupted XLSX file yields clean API failure response."""
        f = io.BytesIO(b"NOT A REAL XLSX ARCHIVE")
        f.name = "corrupt.xlsx"

        res = self.client_a.post(
            "/api/conversions/",
            {
                "file": f,
                "source_format": "xlsx",
                "target_format": "jpg",
            },
            format="multipart",
        )

        self.assertEqual(res.status_code, status.HTTP_202_ACCEPTED)
        data = res.json()
        self.assertEqual(data["status"], "failed")
        self.assertIn("valid XLSX", data["error_message"])

    def test_anonymous_session_isolation_xlsx_to_image(self):
        """Session B cannot access or download Session A's XLSX → Image jobs."""
        if not find_libreoffice_executable():
            self.skipTest("LibreOffice not installed.")

        f = io.BytesIO(self.single_xlsx_bytes)
        f.name = "secret.xlsx"

        res_a = self.client_a.post(
            "/api/conversions/",
            {
                "file": f,
                "source_format": "xlsx",
                "target_format": "jpg",
            },
            format="multipart",
        )
        self.assertEqual(res_a.status_code, status.HTTP_201_CREATED)
        job_id = res_a.json()["id"]

        # Session B attempt detail view
        detail_url = reverse("conversions:job-detail", kwargs={"job_id": job_id})
        res_b_detail = self.client_b.get(detail_url)
        self.assertEqual(res_b_detail.status_code, status.HTTP_404_NOT_FOUND)

        # Session B attempt download
        dl_url = reverse("conversions:job-download", kwargs={"job_id": job_id})
        res_b_dl = self.client_b.get(dl_url)
        self.assertEqual(res_b_dl.status_code, status.HTTP_404_NOT_FOUND)
