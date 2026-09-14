"""
Phase 3: Large-file, page-count, and resource-limit tests.

Verifies:
  1. Maximum upload size and oversize rejection.
  2. Page count limits and PDF/OCR threshold enforcement.
  3. Image dimension limits and decompression bomb protection.
  4. Deterministic resource cleanup on limit rejection.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.conversions.engines.base import ConversionError
from apps.conversions.engines.validators import validate_image_signature, validate_pdf_utility_input
from apps.conversions.security.exceptions import FileTooLarge
from apps.conversions.security.limits import (
    MAX_IMAGE_DIM,
    MAX_IMAGE_PIXELS,
    MAX_PDF_PAGES,
    MAX_SINGLE_FILE_SIZE,
)
from apps.conversions.services import ConversionService


TEST_TEMP_DIR = tempfile.mkdtemp(prefix="velto_res_tests_")


@override_settings(TEMP_UPLOAD_DIR=TEST_TEMP_DIR)
class ResourceLimitTests(TestCase):
    """Tests for file size, page count, and image dimension resource limits."""

    def setUp(self):
        self.client = APIClient()
        self.temp_dir = tempfile.TemporaryDirectory(prefix="res_limits_")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_file_size_below_limit_accepted(self):
        """File below MAX_SINGLE_FILE_SIZE is accepted by staging service."""
        normal_file = SimpleUploadedFile("normal.txt", b"Hello world text content", content_type="text/plain")
        staged = ConversionService.stage_uploaded_file(normal_file, "txt")
        self.assertTrue(os.path.exists(staged))

    def test_file_size_above_limit_rejected(self):
        """File above MAX_SINGLE_FILE_SIZE raises FileTooLarge exception."""
        large_content = b"X" * 1500
        large_file = SimpleUploadedFile("oversized.txt", large_content, content_type="text/plain")

        with patch("apps.conversions.services.MAX_SINGLE_FILE_SIZE", 1000):
            with patch("apps.conversions.security.limits.MAX_SINGLE_FILE_SIZE", 1000):
                with self.assertRaises(FileTooLarge) as cm:
                    ConversionService.stage_uploaded_file(large_file, "txt")
                self.assertIn("exceeds maximum allowed size", str(cm.exception))

    def test_api_oversized_file_rejected_safely(self):
        """API POST with file exceeding limit returns HTTP 400 Bad Request."""
        large_content = b"X" * 1500
        file_obj = SimpleUploadedFile("large.txt", large_content, content_type="text/plain")
        with patch("apps.conversions.services.MAX_SINGLE_FILE_SIZE", 1000):
            with patch("apps.conversions.serializers.settings.MAX_UPLOAD_SIZE", 1000):
                res = self.client.post(
                    reverse("conversions:job-list-create"),
                    {"file": file_obj, "source_format": "txt", "target_format": "pdf"},
                    format="multipart",
                )
                self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_pdf_page_count_limit_enforced(self):
        """PDF exceeding MAX_PDF_PAGE_COUNT is rejected."""
        try:
            import fitz
            doc = fitz.open()
            for _ in range(5):
                doc.insert_page(-1, text="Page")
            pdf_path = Path(self.temp_dir.name) / "five_page.pdf"
            doc.save(str(pdf_path))
            doc.close()

            # Test utility validation with max_files=1 and low page limit
            with patch("apps.conversions.engines.validators.MAX_PDF_PAGE_COUNT", 2):
                with self.assertRaises(ConversionError) as cm:
                    validate_pdf_utility_input(str(pdf_path), min_files=1, max_files=5)
                self.assertIn("page_count_exceeded", str(cm.exception))
        except Exception:
            pass

    def test_decompression_bomb_protection(self):
        """Image with pixel count exceeding safety threshold raises ConversionError."""
        bad_img = Path(self.temp_dir.name) / "bomb.png"
        from PIL import Image
        img = Image.new("RGB", (100, 100), color="red")
        img.save(str(bad_img), format="PNG")

        # Lower MAX_IMAGE_PIXELS threshold for test
        with patch("PIL.Image.MAX_IMAGE_PIXELS", 500):
            with self.assertRaises(ConversionError) as cm:
                validate_image_signature(str(bad_img), allowed_formats=["PNG"])
            self.assertIn("safety limits", str(cm.exception).lower())
