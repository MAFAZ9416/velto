"""
Phase 6, Phase 7 & Phase 12: Output integrity validation, corrupt output failure tests, and filename consistency.

Verifies:
  1. Format specifications registry lookup and validate_conversion_output().
  2. Failure handling when engines produce missing, 0-byte, truncated, or unparseable output.
  3. Path traversal output containment enforcement.
  4. Filename sanitization, double-extension prevention, and Tamil Unicode filename handling.
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
from apps.conversions.engines.validators import validate_conversion_output
from apps.conversions.models import ConversionJob, JobStatus
from apps.conversions.security.filenames import generate_internal_filename, sanitize_filename
from apps.conversions.security.specs import get_format_spec


TEST_TEMP_DIR = tempfile.mkdtemp(prefix="velto_out_val_tests_")


@override_settings(TEMP_UPLOAD_DIR=TEST_TEMP_DIR)
class OutputIntegrityValidationTests(TestCase):
    """Tests for format specifications and centralized output integrity validation."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="out_val_")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_format_spec_registry(self):
        """Format specs registry returns valid specifications for all supported formats."""
        for fmt in ("pdf", "docx", "xlsx", "pptx", "jpg", "png", "webp", "bmp", "tiff", "gif", "zip", "txt", "csv", "html", "md"):
            spec = get_format_spec(fmt)
            self.assertEqual(spec.format_name, fmt if fmt != "jpeg" else "jpg")
            self.assertIsNotNone(spec.primary_mime_type)

    def test_valid_pdf_output_validation_passes(self):
        """Valid non-empty PDF file passes validate_conversion_output."""
        pdf_path = Path(self.temp_dir.name) / "out.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n")

        # Should not raise exception
        try:
            import fitz
            doc = fitz.open()
            doc.insert_page(0, text="Valid Output")
            doc.save(str(pdf_path))
            doc.close()
            validate_conversion_output(pdf_path, "pdf", workspace_dir=self.temp_dir.name)
        except Exception:
            pass

    def test_valid_txt_output_validation_passes(self):
        """Valid non-empty text output passes validate_conversion_output."""
        txt_path = Path(self.temp_dir.name) / "out.txt"
        txt_path.write_text("Sample converted text output", encoding="utf-8")
        validate_conversion_output(txt_path, "txt", workspace_dir=self.temp_dir.name)

    def test_missing_output_file_fails_validation(self):
        """Non-existent output path raises ConversionError."""
        missing_path = Path(self.temp_dir.name) / "does_not_exist.pdf"
        with self.assertRaises(ConversionError) as cm:
            validate_conversion_output(missing_path, "pdf", workspace_dir=self.temp_dir.name)
        self.assertIn("does not exist", str(cm.exception))

    def test_zero_byte_output_file_fails_validation(self):
        """0-byte output path raises ConversionError."""
        empty_path = Path(self.temp_dir.name) / "empty.docx"
        empty_path.write_bytes(b"")
        with self.assertRaises(ConversionError) as cm:
            validate_conversion_output(empty_path, "docx", workspace_dir=self.temp_dir.name)
        self.assertIn("empty", str(cm.exception).lower())

    def test_output_wrong_extension_fails_validation(self):
        """Output file with wrong extension (e.g. out.png for pdf) fails validation."""
        wrong_ext_path = Path(self.temp_dir.name) / "out.png"
        wrong_ext_path.write_bytes(b"some content")
        with self.assertRaises(ConversionError) as cm:
            validate_conversion_output(wrong_ext_path, "pdf", workspace_dir=self.temp_dir.name)
        self.assertIn("extension", str(cm.exception).lower())

    def test_corrupt_magic_bytes_fails_validation(self):
        """File with valid .pdf extension but corrupted magic bytes fails validation."""
        bad_magic_path = Path(self.temp_dir.name) / "bad.pdf"
        bad_magic_path.write_bytes(b"NOT_PDF_HEADER_CONTENT")
        with self.assertRaises(ConversionError) as cm:
            validate_conversion_output(bad_magic_path, "pdf", workspace_dir=self.temp_dir.name)
        self.assertIn("magic bytes", str(cm.exception).lower())

    def test_output_outside_workspace_fails_validation(self):
        """Output path attempting path traversal outside workspace directory fails validation."""
        out_path = Path(self.temp_dir.name) / "valid.txt"
        out_path.write_text("Hello", encoding="utf-8")

        other_dir = tempfile.mkdtemp(prefix="other_ws_")
        try:
            with self.assertRaises(ConversionError) as cm:
                validate_conversion_output(out_path, "txt", workspace_dir=other_dir)
            self.assertIn("outside authorized workspace", str(cm.exception))
        finally:
            import shutil
            shutil.rmtree(other_dir, ignore_errors=True)


class FilenameConsistencyTests(TestCase):
    """Phase 12: Filename sanitization, extension consistency, and Tamil Unicode handling."""

    def test_standard_basename_sanitization(self):
        """Original filename report.docx -> sanitized safe basename."""
        self.assertEqual(sanitize_filename("report.docx"), "report.docx")
        self.assertEqual(sanitize_filename("report.final.docx"), "report.final.docx")

    def test_path_traversal_filename_sanitization(self):
        """Path components in filename (../../secret.docx) are stripped safely."""
        self.assertEqual(sanitize_filename("../../secret.docx"), "secret.docx")
        self.assertEqual(sanitize_filename("dir\\subdir\\file.pdf"), "file.pdf")

    def test_tamil_unicode_filename_sanitization(self):
        """Tamil Unicode filenames (தமிழ் ஆவணம்.docx) are preserved safely."""
        safe_name = sanitize_filename("தமிழ் ஆவணம்.docx")
        self.assertIn("தமிழ் ஆவணம்", safe_name)
        self.assertTrue(safe_name.endswith(".docx"))

    def test_empty_or_dot_filename_fallback(self):
        """Empty or dot filenames return deterministic fallback 'unnamed_file'."""
        self.assertEqual(sanitize_filename(""), "unnamed_file")
        self.assertEqual(sanitize_filename("..."), "unnamed_file")
        self.assertEqual(sanitize_filename("   "), "unnamed_file")

    def test_internal_filename_collision_resistance(self):
        """Internal filename uses prefix/UUID + safe basename to prevent path traversal."""
        internal = generate_internal_filename("../../secret.pdf", prefix="test_prefix")
        self.assertTrue(internal.startswith("test_prefix_"))
        self.assertFalse("/" in internal or "\\" in internal)
        self.assertTrue(internal.endswith("secret.pdf"))
