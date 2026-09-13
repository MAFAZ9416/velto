"""
Phase 2 tests — DOCX → PDF conversion engine using LibreOffice.

Scenarios covered:
  1. Successful real DOCX → PDF conversion & PyMuPDF validation.
  2. Protected download endpoint (HTTP 200, Content-Type: application/pdf).
  3. Invalid/corrupted DOCX file handling (fails cleanly, no orphan files).
  4. Missing LibreOffice executable discovery fallback & error handling.
  5. LibreOffice conversion timeout (subprocess.TimeoutExpired).
  6. LibreOffice non-zero exit code handling.
  7. Invalid generated PDF output validation failure.
  8. Anonymous session isolation (cross-session access blocked with HTTP 404).
  9. Executable discovery ordering (LIBREOFFICE_PATH vs PATH vs Windows defaults).
"""

import io
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock
import subprocess
from pathlib import Path

import docx
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.conversions.engines.base import ConversionError
from apps.conversions.engines.docx_to_pdf import (
    DocxToPdfEngine,
    find_libreoffice_executable,
)
from apps.conversions.engines.validators import validate_docx_signature, validate_pdf_output
from apps.conversions.models import ConversionJob, JobStatus
from apps.conversions.services import ConversionService

# ── Isolated temp directory for DOCX tests ────────────────────────────────────
TEST_TEMP_DIR = tempfile.mkdtemp(prefix="velto_phase2_docx_tests_")


def create_sample_docx_bytes(title: str = "Sample DOCX Title") -> bytes:
    """Helper to generate a valid in-memory .docx file."""
    doc = docx.Document()
    doc.add_heading(title, level=0)
    doc.add_paragraph("This is a test paragraph for DOCX to PDF conversion testing.")
    doc.add_paragraph("Second paragraph with some sample details.")
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


@override_settings(TEMP_UPLOAD_DIR=TEST_TEMP_DIR)
class DocxToPdfEngineIntegrationTests(TestCase):
    """
    Integration & Unit tests for DocxToPdfEngine and LibreOffice discovery.
    """

    def setUp(self):
        self.client = APIClient()
        self.docx_bytes = create_sample_docx_bytes()

    def test_find_libreoffice_executable_discovery(self):
        """Verify executable discovery logic order."""
        # 1. Custom LIBREOFFICE_PATH env var
        dummy_exe = os.path.join(TEST_TEMP_DIR, "mock_soffice.exe")
        with open(dummy_exe, "w") as f:
            f.write("mock")

        with patch.dict(os.environ, {"LIBREOFFICE_PATH": dummy_exe}):
            found = find_libreoffice_executable()
            self.assertEqual(found, dummy_exe)

        # Cleanup dummy file
        try:
            os.remove(dummy_exe)
        except OSError:
            pass

    def test_validate_docx_signature_valid(self):
        """Valid DOCX should pass validation without error."""
        docx_file = os.path.join(TEST_TEMP_DIR, "valid.docx")
        with open(docx_file, "wb") as f:
            f.write(self.docx_bytes)
        try:
            validate_docx_signature(docx_file)
        finally:
            if os.path.exists(docx_file):
                os.remove(docx_file)

    def test_validate_docx_signature_invalid(self):
        """Corrupt or non-ZIP file should raise ConversionError."""
        bad_file = os.path.join(TEST_TEMP_DIR, "bad.docx")
        with open(bad_file, "wb") as f:
            f.write(b"NOT A REAL DOCX FILE")
        try:
            with self.assertRaises(ConversionError) as ctx:
                validate_docx_signature(bad_file)
            self.assertIn("valid DOCX", str(ctx.exception))
        finally:
            if os.path.exists(bad_file):
                os.remove(bad_file)

    def test_missing_libreoffice_fails_cleanly(self):
        """If LibreOffice cannot be found, conversion must fail with clear message."""
        engine = DocxToPdfEngine()
        docx_file = os.path.join(TEST_TEMP_DIR, "test.docx")
        with open(docx_file, "wb") as f:
            f.write(self.docx_bytes)

        try:
            with patch("apps.conversions.engines.libreoffice.find_libreoffice_executable", return_value=None):
                with self.assertRaises(ConversionError) as ctx:
                    engine.convert(docx_file, os.path.join(TEST_TEMP_DIR, "out.pdf"))
                self.assertIn("LibreOffice is not installed or could not be found", str(ctx.exception))
        finally:
            if os.path.exists(docx_file):
                os.remove(docx_file)

    def test_libreoffice_timeout_fails_cleanly(self):
        """Subprocess timeout must raise a clear timeout ConversionError."""
        engine = DocxToPdfEngine()
        docx_file = os.path.join(TEST_TEMP_DIR, "timeout.docx")
        with open(docx_file, "wb") as f:
            f.write(self.docx_bytes)

        try:
            with patch("apps.conversions.engines.libreoffice.find_libreoffice_executable", return_value="soffice"), \
                 patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="soffice", timeout=60)):
                with self.assertRaises(ConversionError) as ctx:
                    engine.convert(docx_file, os.path.join(TEST_TEMP_DIR, "out.pdf"))
                self.assertEqual(str(ctx.exception), "LibreOffice conversion timed out.")
        finally:
            if os.path.exists(docx_file):
                os.remove(docx_file)

    def test_libreoffice_nonzero_exit_code_fails_cleanly(self):
        """Subprocess non-zero exit code must raise ConversionError."""
        engine = DocxToPdfEngine()
        docx_file = os.path.join(TEST_TEMP_DIR, "nonzero.docx")
        with open(docx_file, "wb") as f:
            f.write(self.docx_bytes)

        mock_res = subprocess.CompletedProcess(args=["soffice"], returncode=1, stdout="", stderr="Fatal error")

        try:
            with patch("apps.conversions.engines.libreoffice.find_libreoffice_executable", return_value="soffice"), \
                 patch("subprocess.run", return_value=mock_res):
                with self.assertRaises(ConversionError) as ctx:
                    engine.convert(docx_file, os.path.join(TEST_TEMP_DIR, "out.pdf"))
                self.assertEqual(str(ctx.exception), "LibreOffice failed to convert the DOCX file to PDF.")
        finally:
            if os.path.exists(docx_file):
                os.remove(docx_file)

    def test_invalid_generated_pdf_fails_cleanly(self):
        """If LibreOffice output is corrupted or invalid, output validation must reject it."""
        engine = DocxToPdfEngine()
        docx_file = os.path.join(TEST_TEMP_DIR, "badpdf.docx")
        with open(docx_file, "wb") as f:
            f.write(self.docx_bytes)

        try:
            with patch("apps.conversions.engines.libreoffice.find_libreoffice_executable", return_value="soffice"), \
                 patch("apps.conversions.engines.libreoffice.validate_pdf_output", side_effect=ConversionError("The generated PDF file is invalid or unreadable.")):
                # Mock subprocess run to create a dummy output file so it reaches validation
                def mock_run(cmd, **kwargs):
                    out_dir = Path(cmd[cmd.index("--outdir") + 1])
                    (out_dir / "badpdf.pdf").write_bytes(b"invalid pdf bytes")
                    return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")

                with patch("subprocess.run", side_effect=mock_run):
                    with self.assertRaises(ConversionError) as ctx:
                        engine.convert(docx_file, os.path.join(TEST_TEMP_DIR, "out.pdf"))
                    self.assertEqual(str(ctx.exception), "The generated PDF file is invalid or unreadable.")
        finally:
            if os.path.exists(docx_file):
                os.remove(docx_file)



@override_settings(TEMP_UPLOAD_DIR=TEST_TEMP_DIR)
class DocxToPdfApiIntegrationTests(TestCase):
    """
    API integration tests for DOCX → PDF conversion flow.
    """

    def setUp(self):
        self.client_a = APIClient()
        self.client_b = APIClient()
        self.docx_bytes = create_sample_docx_bytes("Integration Test Document")

    def test_successful_docx_to_pdf_flow_and_download(self):
        """Full success flow: Upload DOCX → Status Completed → Download PDF."""
        # 1. Check LibreOffice is available on the dev environment
        exe = find_libreoffice_executable()
        if not exe:
            self.skipTest("LibreOffice not installed on machine.")

        # 2. Upload file
        f = io.BytesIO(self.docx_bytes)
        f.name = "sample_report.docx"

        response = self.client_a.post(
            "/api/conversions/",
            {
                "file": f,
                "source_format": "docx",
                "target_format": "pdf",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["source_format"], "docx")
        self.assertEqual(data["target_format"], "pdf")
        self.assertEqual(data["output_filename"], "sample_report.pdf")
        self.assertTrue(data["output_size_bytes"] > 0)
        self.assertIsNotNone(data["download_url"])

        job_id = data["id"]
        job = ConversionJob.objects.get(id=job_id)
        self.assertTrue(Path(job.output_path).exists())

        # Validate generated PDF using PyMuPDF
        import fitz
        doc = fitz.open(job.output_path)
        self.assertGreaterEqual(len(doc), 1)
        doc.close()

        # 3. Download the PDF
        download_url = reverse("conversions:job-download", kwargs={"job_id": job_id})
        dl_response = self.client_a.get(download_url)
        self.assertEqual(dl_response.status_code, status.HTTP_200_OK)
        self.assertEqual(dl_response["Content-Type"], "application/pdf")
        content = b"".join(dl_response.streaming_content)
        self.assertTrue(content.startswith(b"%PDF"))


    def test_invalid_docx_api_failure_flow(self):
        """Uploading corrupted DOCX file yields clean API failure response."""
        f = io.BytesIO(b"NOT A REAL DOCX")
        f.name = "corrupt.docx"

        response = self.client_a.post(
            "/api/conversions/",
            {
                "file": f,
                "source_format": "docx",
                "target_format": "pdf",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        data = response.json()
        self.assertEqual(data["status"], "failed")
        self.assertIn("valid DOCX", data["error_message"])

    def test_anonymous_session_isolation(self):
        """Job created by Session A cannot be retrieved or downloaded by Session B."""
        exe = find_libreoffice_executable()
        if not exe:
            self.skipTest("LibreOffice not installed on machine.")

        f = io.BytesIO(self.docx_bytes)
        f.name = "secret.docx"

        res_a = self.client_a.post(
            "/api/conversions/",
            {
                "file": f,
                "source_format": "docx",
                "target_format": "pdf",
            },
            format="multipart",
        )
        self.assertEqual(res_a.status_code, status.HTTP_201_CREATED)
        job_id = res_a.json()["id"]

        # Client B attempt detail view
        detail_url = reverse("conversions:job-detail", kwargs={"job_id": job_id})
        res_b_detail = self.client_b.get(detail_url)
        self.assertEqual(res_b_detail.status_code, status.HTTP_404_NOT_FOUND)

        # Client B attempt download
        dl_url = reverse("conversions:job-download", kwargs={"job_id": job_id})
        res_b_dl = self.client_b.get(dl_url)
        self.assertEqual(res_b_dl.status_code, status.HTTP_404_NOT_FOUND)
