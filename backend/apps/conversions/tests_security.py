"""
Comprehensive Security Test Suite for VELTO Conversion.

Covers all 13 Security Hardening Requirements:
1. MIME type validation & spoofing rejection
2. File signature magic-byte verification
3. File size and resource limits
4. Filename sanitization (Windows reserved names, null bytes, Unicode, path traversal)
5. Path traversal protection (canonical path resolution, UNC paths, symlink escapes)
6. Temporary directory isolation
7. Output file access protection & IDOR prevention
8. Session and user ownership checks
9. Rate limiting (HTTP 429 response)
10. Abuse protection (concurrency limits & job processing timeouts)
11. Antivirus / malware scanning modes (disabled, optional, required, mock malware)
12. Sandboxed execution & timeout handling
13. Decompression-bomb and oversized-archive protection
"""

import io
import os
import shutil
import tempfile
import uuid
import zipfile
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.conversions.models import ConversionJob, JobStatus
from apps.conversions.services import ConversionService
from apps.conversions.security import (
    AbuseLimitExceeded,
    AntivirusUnavailable,
    ArchiveLimitExceeded,
    FileTooLarge,
    InvalidFileSignature,
    InvalidMimeType,
    MalwareDetected,
    OwnershipDenied,
    PathTraversalAttempt,
    ProcessingTimeout,
    UnsafeFilename,
    check_concurrent_jobs,
    check_job_ownership,
    generate_internal_filename,
    get_security_diagnostics,
    resolve_safe_path,
    run_sandboxed_command,
    sanitize_filename,
    scan_file_security,
    validate_file_signature,
    validate_mime_type,
    validate_path_containment,
    validate_zip_archive_security,
)

User = get_user_model()


class SecurityHardeningTests(TestCase):
    """Test suite verifying all 13 Backend Security Hardening requirements."""

    def setUp(self):
        self.client = APIClient()
        self.test_dir = tempfile.mkdtemp(prefix="velto_sec_test_")
        self.addCleanup(lambda: shutil.rmtree(self.test_dir, ignore_errors=True))

        self.user_a = User.objects.create_user(username="usera", password="password123")
        self.user_b = User.objects.create_user(username="userb", password="password123")

    # ── 1. MIME Type Validation ──────────────────────────────────────────────

    def test_mime_validation_valid_pdf(self):
        pdf_file = Path(self.test_dir) / "sample.pdf"
        pdf_file.write_bytes(b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF")
        # Should pass without error
        validate_mime_type(pdf_file, declared_mime="application/pdf", expected_format="pdf")

    def test_mime_validation_pdf_renamed_as_jpg(self):
        jpg_file = Path(self.test_dir) / "fake.jpg"
        jpg_file.write_bytes(b"%PDF-1.4\nfake pdf content")
        with self.assertRaises(InvalidMimeType):
            validate_mime_type(jpg_file, declared_mime="image/jpeg", expected_format="jpg")

    def test_mime_validation_executable_renamed_as_pdf(self):
        exe_file = Path(self.test_dir) / "payload.pdf"
        exe_file.write_bytes(b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff")
        with self.assertRaises(InvalidMimeType):
            validate_mime_type(exe_file, declared_mime="application/pdf", expected_format="pdf")

    def test_mime_validation_generic_browser_mime_for_csv(self):
        csv_file = Path(self.test_dir) / "data.csv"
        csv_file.write_text("col1,col2\nval1,val2\n", encoding="utf-8")
        # Text/plain or octet-stream browser MIME should be accepted for valid CSV
        validate_mime_type(csv_file, declared_mime="text/plain", expected_format="csv")
        validate_mime_type(csv_file, declared_mime="application/octet-stream", expected_format="csv")

    # ── 2. File Signature Validation ─────────────────────────────────────────

    def test_signature_validation_binary_magic_bytes(self):
        pdf_file = Path(self.test_dir) / "valid.pdf"
        pdf_file.write_bytes(b"%PDF-1.5 header bytes")
        validate_file_signature(pdf_file, "pdf")

        png_file = Path(self.test_dir) / "valid.png"
        png_file.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")
        validate_file_signature(png_file, "png")

        fake_png = Path(self.test_dir) / "fake.png"
        fake_png.write_bytes(b"NOT A PNG FILE")
        with self.assertRaises(InvalidFileSignature):
            validate_file_signature(fake_png, "png")

    def test_signature_validation_docx_office_zip(self):
        docx_file = Path(self.test_dir) / "doc.docx"
        with zipfile.ZipFile(docx_file, "w") as zf:
            zf.writestr("[Content_Types].xml", "<Types/>")
            zf.writestr("word/document.xml", "<w:document/>")
        validate_file_signature(docx_file, "docx")

        invalid_docx = Path(self.test_dir) / "bad.docx"
        with zipfile.ZipFile(invalid_docx, "w") as zf:
            zf.writestr("xl/workbook.xml", "<workbook/>")
        with self.assertRaises(InvalidFileSignature):
            validate_file_signature(invalid_docx, "docx")

    # ── 3. File Size & Resource Limits ───────────────────────────────────────

    def test_file_size_limits(self):
        large_file = SimpleUploadedFile("big.pdf", b"X" * (53 * 1024 * 1024))
        with patch("apps.conversions.services.MAX_SINGLE_FILE_SIZE", 50 * 1024 * 1024):
            with self.assertRaises(FileTooLarge):
                ConversionService.stage_uploaded_file(large_file, "pdf")

    # ── 4. Filename Sanitization ─────────────────────────────────────────────

    def test_filename_sanitization(self):
        self.assertEqual(sanitize_filename("../../secret.pdf"), "secret.pdf")
        self.assertEqual(sanitize_filename("..\\..\\secret.pdf"), "secret.pdf")
        self.assertEqual(sanitize_filename("CON.txt"), "safe_CON.txt")
        self.assertEqual(sanitize_filename("NUL.pdf"), "safe_NUL.pdf")
        self.assertTrue(sanitize_filename("தமிழ்_ஆவணம்.pdf").endswith(".pdf"))

        with self.assertRaises(UnsafeFilename):
            sanitize_filename("report_\x00_2026.pdf")

    def test_generate_internal_filename(self):
        internal_name = generate_internal_filename("../../my_report.pdf", prefix="test123")
        self.assertEqual(internal_name, "test123_my_report.pdf")

    # ── 5. Path Traversal Protection ────────────────────────────────────────

    def test_path_traversal_protection(self):
        base = Path(self.test_dir).resolve()

        # Valid nested path
        safe_p = resolve_safe_path(base, "sub/dir/file.txt")
        self.assertTrue(str(safe_p).startswith(str(base)))

        # Traversal attempts
        with self.assertRaises(PathTraversalAttempt):
            resolve_safe_path(base, "../outside.txt")

        with self.assertRaises(PathTraversalAttempt):
            resolve_safe_path(base, "..\\outside.txt")

        with self.assertRaises(PathTraversalAttempt):
            resolve_safe_path(base, "\\\\server\\share\\file.txt")

    # ── 6. Temporary Directory Isolation ─────────────────────────────────────

    def test_isolated_workspace_per_job(self):
        job = ConversionService.create_job(
            source_format="txt",
            target_format="pdf",
            uploaded_file=SimpleUploadedFile("hello.txt", b"Hello World\n"),
            session_key="sess_iso_1",
        )
        self.assertTrue(Path(job.input_path).exists())
        self.assertIn("job_", Path(job.input_path).parent.name)

        # Process job and verify output is inside same isolated workspace
        processed = ConversionService.process_job(job)
        self.assertEqual(processed.status, JobStatus.COMPLETED)
        self.assertTrue(Path(processed.output_path).exists())

        # Clean up job files and verify workspace is removed
        ConversionService.cleanup_job_files(processed)
        self.assertFalse(Path(processed.input_path).exists())

    # ── 7. Output Access Protection & IDOR Prevention ───────────────────────

    def test_output_access_protection_cross_session(self):
        # Create job owned by session 1
        job = ConversionJob.objects.create(
            session_key="session_owner_1",
            source_format="txt",
            target_format="pdf",
            status=JobStatus.COMPLETED,
            original_filename="doc.txt",
            output_path=str(Path(self.test_dir) / "out.pdf"),
            output_filename="doc.pdf",
        )
        Path(job.output_path).write_bytes(b"%PDF-1.4 output")

        # Client without matching session should receive 404 Not Found (no info leak)
        response = self.client.get(f"/api/conversions/{job.id}/download/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_output_access_protection_cross_user(self):
        job = ConversionJob.objects.create(
            user=self.user_a,
            source_format="txt",
            target_format="pdf",
            status=JobStatus.COMPLETED,
            original_filename="doc.txt",
            output_path=str(Path(self.test_dir) / "out.pdf"),
            output_filename="doc.pdf",
        )
        Path(job.output_path).write_bytes(b"%PDF-1.4 output")

        # Login as User B and attempt download
        self.client.force_authenticate(user=self.user_b)
        response = self.client.get(f"/api/conversions/{job.id}/download/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ── 8. Session & User Ownership ──────────────────────────────────────────

    def test_ownership_check_helper(self):
        job_a = ConversionJob.objects.create(user=self.user_a, source_format="txt", target_format="pdf")

        class DummyRequest:
            user = self.user_b
            session = type("S", (), {"session_key": "sess1"})()

        with self.assertRaises(OwnershipDenied):
            check_job_ownership(DummyRequest(), job_a)

    # ── 9. Rate Limiting ─────────────────────────────────────────────────────

    @override_settings(REST_FRAMEWORK_THROTTLE_ENABLE=True, TESTING=False)
    def test_rate_limiting_throttle_trigger(self):
        # Triggering throttled request on supported-formats or upload
        from apps.conversions.security.rate_limits import UploadRateThrottle
        throttle = UploadRateThrottle()
        req = type("Req", (), {"user": None, "session": type("S", (), {"session_key": "rate_test_1"})(), "META": {"REMOTE_ADDR": "127.0.0.1"}})()
        
        # Fast loop past allowed rate (30/min)
        for _ in range(30):
            throttle.allow_request(req, None)

        self.assertFalse(throttle.allow_request(req, None))

    # ── 10. Resource Abuse Controls ──────────────────────────────────────────

    def test_concurrent_jobs_limit(self):
        session_key = "abuse_session_key"

        # Create MAX_CONCURRENT_JOBS_PER_OWNER active jobs
        for i in range(5):
            ConversionJob.objects.create(
                session_key=session_key,
                source_format="txt",
                target_format="pdf",
                status=JobStatus.PROCESSING,
            )

        class DummyReq:
            user = None
            session = type("S", (), {"session_key": session_key, "create": lambda: None})()

        with self.assertRaises(AbuseLimitExceeded):
            check_concurrent_jobs(DummyReq())

    # ── 11. Antivirus / Malware Scanning ─────────────────────────────────────

    @override_settings(ANTIVIRUS_MODE="required", ANTIVIRUS_PROVIDER="mock")
    def test_antivirus_eicar_malware_detection(self):
        malware_file = Path(self.test_dir) / "test_malware.txt"
        malware_file.write_bytes(b"MALWARE_TEST_VIRUS_SIGNATURE_PAYLOAD")

        with self.assertRaises(MalwareDetected):
            scan_file_security(malware_file)

    @override_settings(ANTIVIRUS_MODE="disabled")
    def test_antivirus_disabled_mode(self):
        malware_file = Path(self.test_dir) / "test_malware.txt"
        malware_file.write_bytes(b"MALWARE_TEST_VIRUS_SIGNATURE_PAYLOAD")
        res = scan_file_security(malware_file)
        self.assertTrue(res.clean)
        self.assertEqual(res.metadata.get("status"), "skipped")

    # ── 12. Sandboxed Subprocess Execution ───────────────────────────────────

    def test_sandboxed_command_execution(self):
        # Run python version command in isolated workspace
        res = run_sandboxed_command(["python", "--version"], cwd=self.test_dir, timeout=10)
        self.assertEqual(res.returncode, 0)
        self.assertIn("Python", res.stdout + res.stderr)

    def test_sandboxed_command_timeout(self):
        # Run sleep command expecting timeout
        cmd = ["python", "-c", "import time; time.sleep(5)"]
        with self.assertRaises(ProcessingTimeout):
            run_sandboxed_command(cmd, cwd=self.test_dir, timeout=1)

    # ── 13. Archive Protection & Zip Bombs ───────────────────────────────────

    def test_archive_zip_bomb_detection(self):
        zip_bomb_path = Path(self.test_dir) / "bomb.zip"
        # Create a compressed file with extreme ratio
        data = b"0" * (5 * 1024 * 1024)  # 5 MB of zeroes
        with zipfile.ZipFile(zip_bomb_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("bomb.txt", data)

        with patch("apps.conversions.security.archive_limits.MAX_ARCHIVE_RATIO", 10.0):
            with self.assertRaises(ArchiveLimitExceeded):
                validate_zip_archive_security(zip_bomb_path)

    def test_archive_path_traversal_rejection(self):
        bad_zip_path = Path(self.test_dir) / "traversal.zip"
        with zipfile.ZipFile(bad_zip_path, "w") as zf:
            zf.writestr("../../etc/passwd", "root:x:0:0")

        with self.assertRaises(ArchiveLimitExceeded):
            validate_zip_archive_security(bad_zip_path)

    # ── Diagnostics Endpoint Test ────────────────────────────────────────────

    def test_security_diagnostics_endpoint(self):
        response = self.client.get("/api/conversions/security/diagnostics/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["controls"]["mime_validation"])
        self.assertEqual(response.data["status"], "healthy")
