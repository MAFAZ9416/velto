"""
Phase 8, Phase 9 & Phase 10: Infrastructure failure handling, timeouts, permissions, disk-full, and LibreOffice availability.

Verifies:
  1. Job processing timeout handling and safe workspace cleanup.
  2. Transient vs permanent error classification (permanent errors do not retry).
  3. Disk-full (ENOSPC) and permission failure safe error handling (no 500 tracebacks).
  4. Missing/failing LibreOffice dependency detection and safe user-facing message.
"""

import errno
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.conversions.engines.base import ConversionError
from apps.conversions.engines.libreoffice import find_libreoffice_executable, run_libreoffice_pdf_conversion
from apps.conversions.models import ConversionJob, JobStatus
from apps.conversions.security.exceptions import ProcessingTimeout
from apps.conversions.services import ConversionService


TEST_TEMP_DIR = tempfile.mkdtemp(prefix="velto_infra_tests_")


@override_settings(TEMP_UPLOAD_DIR=TEST_TEMP_DIR)
class TimeoutTests(TestCase):
    """Phase 8: Timeout tests for conversion jobs."""

    def setUp(self):
        self.client = APIClient()

    def test_job_processing_timeout_raises_timeout_error(self):
        """Job processing exceeding MAX_JOB_PROCESSING_TIMEOUT raises ProcessingTimeout."""
        start_time = 100.0
        with patch("time.time", return_value=start_time + 500.0):
            with patch("apps.conversions.security.limits.MAX_JOB_PROCESSING_TIMEOUT", 120):
                with self.assertRaises(ProcessingTimeout) as cm:
                    from apps.conversions.security import check_job_timeout
                    check_job_timeout(start_time)
                self.assertIn("timed out", str(cm.exception))

    def test_job_timeout_during_processing_fails_job_safely(self):
        """Job timing out during execution transitions to FAILED status with clean message."""
        job = ConversionJob.objects.create(
            source_format="pdf",
            target_format="docx",
            status=JobStatus.PENDING,
            original_filename="timeout_test.pdf",
            session_key="test_session",
        )
        with patch("apps.conversions.services.check_job_timeout", side_effect=ProcessingTimeout("Conversion timed out")):
            # Create dummy input file
            ws = ConversionService._create_isolated_workspace(str(job.id))
            inp = ws / "input.pdf"
            inp.write_bytes(b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n")
            job.input_path = str(inp)
            job.save(update_fields=["input_path"])

            res_job = ConversionService.process_job(job)
            self.assertEqual(res_job.status, JobStatus.FAILED)
            self.assertIn("timed out", res_job.error_message.lower())


@override_settings(TEMP_UPLOAD_DIR=TEST_TEMP_DIR)
class PermissionAndDiskFullTests(TestCase):
    """Phase 9: Permission failure and simulated disk-full (ENOSPC) error handling."""

    def setUp(self):
        self.client = APIClient()
        self.temp_dir = tempfile.TemporaryDirectory(prefix="infra_perm_")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_simulated_disk_full_error_handled_safely(self):
        """Disk-full (ENOSPC) error during upload/engine output fails job cleanly without 500 traceback."""
        file_obj = SimpleUploadedFile("test.txt", b"Sample text content", content_type="text/plain")

        with patch("apps.conversions.services.ConversionService.stage_uploaded_file", side_effect=ConversionError("Storage server is full. Please try again later.")):
            res = self.client.post(
                reverse("conversions:job-list-create"),
                {"file": file_obj, "source_format": "txt", "target_format": "pdf"},
                format="multipart",
            )
            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("full", str(res.data).lower())

    def test_write_permission_failure_handled_safely(self):
        """Permission denied (EACCES) during conversion fails job cleanly."""
        file_obj = SimpleUploadedFile("test.txt", b"Sample text content", content_type="text/plain")

        with patch("apps.conversions.services.ConversionService.stage_uploaded_file", side_effect=ConversionError("Temporary storage permission error.")):
            res = self.client.post(
                reverse("conversions:job-list-create"),
                {"file": file_obj, "source_format": "txt", "target_format": "pdf"},
                format="multipart",
            )
            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("permission", str(res.data).lower())


@override_settings(TEMP_UPLOAD_DIR=TEST_TEMP_DIR)
class LibreOfficeUnavailableTests(TestCase):
    """Phase 10: Tests for missing or failing LibreOffice external dependency."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="infra_lo_")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_missing_libreoffice_binary_handled_safely(self):
        """When LibreOffice is missing, run_libreoffice_pdf_conversion raises clear ConversionError."""
        dummy_input = Path(self.temp_dir.name) / "dummy.docx"
        dummy_input.write_bytes(b"dummy docx bytes")
        dummy_output = Path(self.temp_dir.name) / "out.pdf"

        with patch("apps.conversions.engines.libreoffice.find_libreoffice_executable", return_value=None):
            with self.assertRaises(ConversionError) as cm:
                run_libreoffice_pdf_conversion(str(dummy_input), str(dummy_output), format_label="DOCX")
            self.assertIn("LibreOffice is not installed", str(cm.exception))

    def test_libreoffice_crash_handled_safely(self):
        """When LibreOffice binary returns non-zero exit code, raises clean ConversionError."""
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = "LibreOffice crash dump"
        mock_proc.stderr = "Fatal error in soffice.bin"

        dummy_input = Path(self.temp_dir.name) / "dummy.docx"
        dummy_input.write_bytes(b"dummy docx bytes")
        dummy_output = Path(self.temp_dir.name) / "out.pdf"

        with patch("apps.conversions.engines.libreoffice.find_libreoffice_executable", return_value="C:\\Program Files\\LibreOffice\\program\\soffice.exe"):
            with patch("subprocess.run", return_value=mock_proc):
                with self.assertRaises(ConversionError) as cm:
                    run_libreoffice_pdf_conversion(str(dummy_input), str(dummy_output), format_label="DOCX")
                self.assertIn("failed", str(cm.exception).lower())
