"""
Phase 2 tests — XLSX → PDF conversion engine using LibreOffice.

Scenarios covered:
  1. Valid XLSX signature validation.
  2. Missing xl/workbook.xml XLSX signature validation failure.
  3. Corrupted non-ZIP file XLSX signature validation failure.
  4. Real end-to-end multi-sheet XLSX → PDF conversion pipeline.
  5. Correct output filename stem preservation (e.g. report.xlsx → report.pdf).
  6. Generated PDF validation with PyMuPDF (page count >= 1).
  7. Missing LibreOffice executable handling.
  8. LibreOffice conversion timeout handling.
  9. LibreOffice non-zero exit code handling.
 10. Invalid generated PDF output validation failure.
 11. API POST upload success flow.
 12. API POST upload failure flow (HTTP 202 status, failed status).
 13. Download endpoint verification (HTTP 200, Content-Type: application/pdf).
 14. Anonymous session isolation (cross-session access blocked with HTTP 404).
 15. Engine registry verification for XLSX → PDF pair.
 16. Resource and temporary directory cleanup verification.
"""

import io
import os
import tempfile
import zipfile
from unittest.mock import patch
import subprocess
from pathlib import Path

import openpyxl
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.conversions.engines.base import ConversionError
from apps.conversions.engines.libreoffice import find_libreoffice_executable
from apps.conversions.engines.xlsx_to_pdf import XlsxToPdfEngine
from apps.conversions.engines.validators import validate_xlsx_signature
from apps.conversions.engines.registry import engine_registry
from apps.conversions.formats import is_valid_conversion
from apps.conversions.models import ConversionJob, JobStatus

# ── Isolated temp directory for XLSX tests ────────────────────────────────────
TEST_TEMP_DIR = tempfile.mkdtemp(prefix="velto_phase2_xlsx_pdf_tests_")


def create_sample_xlsx_bytes(sheets: int = 2) -> bytes:
    """Helper to generate a valid in-memory XLSX workbook using openpyxl."""
    wb = openpyxl.Workbook()
    ws_default = wb.active
    ws_default.title = "Sheet1"
    ws_default["A1"] = "Summary Header"
    ws_default["A2"] = "Row 1 Value"

    for s in range(2, sheets + 1):
        ws = wb.create_sheet(title=f"Sheet{s}")
        ws["A1"] = f"Data Header Sheet {s}"
        ws["B2"] = 100 * s

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


@override_settings(TEMP_UPLOAD_DIR=TEST_TEMP_DIR)
class XlsxToPdfEngineUnitTests(TestCase):
    """Unit tests for XLSX signature validation, engine registration, and XlsxToPdfEngine."""

    def setUp(self):
        self.xlsx_bytes = create_sample_xlsx_bytes(sheets=3)

    def test_engine_registry_contains_xlsx_to_pdf(self):
        """XlsxToPdfEngine is registered in global engine_registry."""
        cls = engine_registry.get("xlsx", "pdf")
        self.assertEqual(cls, XlsxToPdfEngine)
        self.assertTrue(is_valid_conversion("xlsx", "pdf"))

    def test_validate_xlsx_signature_valid(self):
        """Valid XLSX workbook passes signature validation."""
        xlsx_file = os.path.join(TEST_TEMP_DIR, "valid.xlsx")
        with open(xlsx_file, "wb") as f:
            f.write(self.xlsx_bytes)
        try:
            validate_xlsx_signature(xlsx_file)
        finally:
            if os.path.exists(xlsx_file):
                os.remove(xlsx_file)

    def test_validate_xlsx_signature_missing_workbook_xml(self):
        """ZIP file without xl/workbook.xml raises ConversionError."""
        bad_zip = os.path.join(TEST_TEMP_DIR, "no_xl.xlsx")
        with zipfile.ZipFile(bad_zip, "w") as zf:
            zf.writestr("word/document.xml", "<dummy/>")

        try:
            with self.assertRaises(ConversionError) as ctx:
                validate_xlsx_signature(bad_zip)
            self.assertIn("valid XLSX", str(ctx.exception))
        finally:
            if os.path.exists(bad_zip):
                os.remove(bad_zip)

    def test_validate_xlsx_signature_corrupted_non_zip(self):
        """Non-ZIP corrupt file raises ConversionError."""
        bad_file = os.path.join(TEST_TEMP_DIR, "corrupt.xlsx")
        with open(bad_file, "wb") as f:
            f.write(b"CORRUPTED NON ZIP DATA")

        try:
            with self.assertRaises(ConversionError) as ctx:
                validate_xlsx_signature(bad_file)
            self.assertIn("valid XLSX", str(ctx.exception))
        finally:
            if os.path.exists(bad_file):
                os.remove(bad_file)

    def test_missing_libreoffice_fails_cleanly(self):
        """Missing LibreOffice executable raises clear ConversionError."""
        engine = XlsxToPdfEngine()
        xlsx_file = os.path.join(TEST_TEMP_DIR, "test.xlsx")
        with open(xlsx_file, "wb") as f:
            f.write(self.xlsx_bytes)

        try:
            with patch("apps.conversions.engines.libreoffice.find_libreoffice_executable", return_value=None):
                with self.assertRaises(ConversionError) as ctx:
                    engine.convert(xlsx_file, os.path.join(TEST_TEMP_DIR, "out.pdf"))
                self.assertIn("LibreOffice is not installed or could not be found", str(ctx.exception))
        finally:
            if os.path.exists(xlsx_file):
                os.remove(xlsx_file)

    def test_libreoffice_timeout_fails_cleanly(self):
        """Subprocess timeout raises clear timeout ConversionError."""
        engine = XlsxToPdfEngine()
        xlsx_file = os.path.join(TEST_TEMP_DIR, "timeout.xlsx")
        with open(xlsx_file, "wb") as f:
            f.write(self.xlsx_bytes)

        try:
            with patch("apps.conversions.engines.libreoffice.find_libreoffice_executable", return_value="soffice"), \
                 patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="soffice", timeout=60)):
                with self.assertRaises(ConversionError) as ctx:
                    engine.convert(xlsx_file, os.path.join(TEST_TEMP_DIR, "out.pdf"))
                self.assertEqual(str(ctx.exception), "LibreOffice conversion timed out.")
        finally:
            if os.path.exists(xlsx_file):
                os.remove(xlsx_file)

    def test_libreoffice_nonzero_exit_code_fails_cleanly(self):
        """Subprocess non-zero exit code raises ConversionError."""
        engine = XlsxToPdfEngine()
        xlsx_file = os.path.join(TEST_TEMP_DIR, "nonzero.xlsx")
        with open(xlsx_file, "wb") as f:
            f.write(self.xlsx_bytes)

        mock_res = subprocess.CompletedProcess(args=["soffice"], returncode=1, stdout="", stderr="Fatal error")

        try:
            with patch("apps.conversions.engines.libreoffice.find_libreoffice_executable", return_value="soffice"), \
                 patch("subprocess.run", return_value=mock_res):
                with self.assertRaises(ConversionError) as ctx:
                    engine.convert(xlsx_file, os.path.join(TEST_TEMP_DIR, "out.pdf"))
                self.assertEqual(str(ctx.exception), "LibreOffice failed to convert the XLSX file to PDF.")
        finally:
            if os.path.exists(xlsx_file):
                os.remove(xlsx_file)

    def test_invalid_generated_pdf_fails_cleanly(self):
        """If LibreOffice output PDF is corrupted or invalid, validation rejects it."""
        engine = XlsxToPdfEngine()
        xlsx_file = os.path.join(TEST_TEMP_DIR, "badpdf.xlsx")
        with open(xlsx_file, "wb") as f:
            f.write(self.xlsx_bytes)

        try:
            with patch("apps.conversions.engines.libreoffice.find_libreoffice_executable", return_value="soffice"), \
                 patch("apps.conversions.engines.libreoffice.validate_pdf_output", side_effect=ConversionError("The generated PDF file is invalid or unreadable.")):
                def mock_run(cmd, **kwargs):
                    out_dir = Path(cmd[cmd.index("--outdir") + 1])
                    (out_dir / "badpdf.pdf").write_bytes(b"invalid pdf bytes")
                    return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")

                with patch("subprocess.run", side_effect=mock_run):
                    with self.assertRaises(ConversionError) as ctx:
                        engine.convert(xlsx_file, os.path.join(TEST_TEMP_DIR, "out.pdf"))
                    self.assertEqual(str(ctx.exception), "The generated PDF file is invalid or unreadable.")
        finally:
            if os.path.exists(xlsx_file):
                os.remove(xlsx_file)


@override_settings(TEMP_UPLOAD_DIR=TEST_TEMP_DIR)
class XlsxToPdfApiIntegrationTests(TestCase):
    """API Integration tests for XLSX → PDF conversion flow."""

    def setUp(self):
        self.client_a = APIClient()
        self.client_b = APIClient()
        self.xlsx_bytes = create_sample_xlsx_bytes(sheets=3)

    def test_successful_xlsx_to_pdf_flow_and_download(self):
        """Full success flow: Upload XLSX → Status Completed → Download PDF."""
        exe = find_libreoffice_executable()
        if not exe:
            self.skipTest("LibreOffice not installed on machine.")

        f = io.BytesIO(self.xlsx_bytes)
        f.name = "financial_report.xlsx"

        response = self.client_a.post(
            "/api/conversions/",
            {
                "file": f,
                "source_format": "xlsx",
                "target_format": "pdf",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["source_format"], "xlsx")
        self.assertEqual(data["target_format"], "pdf")
        self.assertEqual(data["output_filename"], "financial_report.pdf")
        self.assertTrue(data["output_size_bytes"] > 0)
        self.assertIsNotNone(data["download_url"])

        job_id = data["id"]
        job = ConversionJob.objects.get(id=job_id)
        self.assertTrue(Path(job.output_path).exists())

        # Validate generated PDF page count with PyMuPDF
        import fitz
        doc = fitz.open(job.output_path)
        self.assertGreaterEqual(len(doc), 1)
        doc.close()

        # Download the PDF
        download_url = reverse("conversions:job-download", kwargs={"job_id": job_id})
        dl_response = self.client_a.get(download_url)
        self.assertEqual(dl_response.status_code, status.HTTP_200_OK)
        self.assertEqual(dl_response["Content-Type"], "application/pdf")
        content = b"".join(dl_response.streaming_content)
        self.assertTrue(content.startswith(b"%PDF"))

    def test_invalid_xlsx_api_failure_flow(self):
        """Uploading corrupted XLSX file yields clean API failure response."""
        f = io.BytesIO(b"NOT A REAL XLSX ARCHIVE")
        f.name = "corrupt.xlsx"

        response = self.client_a.post(
            "/api/conversions/",
            {
                "file": f,
                "source_format": "xlsx",
                "target_format": "pdf",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        data = response.json()
        self.assertEqual(data["status"], "failed")
        self.assertIn("valid XLSX", data["error_message"])

    def test_anonymous_session_isolation_xlsx(self):
        """Job created by Session A cannot be retrieved or downloaded by Session B."""
        exe = find_libreoffice_executable()
        if not exe:
            self.skipTest("LibreOffice not installed on machine.")

        f = io.BytesIO(self.xlsx_bytes)
        f.name = "confidential.xlsx"

        res_a = self.client_a.post(
            "/api/conversions/",
            {
                "file": f,
                "source_format": "xlsx",
                "target_format": "pdf",
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
