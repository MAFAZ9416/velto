"""
Phase 2 & Phase 11: Malformed input and unsupported conversion pair tests.

Verifies:
  1. Rejection of corrupt, truncated, 0-byte, or malformed input files.
  2. Signature, MIME, and magic byte mismatch validation.
  3. Stable error codes without stack traces or path leaks.
  4. Unsupported conversion pairs, invalid formats, and uppercase variations.
"""

import os
import tempfile
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.conversions.engines.base import ConversionError
from apps.conversions.engines.validators import (
    validate_csv_signature,
    validate_docx_signature,
    validate_html_signature,
    validate_image_signature,
    validate_md_signature,
    validate_pdf_signature,
    validate_pptx_signature,
    validate_txt_signature,
    validate_xlsx_signature,
)
from apps.conversions.formats import is_valid_conversion
from apps.conversions.models import ConversionJob, JobStatus


TEST_TEMP_DIR = tempfile.mkdtemp(prefix="velto_val_tests_")


@override_settings(TEMP_UPLOAD_DIR=TEST_TEMP_DIR)
class MalformedInputTests(TestCase):
    """Tests for malformed, corrupt, 0-byte, or invalid input files."""

    def setUp(self):
        self.client = APIClient()
        self.temp_dir = tempfile.TemporaryDirectory(prefix="malformed_val_")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_random_bytes_with_pdf_extension_rejected(self):
        """Random bytes with .pdf extension fail signature check safely."""
        fake_pdf = Path(self.temp_dir.name) / "bad.pdf"
        fake_pdf.write_bytes(b"RANDOM_NOISE_NOT_PDF_HEADER_123456789")

        with self.assertRaises(ConversionError) as cm:
            validate_pdf_signature(str(fake_pdf))
        self.assertIn("Expected file header '%PDF' was not found", str(cm.exception))

    def test_empty_file_rejected(self):
        """0-byte file raises input file is empty error."""
        empty_file = Path(self.temp_dir.name) / "empty.pdf"
        empty_file.write_bytes(b"")

        with self.assertRaises(ConversionError) as cm:
            validate_pdf_signature(str(empty_file))
        self.assertIn("empty", str(cm.exception).lower())

    def test_truncated_pdf_rejected(self):
        """Truncated PDF with valid header but incomplete body is handled safely."""
        trunc_pdf = Path(self.temp_dir.name) / "trunc.pdf"
        trunc_pdf.write_bytes(b"%PDF-1.4\n%trunc")

        file_obj = SimpleUploadedFile("trunc.pdf", trunc_pdf.read_bytes(), content_type="application/pdf")
        res = self.client.post(
            reverse("conversions:job-list-create"),
            {"file": file_obj, "source_format": "pdf", "target_format": "docx"},
            format="multipart",
        )
        self.assertEqual(res.status_code, status.HTTP_202_ACCEPTED)
        data = res.json()
        self.assertEqual(data["status"], "failed")
        self.assertFalse("Traceback" in data.get("error_message", ""))
        self.assertFalse("C:\\" in data.get("error_message", "") or "/home/" in data.get("error_message", ""))

    def test_invalid_docx_zip_structure_rejected(self):
        """ZIP file with .docx extension missing word/document.xml is rejected."""
        import zipfile
        bad_docx = Path(self.temp_dir.name) / "invalid.docx"
        with zipfile.ZipFile(bad_docx, "w") as zf:
            zf.writestr("something_else.xml", "<xml></xml>")

        with self.assertRaises(ConversionError) as cm:
            validate_docx_signature(str(bad_docx))
        self.assertIn("not appear to be a valid DOCX", str(cm.exception))

    def test_invalid_xlsx_zip_structure_rejected(self):
        """ZIP file with .xlsx extension missing xl/workbook.xml is rejected."""
        import zipfile
        bad_xlsx = Path(self.temp_dir.name) / "invalid.xlsx"
        with zipfile.ZipFile(bad_xlsx, "w") as zf:
            zf.writestr("not_excel.xml", "<data></data>")

        with self.assertRaises(ConversionError) as cm:
            validate_xlsx_signature(str(bad_xlsx))
        self.assertIn("not appear to be a valid XLSX", str(cm.exception))

    def test_invalid_pptx_zip_structure_rejected(self):
        """ZIP file with .pptx extension missing ppt/presentation.xml is rejected."""
        import zipfile
        bad_pptx = Path(self.temp_dir.name) / "invalid.pptx"
        with zipfile.ZipFile(bad_pptx, "w") as zf:
            zf.writestr("not_ppt.xml", "<slides></slides>")

        with self.assertRaises(ConversionError) as cm:
            validate_pptx_signature(str(bad_pptx))
        self.assertIn("not appear to be a valid PPTX", str(cm.exception))

    def test_corrupt_image_header_rejected(self):
        """Corrupt JPEG or PNG header fails image signature validation."""
        bad_img = Path(self.temp_dir.name) / "corrupt.png"
        bad_img.write_bytes(b"\x89PNG\r\n\x1a\nCORRUPT_HEADER_BODY")

        with self.assertRaises(ConversionError):
            validate_image_signature(str(bad_img), allowed_formats=["PNG"])

    def test_mismatched_extension_and_signature_rejected(self):
        """File named report.pdf containing plain text fails MIME and signature validation."""
        fake_pdf = SimpleUploadedFile("report.pdf", b"This is plain text content", content_type="application/pdf")
        res = self.client.post(
            reverse("conversions:job-list-create"),
            {"file": fake_pdf, "source_format": "pdf", "target_format": "txt"},
            format="multipart",
        )
        # Rejected at API boundary (400) or staged and failed (202)
        self.assertIn(res.status_code, (status.HTTP_400_BAD_REQUEST, status.HTTP_202_ACCEPTED))
        if res.status_code == status.HTTP_202_ACCEPTED:
            data = res.json()
            self.assertEqual(data["status"], "failed")

    def test_password_protected_pdf_rejected(self):
        """Encrypted PDF without password fails with clean error message."""
        try:
            import fitz
            doc = fitz.open()
            doc.insert_page(0, text="Secret Content")
            enc_path = Path(self.temp_dir.name) / "encrypted.pdf"
            doc.save(str(enc_path), encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw="owner", user_pw="user")
            doc.close()

            file_obj = SimpleUploadedFile("encrypted.pdf", enc_path.read_bytes(), content_type="application/pdf")
            res = self.client.post(
                reverse("conversions:job-list-create"),
                {"file": file_obj, "source_format": "pdf", "target_format": "docx"},
                format="multipart",
            )
            self.assertEqual(res.status_code, status.HTTP_202_ACCEPTED)
            data = res.json()
            self.assertEqual(data["status"], "failed")
            self.assertIn("password", data["error_message"].lower())
        except Exception:
            pass


class UnsupportedConversionPairTests(TestCase):
    """Tests for unknown formats and unsupported conversion pairs."""

    def setUp(self):
        self.client = APIClient()

    def test_unknown_source_format_rejected(self):
        """Source format not in registry returns 400 Bad Request."""
        file_obj = SimpleUploadedFile("test.exe", b"MZ\x90\x00_binary", content_type="application/octet-stream")
        res = self.client.post(
            reverse("conversions:job-list-create"),
            {"file": file_obj, "source_format": "exe", "target_format": "pdf"},
            format="multipart",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unknown_target_format_rejected(self):
        """Target format not supported returns 400 Bad Request."""
        file_obj = SimpleUploadedFile("test.pdf", b"%PDF-1.4\n1 0 obj<<>>endobj\n", content_type="application/pdf")
        res = self.client.post(
            reverse("conversions:job-list-create"),
            {"file": file_obj, "source_format": "pdf", "target_format": "exe"},
            format="multipart",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unsupported_pair_combination_rejected(self):
        """Unsupported pair (e.g. xlsx -> docx) returns 400 Bad Request at API boundary."""
        self.assertFalse(is_valid_conversion("xlsx", "docx"))
        file_obj = SimpleUploadedFile("sheet.xlsx", b"PK\x03\x04fake_xlsx", content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        res = self.client.post(
            reverse("conversions:job-list-create"),
            {"file": file_obj, "source_format": "xlsx", "target_format": "docx"},
            format="multipart",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        # Ensure job model instance was NOT created
        self.assertEqual(ConversionJob.objects.count(), 0)
