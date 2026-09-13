"""
Phase 2 (Extension): Tests for real PDF → JPG and PDF → PNG conversion engines.

Tests exercise real PDF fixtures (single-page & multi-page) generated with reportlab,
verifying:
  1. PdfToJpgEngine and PdfToPngEngine functionality.
  2. Single-page image output vs multi-page ZIP output.
  3. Image file integrity and ZIP contents (page-001.jpg, page-002.jpg, ...).
  4. API lifecycle: POST upload → process → GET download.
  5. Content-Type headers (image/jpeg, image/png, application/zip).
  6. File validation, empty PDF handling, corrupt PDF handling.
  7. Session ownership isolation.
  8. PDF → DOCX regression checks.
"""

import io
import os
import tempfile
import zipfile
from pathlib import Path
from PIL import Image

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.conversions.engines.base import ConversionError
from apps.conversions.engines.pdf_to_image import PdfToJpgEngine, PdfToPngEngine
from apps.conversions.engines.registry import engine_registry
from apps.conversions.fixtures.generate_fixtures import generate_all_fixtures
from apps.conversions.models import ConversionJob, JobStatus
from apps.conversions.services import ConversionService


class BaseImageEngineTestCase(TestCase):
    """Base setup for PDF image rendering tests."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.fixtures = generate_all_fixtures()
        cls.simple_pdf = cls.fixtures["simple_text"]
        cls.multipage_pdf = cls.fixtures["multipage"]
        cls.image_pdf = cls.fixtures["with_image"]


class PdfToJpgEngineTests(BaseImageEngineTestCase):
    """Direct engine unit tests for PdfToJpgEngine."""

    def setUp(self):
        self.engine = PdfToJpgEngine()
        self.temp_dir = tempfile.TemporaryDirectory(prefix="test_jpg_engine_")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_single_page_pdf_to_jpg(self):
        """Single-page PDF produces a valid .jpg file."""
        out_path = os.path.join(self.temp_dir.name, "output.jpg")
        res_path = self.engine.convert(str(self.simple_pdf), out_path)

        self.assertTrue(os.path.exists(res_path or out_path))
        target_file = res_path or out_path
        self.assertTrue(target_file.endswith(".jpg"))

        # Verify image validity with Pillow
        with Image.open(target_file) as img:
            self.assertEqual(img.format, "JPEG")
            self.assertGreater(img.width, 0)
            self.assertGreater(img.height, 0)

    def test_multipage_pdf_to_jpg_zip(self):
        """Multi-page PDF produces a valid ZIP archive containing ordered JPGs."""
        out_path = os.path.join(self.temp_dir.name, "output.jpg")
        res_path = self.engine.convert(str(self.multipage_pdf), out_path)

        self.assertIsNotNone(res_path)
        self.assertTrue(res_path.endswith(".zip"))
        self.assertTrue(os.path.exists(res_path))

        with zipfile.ZipFile(res_path, "r") as zf:
            namelist = zf.namelist()
            self.assertEqual(len(namelist), 3)
            self.assertEqual(namelist, ["page-001.jpg", "page-002.jpg", "page-003.jpg"])

            for name in namelist:
                data = zf.read(name)
                with Image.open(io.BytesIO(data)) as img:
                    self.assertEqual(img.format, "JPEG")

    def test_corrupt_pdf_raises_conversion_error(self):
        """Corrupt PDF raises ConversionError."""
        bad_pdf = os.path.join(self.temp_dir.name, "bad.pdf")
        with open(bad_pdf, "wb") as f:
            f.write(b"%PDF-1.4\nNot a real PDF body corrupt data\n")

        out_path = os.path.join(self.temp_dir.name, "out.jpg")
        with self.assertRaises(ConversionError):
            self.engine.convert(bad_pdf, out_path)


class PdfToPngEngineTests(BaseImageEngineTestCase):
    """Direct engine unit tests for PdfToPngEngine."""

    def setUp(self):
        self.engine = PdfToPngEngine()
        self.temp_dir = tempfile.TemporaryDirectory(prefix="test_png_engine_")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_single_page_pdf_to_png(self):
        """Single-page PDF produces a valid .png file."""
        out_path = os.path.join(self.temp_dir.name, "output.png")
        res_path = self.engine.convert(str(self.simple_pdf), out_path)

        target_file = res_path or out_path
        self.assertTrue(os.path.exists(target_file))
        self.assertTrue(target_file.endswith(".png"))

        with Image.open(target_file) as img:
            self.assertEqual(img.format, "PNG")

    def test_multipage_pdf_to_png_zip(self):
        """Multi-page PDF produces a valid ZIP archive containing ordered PNGs."""
        out_path = os.path.join(self.temp_dir.name, "output.png")
        res_path = self.engine.convert(str(self.multipage_pdf), out_path)

        self.assertIsNotNone(res_path)
        self.assertTrue(res_path.endswith(".zip"))
        self.assertTrue(os.path.exists(res_path))

        with zipfile.ZipFile(res_path, "r") as zf:
            namelist = zf.namelist()
            self.assertEqual(len(namelist), 3)
            self.assertEqual(namelist, ["page-001.png", "page-002.png", "page-003.png"])

            for name in namelist:
                data = zf.read(name)
                with Image.open(io.BytesIO(data)) as img:
                    self.assertEqual(img.format, "PNG")


TEST_TEMP_DIR = tempfile.mkdtemp(prefix="velto_phase2_img_tests_")


@override_settings(TEMP_UPLOAD_DIR=TEST_TEMP_DIR)
class ImageConversionApiIntegrationTests(BaseImageEngineTestCase):
    """Full API integration tests for PDF → JPG and PDF → PNG."""

    def setUp(self):
        self.client = APIClient()

    def test_pdf_to_jpg_single_page_api_flow(self):
        """Upload 1-page PDF → JPG: check job status, download URL, content-type."""
        with open(self.simple_pdf, "rb") as f:
            pdf_bytes = f.read()

        file_obj = SimpleUploadedFile("report.pdf", pdf_bytes, content_type="application/pdf")
        response = self.client.post(
            reverse("conversions:job-list-create"),
            {"file": file_obj, "source_format": "pdf", "target_format": "jpg"},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["output_filename"], "report.jpg")
        self.assertIsNotNone(data["download_url"])

        # Test download endpoint
        dl_response = self.client.get(data["download_url"])
        self.assertEqual(dl_response.status_code, status.HTTP_200_OK)
        self.assertEqual(dl_response["Content-Type"], "image/jpeg")
        self.assertIn('filename="report.jpg"', dl_response["Content-Disposition"])

        dl_bytes = b"".join(dl_response.streaming_content)
        # Verify image content
        with Image.open(io.BytesIO(dl_bytes)) as img:
            self.assertEqual(img.format, "JPEG")

    def test_pdf_to_jpg_multipage_api_flow(self):
        """Upload multi-page PDF → JPG: returns ZIP download with Content-Type application/zip."""
        with open(self.multipage_pdf, "rb") as f:
            pdf_bytes = f.read()

        file_obj = SimpleUploadedFile("doc.pdf", pdf_bytes, content_type="application/pdf")
        response = self.client.post(
            reverse("conversions:job-list-create"),
            {"file": file_obj, "source_format": "pdf", "target_format": "jpg"},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["output_filename"], "doc.zip")

        # Test download endpoint
        dl_response = self.client.get(data["download_url"])
        self.assertEqual(dl_response.status_code, status.HTTP_200_OK)
        self.assertEqual(dl_response["Content-Type"], "application/zip")
        self.assertIn('filename="doc.zip"', dl_response["Content-Disposition"])

        dl_bytes = b"".join(dl_response.streaming_content)
        # Verify ZIP body content
        with zipfile.ZipFile(io.BytesIO(dl_bytes), "r") as zf:
            self.assertEqual(len(zf.namelist()), 3)
            self.assertEqual(zf.namelist(), ["page-001.jpg", "page-002.jpg", "page-003.jpg"])

    def test_pdf_to_png_single_page_api_flow(self):
        """Upload 1-page PDF → PNG: check job status, download URL, content-type image/png."""
        with open(self.simple_pdf, "rb") as f:
            pdf_bytes = f.read()

        file_obj = SimpleUploadedFile("diagram.pdf", pdf_bytes, content_type="application/pdf")
        response = self.client.post(
            reverse("conversions:job-list-create"),
            {"file": file_obj, "source_format": "pdf", "target_format": "png"},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["output_filename"], "diagram.png")

        dl_response = self.client.get(data["download_url"])
        self.assertEqual(dl_response.status_code, status.HTTP_200_OK)
        self.assertEqual(dl_response["Content-Type"], "image/png")

        dl_bytes = b"".join(dl_response.streaming_content)
        with Image.open(io.BytesIO(dl_bytes)) as img:
            self.assertEqual(img.format, "PNG")

    def test_pdf_to_png_multipage_api_flow(self):
        """Upload multi-page PDF → PNG: returns ZIP download with Content-Type application/zip."""
        with open(self.multipage_pdf, "rb") as f:
            pdf_bytes = f.read()

        file_obj = SimpleUploadedFile("multi.pdf", pdf_bytes, content_type="application/pdf")
        response = self.client.post(
            reverse("conversions:job-list-create"),
            {"file": file_obj, "source_format": "pdf", "target_format": "png"},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["output_filename"], "multi.zip")

        dl_response = self.client.get(data["download_url"])
        self.assertEqual(dl_response.status_code, status.HTTP_200_OK)
        self.assertEqual(dl_response["Content-Type"], "application/zip")

        dl_bytes = b"".join(dl_response.streaming_content)
        with zipfile.ZipFile(io.BytesIO(dl_bytes), "r") as zf:
            self.assertEqual(len(zf.namelist()), 3)
            self.assertEqual(zf.namelist(), ["page-001.png", "page-002.png", "page-003.png"])


class ValidationAndSecurityTests(BaseImageEngineTestCase):
    """Validation, error handling, and session isolation tests."""

    def setUp(self):
        self.client = APIClient()

    def test_supported_formats_endpoint_includes_image_pairs(self):
        """GET /api/conversions/supported-formats/ includes pdf -> jpg and pdf -> png."""
        response = self.client.get(reverse("conversions:supported-formats"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        formats = response.json()["formats"]

        pairs = [(item["source_format"], item["target_format"]) for item in formats]
        self.assertIn(("pdf", "jpg"), pairs)
        self.assertIn(("pdf", "png"), pairs)

    def test_invalid_fake_pdf_header_rejected(self):
        """File with .pdf extension but missing %PDF magic header fails gracefully."""
        file_obj = SimpleUploadedFile(
            "fake.pdf", b"This is plain text pretending to be PDF", content_type="application/pdf"
        )
        response = self.client.post(
            reverse("conversions:job-list-create"),
            {"file": file_obj, "source_format": "pdf", "target_format": "jpg"},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        data = response.json()
        self.assertEqual(data["status"], "failed")
        self.assertIn("Expected file header '%PDF' was not found", data["error_message"])

    def test_anonymous_session_isolation(self):
        """User A cannot access or download User B's conversion job."""
        client_a = APIClient()
        client_b = APIClient()

        with open(self.simple_pdf, "rb") as f:
            pdf_bytes = f.read()

        file_obj = SimpleUploadedFile("secret.pdf", pdf_bytes, content_type="application/pdf")
        res_a = client_a.post(
            reverse("conversions:job-list-create"),
            {"file": file_obj, "source_format": "pdf", "target_format": "jpg"},
            format="multipart",
        )
        job_id = res_a.json()["id"]

        # Client B attempts GET detail
        detail_b = client_b.get(reverse("conversions:job-detail", kwargs={"job_id": job_id}))
        self.assertEqual(detail_b.status_code, status.HTTP_404_NOT_FOUND)

        # Client B attempts GET download
        dl_b = client_b.get(reverse("conversions:job-download", kwargs={"job_id": job_id}))
        self.assertEqual(dl_b.status_code, status.HTTP_404_NOT_FOUND)


class RegressionPdfToDocxTests(BaseImageEngineTestCase):
    """Ensure PDF → DOCX continues to work without regression."""

    def setUp(self):
        self.client = APIClient()

    def test_pdf_to_docx_regression(self):
        """PDF → DOCX conversion completes successfully."""
        with open(self.simple_pdf, "rb") as f:
            pdf_bytes = f.read()

        file_obj = SimpleUploadedFile("test.pdf", pdf_bytes, content_type="application/pdf")
        response = self.client.post(
            reverse("conversions:job-list-create"),
            {"file": file_obj, "source_format": "pdf", "target_format": "docx"},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["output_filename"], "test.docx")

        dl_res = self.client.get(data["download_url"])
        self.assertEqual(dl_res.status_code, status.HTTP_200_OK)
        self.assertEqual(
            dl_res["Content-Type"],
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
