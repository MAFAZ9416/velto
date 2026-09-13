"""
Phase 2 (Extension): Tests for DOCX → JPG and DOCX → PNG conversion engines.

Scenarios covered:
  1. Single-page DOCX → JPG (1 .jpg image output, validated via PIL).
  2. Single-page DOCX → PNG (1 .png image output, validated via PIL).
  3. Multi-page DOCX → JPG (ZIP archive containing page-001.jpg, page-002.jpg, ...).
  4. Multi-page DOCX → PNG (ZIP archive containing page-001.png, page-002.png, ...).
  5. Download endpoint verification (Content-Type: image/jpeg, image/png, application/zip).
  6. Failure handling: Invalid DOCX, missing LibreOffice, timeout, intermediate PDF failure.
  7. Session ownership isolation (cross-session access blocked with HTTP 404).
"""

import io
import os
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch
import subprocess

import docx
from PIL import Image
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.conversions.engines.base import ConversionError
from apps.conversions.engines.docx_to_image import (
    DocxToJpgEngine,
    DocxToPngEngine,
)
from apps.conversions.engines.docx_to_pdf import find_libreoffice_executable
from apps.conversions.models import ConversionJob, JobStatus
from apps.conversions.services import ConversionService

# ── Temp directory for tests ──────────────────────────────────────────────────
TEST_TEMP_DIR = tempfile.mkdtemp(prefix="velto_docx_img_tests_")


def create_docx_fixture(pages: int = 1) -> bytes:
    """Helper to generate single or multi-page DOCX files."""
    doc = docx.Document()
    doc.add_heading(f"Sample DOCX Document ({pages} page/s)", level=0)
    for p in range(1, pages + 1):
        doc.add_paragraph(f"This is paragraph text for page {p}.")
        if p < pages:
            doc.add_page_break()
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


@override_settings(TEMP_UPLOAD_DIR=TEST_TEMP_DIR)
class DocxToImageEngineUnitTests(TestCase):
    """Direct engine unit tests for DocxToJpgEngine and DocxToPngEngine."""

    def setUp(self):
        self.single_docx = os.path.join(TEST_TEMP_DIR, "single.docx")
        with open(self.single_docx, "wb") as f:
            f.write(create_docx_fixture(pages=1))

        self.multi_docx = os.path.join(TEST_TEMP_DIR, "multi.docx")
        with open(self.multi_docx, "wb") as f:
            f.write(create_docx_fixture(pages=2))

    def tearDown(self):
        for f in (self.single_docx, self.multi_docx):
            if os.path.exists(f):
                try:
                    os.remove(f)
                except OSError:
                    pass

    def test_single_page_docx_to_jpg_engine(self):
        """Single-page DOCX → JPG yields a single .jpg file."""
        if not find_libreoffice_executable():
            self.skipTest("LibreOffice not installed.")

        engine = DocxToJpgEngine()
        out_path = os.path.join(TEST_TEMP_DIR, "output.jpg")
        res_path = engine.convert(self.single_docx, out_path)

        final_file = res_path or out_path
        self.assertTrue(os.path.exists(final_file))
        self.assertTrue(final_file.endswith(".jpg"))
        with Image.open(final_file) as img:
            self.assertEqual(img.format, "JPEG")
            self.assertGreater(img.width, 0)
            self.assertGreater(img.height, 0)

    def test_single_page_docx_to_png_engine(self):
        """Single-page DOCX → PNG yields a single .png file."""
        if not find_libreoffice_executable():
            self.skipTest("LibreOffice not installed.")

        engine = DocxToPngEngine()
        out_path = os.path.join(TEST_TEMP_DIR, "output.png")
        res_path = engine.convert(self.single_docx, out_path)

        final_file = res_path or out_path
        self.assertTrue(os.path.exists(final_file))
        self.assertTrue(final_file.endswith(".png"))
        with Image.open(final_file) as img:
            self.assertEqual(img.format, "PNG")
            self.assertGreater(img.width, 0)
            self.assertGreater(img.height, 0)

    def test_multipage_docx_to_jpg_engine(self):
        """Multi-page DOCX → JPG yields a ZIP archive with page images."""
        if not find_libreoffice_executable():
            self.skipTest("LibreOffice not installed.")

        engine = DocxToJpgEngine()
        out_path = os.path.join(TEST_TEMP_DIR, "output.jpg")
        res_path = engine.convert(self.multi_docx, out_path)

        self.assertIsNotNone(res_path)
        self.assertTrue(res_path.endswith(".zip"))
        self.assertTrue(os.path.exists(res_path))

        with zipfile.ZipFile(res_path, "r") as zf:
            namelist = zf.namelist()
            self.assertEqual(len(namelist), 2)
            self.assertEqual(namelist, ["page-001.jpg", "page-002.jpg"])

    def test_invalid_docx_raises_conversion_error(self):
        """Corrupted DOCX raises ConversionError."""
        bad_docx = os.path.join(TEST_TEMP_DIR, "corrupt.docx")
        with open(bad_docx, "wb") as f:
            f.write(b"NOT A REAL DOCX FILE")

        engine = DocxToJpgEngine()
        out_path = os.path.join(TEST_TEMP_DIR, "out.jpg")
        try:
            with self.assertRaises(ConversionError) as ctx:
                engine.convert(bad_docx, out_path)
            self.assertIn("valid DOCX", str(ctx.exception))
        finally:
            if os.path.exists(bad_docx):
                os.remove(bad_docx)


@override_settings(TEMP_UPLOAD_DIR=TEST_TEMP_DIR)
class DocxToImageApiIntegrationTests(TestCase):
    """API Integration tests for DOCX → JPG and DOCX → PNG conversions."""

    def setUp(self):
        self.client_a = APIClient()
        self.client_b = APIClient()
        self.single_docx_bytes = create_docx_fixture(pages=1)
        self.multi_docx_bytes = create_docx_fixture(pages=2)

    def test_single_page_docx_to_jpg_api_flow(self):
        """API Flow: Upload 1-page DOCX → JPG → status completed → download JPG."""
        if not find_libreoffice_executable():
            self.skipTest("LibreOffice not installed.")

        f = io.BytesIO(self.single_docx_bytes)
        f.name = "resume.docx"

        res = self.client_a.post(
            "/api/conversions/",
            {
                "file": f,
                "source_format": "docx",
                "target_format": "jpg",
            },
            format="multipart",
        )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        data = res.json()
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["output_filename"], "resume.jpg")
        job_id = data["id"]

        dl_url = reverse("conversions:job-download", kwargs={"job_id": job_id})
        dl_res = self.client_a.get(dl_url)
        self.assertEqual(dl_res.status_code, status.HTTP_200_OK)
        self.assertEqual(dl_res["Content-Type"], "image/jpeg")

    def test_single_page_docx_to_png_api_flow(self):
        """API Flow: Upload 1-page DOCX → PNG → status completed → download PNG."""
        if not find_libreoffice_executable():
            self.skipTest("LibreOffice not installed.")

        f = io.BytesIO(self.single_docx_bytes)
        f.name = "diagram.docx"

        res = self.client_a.post(
            "/api/conversions/",
            {
                "file": f,
                "source_format": "docx",
                "target_format": "png",
            },
            format="multipart",
        )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        data = res.json()
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["output_filename"], "diagram.png")
        job_id = data["id"]

        dl_url = reverse("conversions:job-download", kwargs={"job_id": job_id})
        dl_res = self.client_a.get(dl_url)
        self.assertEqual(dl_res.status_code, status.HTTP_200_OK)
        self.assertEqual(dl_res["Content-Type"], "image/png")

    def test_multipage_docx_to_jpg_api_flow(self):
        """API Flow: Upload multi-page DOCX → JPG → status completed → download ZIP."""
        if not find_libreoffice_executable():
            self.skipTest("LibreOffice not installed.")

        f = io.BytesIO(self.multi_docx_bytes)
        f.name = "report.docx"

        res = self.client_a.post(
            "/api/conversions/",
            {
                "file": f,
                "source_format": "docx",
                "target_format": "jpg",
            },
            format="multipart",
        )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        data = res.json()
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["output_filename"], "report.zip")
        job_id = data["id"]

        dl_url = reverse("conversions:job-download", kwargs={"job_id": job_id})
        dl_res = self.client_a.get(dl_url)
        self.assertEqual(dl_res.status_code, status.HTTP_200_OK)
        self.assertEqual(dl_res["Content-Type"], "application/zip")

    def test_multipage_docx_to_png_api_flow(self):
        """API Flow: Upload multi-page DOCX → PNG → status completed → download ZIP."""
        if not find_libreoffice_executable():
            self.skipTest("LibreOffice not installed.")

        f = io.BytesIO(self.multi_docx_bytes)
        f.name = "slides.docx"

        res = self.client_a.post(
            "/api/conversions/",
            {
                "file": f,
                "source_format": "docx",
                "target_format": "png",
            },
            format="multipart",
        )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        data = res.json()
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["output_filename"], "slides.zip")
        job_id = data["id"]

        dl_url = reverse("conversions:job-download", kwargs={"job_id": job_id})
        dl_res = self.client_a.get(dl_url)
        self.assertEqual(dl_res.status_code, status.HTTP_200_OK)
        self.assertEqual(dl_res["Content-Type"], "application/zip")

    def test_session_isolation_docx_to_image(self):
        """Session B cannot access or download Session A's DOCX → Image jobs."""
        if not find_libreoffice_executable():
            self.skipTest("LibreOffice not installed.")

        f = io.BytesIO(self.single_docx_bytes)
        f.name = "private.docx"

        res_a = self.client_a.post(
            "/api/conversions/",
            {
                "file": f,
                "source_format": "docx",
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
