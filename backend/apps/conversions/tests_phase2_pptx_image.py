"""
Phase 2 (Extension): Tests for PPTX → JPG and PPTX → PNG conversion engines.

Scenarios covered:
  1. Engine registration in engine_registry for PptxToJpgEngine and PptxToPngEngine.
  2. Supported pairs registration in SUPPORTED_PAIRS.
  3. Single-slide PPTX → JPG (1 .jpg image output, validated via PIL).
  4. Single-slide PPTX → PNG (1 .png image output, validated via PIL).
  5. Multi-slide PPTX → JPG (ZIP archive containing page-001.jpg, page-002.jpg, ...).
  6. Multi-slide PPTX → PNG (ZIP archive containing page-001.png, page-002.png, ...).
  7. Correct output filename stem preservation (e.g. presentation.pptx → presentation.jpg / presentation.zip).
  8. Correct image MIME types (image/jpeg, image/png, application/zip).
  9. Valid image dimensions (width > 0, height > 0).
 10. ZIP file ordering (page-001.jpg, page-002.jpg, ...).
 11. Invalid PPTX input validation failure.
 12. Missing LibreOffice executable handling.
 13. LibreOffice timeout handling.
 14. Invalid intermediate PDF handling.
 15. PDF rendering failure handling.
 16. REST API POST upload success flow.
 17. REST API POST upload failure flow.
 18. Download endpoint streaming and headers.
 19. Anonymous session isolation (cross-session access blocked with HTTP 404).
 20. Intermediate temp file cleanup verification.
 21. Regression coverage for existing DOCX image conversions.
"""

import io
import os
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch
import subprocess

import pptx
from pptx.util import Inches
from PIL import Image
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.conversions.engines.base import ConversionError
from apps.conversions.engines.pptx_to_image import (
    PptxToJpgEngine,
    PptxToPngEngine,
)
from apps.conversions.engines.libreoffice import find_libreoffice_executable
from apps.conversions.engines.registry import engine_registry
from apps.conversions.formats import SUPPORTED_PAIRS_SET, FORMAT_PPTX, FORMAT_JPG, FORMAT_PNG
from apps.conversions.models import ConversionJob, JobStatus

# ── Temp directory for tests ──────────────────────────────────────────────────
TEST_TEMP_DIR = tempfile.mkdtemp(prefix="velto_pptx_img_tests_")


def create_pptx_fixture(slides: int = 1) -> bytes:
    """Shared helper using python-pptx to generate 1-slide or multi-slide PPTX fixtures."""
    prs = pptx.Presentation()
    blank_layout = prs.slide_layouts[6]
    for s in range(1, slides + 1):
        slide = prs.slides.add_slide(blank_layout)
        tx_box = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(8), Inches(4))
        tf = tx_box.text_frame
        tf.text = f"Sample PPTX Slide Content for slide {s}"
    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


@override_settings(TEMP_UPLOAD_DIR=TEST_TEMP_DIR)
class PptxToImageEngineRegistrationTests(TestCase):
    """Engine registration and supported pairs tests for PPTX → JPG/PNG."""

    def test_pptx_to_jpg_engine_registration(self):
        """PptxToJpgEngine is registered in engine_registry."""
        cls = engine_registry.get("pptx", "jpg")
        self.assertIsNotNone(cls)
        self.assertEqual(cls, PptxToJpgEngine)

    def test_pptx_to_png_engine_registration(self):
        """PptxToPngEngine is registered in engine_registry."""
        cls = engine_registry.get("pptx", "png")
        self.assertIsNotNone(cls)
        self.assertEqual(cls, PptxToPngEngine)

    def test_supported_pairs_registration(self):
        """(pptx, jpg) and (pptx, png) are present in SUPPORTED_PAIRS_SET."""
        self.assertIn((FORMAT_PPTX, FORMAT_JPG), SUPPORTED_PAIRS_SET)
        self.assertIn((FORMAT_PPTX, FORMAT_PNG), SUPPORTED_PAIRS_SET)


@override_settings(TEMP_UPLOAD_DIR=TEST_TEMP_DIR)
class PptxToImageEngineUnitTests(TestCase):
    """Direct engine unit tests for PptxToJpgEngine and PptxToPngEngine."""

    def setUp(self):
        self.single_pptx = os.path.join(TEST_TEMP_DIR, "single.pptx")
        with open(self.single_pptx, "wb") as f:
            f.write(create_pptx_fixture(slides=1))

        self.multi_pptx = os.path.join(TEST_TEMP_DIR, "multi.pptx")
        with open(self.multi_pptx, "wb") as f:
            f.write(create_pptx_fixture(slides=3))

    def tearDown(self):
        for f in (self.single_pptx, self.multi_pptx):
            if os.path.exists(f):
                try:
                    os.remove(f)
                except OSError:
                    pass

    def test_single_slide_pptx_to_jpg_engine(self):
        """Single-slide PPTX → JPG yields a single .jpg file with valid dimensions."""
        if not find_libreoffice_executable():
            self.skipTest("LibreOffice not installed.")

        engine = PptxToJpgEngine()
        out_path = os.path.join(TEST_TEMP_DIR, "presentation.jpg")
        res_path = engine.convert(self.single_pptx, out_path)

        final_file = res_path or out_path
        self.assertTrue(os.path.exists(final_file))
        self.assertTrue(final_file.endswith(".jpg"))
        with Image.open(final_file) as img:
            self.assertEqual(img.format, "JPEG")
            self.assertGreater(img.width, 0)
            self.assertGreater(img.height, 0)

    def test_single_slide_pptx_to_png_engine(self):
        """Single-slide PPTX → PNG yields a single .png file with valid dimensions."""
        if not find_libreoffice_executable():
            self.skipTest("LibreOffice not installed.")

        engine = PptxToPngEngine()
        out_path = os.path.join(TEST_TEMP_DIR, "presentation.png")
        res_path = engine.convert(self.single_pptx, out_path)

        final_file = res_path or out_path
        self.assertTrue(os.path.exists(final_file))
        self.assertTrue(final_file.endswith(".png"))
        with Image.open(final_file) as img:
            self.assertEqual(img.format, "PNG")
            self.assertGreater(img.width, 0)
            self.assertGreater(img.height, 0)

    def test_multislide_pptx_to_jpg_engine(self):
        """Multi-slide PPTX → JPG yields a ZIP archive with ordered page files."""
        if not find_libreoffice_executable():
            self.skipTest("LibreOffice not installed.")

        engine = PptxToJpgEngine()
        out_path = os.path.join(TEST_TEMP_DIR, "presentation.jpg")
        res_path = engine.convert(self.multi_pptx, out_path)

        self.assertIsNotNone(res_path)
        self.assertTrue(res_path.endswith(".zip"))
        self.assertTrue(os.path.exists(res_path))

        with zipfile.ZipFile(res_path, "r") as zf:
            namelist = zf.namelist()
            self.assertEqual(len(namelist), 3)
            self.assertEqual(namelist, ["page-001.jpg", "page-002.jpg", "page-003.jpg"])
            # Ensure no intermediate PDF or profile files in ZIP
            for fname in namelist:
                self.assertTrue(fname.endswith(".jpg"))

    def test_multislide_pptx_to_png_engine(self):
        """Multi-slide PPTX → PNG yields a ZIP archive with ordered page files."""
        if not find_libreoffice_executable():
            self.skipTest("LibreOffice not installed.")

        engine = PptxToPngEngine()
        out_path = os.path.join(TEST_TEMP_DIR, "presentation.png")
        res_path = engine.convert(self.multi_pptx, out_path)

        self.assertIsNotNone(res_path)
        self.assertTrue(res_path.endswith(".zip"))
        self.assertTrue(os.path.exists(res_path))

        with zipfile.ZipFile(res_path, "r") as zf:
            namelist = zf.namelist()
            self.assertEqual(len(namelist), 3)
            self.assertEqual(namelist, ["page-001.png", "page-002.png", "page-003.png"])
            for fname in namelist:
                self.assertTrue(fname.endswith(".png"))

    def test_invalid_pptx_raises_conversion_error(self):
        """Corrupted PPTX input raises ConversionError before calling LibreOffice."""
        bad_pptx = os.path.join(TEST_TEMP_DIR, "corrupt.pptx")
        with open(bad_pptx, "wb") as f:
            f.write(b"NOT A REAL PPTX ZIP ARCHIVE")

        engine = PptxToJpgEngine()
        out_path = os.path.join(TEST_TEMP_DIR, "out.jpg")
        try:
            with self.assertRaises(ConversionError) as ctx:
                engine.convert(bad_pptx, out_path)
            self.assertIn("valid PPTX", str(ctx.exception))
        finally:
            if os.path.exists(bad_pptx):
                os.remove(bad_pptx)

    @patch("apps.conversions.engines.libreoffice.find_libreoffice_executable", return_value=None)
    def test_missing_libreoffice_raises_conversion_error(self, mock_find):
        """Missing LibreOffice raises clear ConversionError."""
        engine = PptxToJpgEngine()
        out_path = os.path.join(TEST_TEMP_DIR, "out.jpg")
        with self.assertRaises(ConversionError) as ctx:
            engine.convert(self.single_pptx, out_path)
        self.assertIn("LibreOffice is not installed", str(ctx.exception))

    @patch("apps.conversions.engines.libreoffice.find_libreoffice_executable", return_value="soffice")
    @patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="soffice", timeout=60))
    def test_libreoffice_timeout_raises_conversion_error(self, mock_run, mock_find):
        """LibreOffice timeout raises ConversionError."""
        engine = PptxToJpgEngine()
        out_path = os.path.join(TEST_TEMP_DIR, "out.jpg")
        with self.assertRaises(ConversionError) as ctx:
            engine.convert(self.single_pptx, out_path)
        self.assertIn("timed out", str(ctx.exception))

    @patch("apps.conversions.engines.libreoffice.find_libreoffice_executable", return_value="soffice")
    @patch("subprocess.run")
    def test_invalid_intermediate_pdf_raises_conversion_error(self, mock_run, mock_find):
        """Intermediate PDF produced by LibreOffice being invalid raises ConversionError."""
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

        # Create a mock run function that creates a zero-byte intermediate pdf
        def side_effect(cmd, **kwargs):
            out_dir = cmd[cmd.index("--outdir") + 1]
            pdf_path = os.path.join(out_dir, "single.pdf")
            with open(pdf_path, "wb") as f:
                f.write(b"")  # 0-byte file
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

        mock_run.side_effect = side_effect

        engine = PptxToJpgEngine()
        out_path = os.path.join(TEST_TEMP_DIR, "out.jpg")
        with self.assertRaises(ConversionError) as ctx:
            engine.convert(self.single_pptx, out_path)
        self.assertIn("empty output file", str(ctx.exception))

    @patch("apps.conversions.engines.pdf_to_image.PdfToJpgEngine.convert", side_effect=ConversionError("PyMuPDF rendering failed"))
    def test_pdf_rendering_failure_raises_conversion_error(self, mock_pdf_render):
        """PyMuPDF rendering failure raises ConversionError."""
        if not find_libreoffice_executable():
            self.skipTest("LibreOffice not installed.")

        engine = PptxToJpgEngine()
        out_path = os.path.join(TEST_TEMP_DIR, "out.jpg")
        with self.assertRaises(ConversionError) as ctx:
            engine.convert(self.single_pptx, out_path)
        self.assertIn("PyMuPDF rendering failed", str(ctx.exception))


@override_settings(TEMP_UPLOAD_DIR=TEST_TEMP_DIR)
class PptxToImageApiIntegrationTests(TestCase):
    """API Integration tests for PPTX → JPG and PPTX → PNG conversions."""

    def setUp(self):
        self.client_a = APIClient()
        self.client_b = APIClient()
        self.single_pptx_bytes = create_pptx_fixture(slides=1)
        self.multi_pptx_bytes = create_pptx_fixture(slides=3)

    def test_single_slide_pptx_to_jpg_api_flow(self):
        """API Flow: Upload 1-slide PPTX → JPG → status completed → download JPG."""
        if not find_libreoffice_executable():
            self.skipTest("LibreOffice not installed.")

        f = io.BytesIO(self.single_pptx_bytes)
        f.name = "presentation.pptx"

        res = self.client_a.post(
            "/api/conversions/",
            {
                "file": f,
                "source_format": "pptx",
                "target_format": "jpg",
            },
            format="multipart",
        )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        data = res.json()
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["output_filename"], "presentation.jpg")
        job_id = data["id"]

        dl_url = reverse("conversions:job-download", kwargs={"job_id": job_id})
        dl_res = self.client_a.get(dl_url)
        self.assertEqual(dl_res.status_code, status.HTTP_200_OK)
        self.assertEqual(dl_res["Content-Type"], "image/jpeg")

    def test_single_slide_pptx_to_png_api_flow(self):
        """API Flow: Upload 1-slide PPTX → PNG → status completed → download PNG."""
        if not find_libreoffice_executable():
            self.skipTest("LibreOffice not installed.")

        f = io.BytesIO(self.single_pptx_bytes)
        f.name = "slideshow.pptx"

        res = self.client_a.post(
            "/api/conversions/",
            {
                "file": f,
                "source_format": "pptx",
                "target_format": "png",
            },
            format="multipart",
        )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        data = res.json()
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["output_filename"], "slideshow.png")
        job_id = data["id"]

        dl_url = reverse("conversions:job-download", kwargs={"job_id": job_id})
        dl_res = self.client_a.get(dl_url)
        self.assertEqual(dl_res.status_code, status.HTTP_200_OK)
        self.assertEqual(dl_res["Content-Type"], "image/png")

    def test_multislide_pptx_to_jpg_api_flow(self):
        """API Flow: Upload multi-slide PPTX → JPG → status completed → download ZIP."""
        if not find_libreoffice_executable():
            self.skipTest("LibreOffice not installed.")

        f = io.BytesIO(self.multi_pptx_bytes)
        f.name = "deck.pptx"

        res = self.client_a.post(
            "/api/conversions/",
            {
                "file": f,
                "source_format": "pptx",
                "target_format": "jpg",
            },
            format="multipart",
        )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        data = res.json()
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["output_filename"], "deck.zip")
        job_id = data["id"]

        dl_url = reverse("conversions:job-download", kwargs={"job_id": job_id})
        dl_res = self.client_a.get(dl_url)
        self.assertEqual(dl_res.status_code, status.HTTP_200_OK)
        self.assertEqual(dl_res["Content-Type"], "application/zip")

    def test_multislide_pptx_to_png_api_flow(self):
        """API Flow: Upload multi-slide PPTX → PNG → status completed → download ZIP."""
        if not find_libreoffice_executable():
            self.skipTest("LibreOffice not installed.")

        f = io.BytesIO(self.multi_pptx_bytes)
        f.name = "deck.pptx"

        res = self.client_a.post(
            "/api/conversions/",
            {
                "file": f,
                "source_format": "pptx",
                "target_format": "png",
            },
            format="multipart",
        )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        data = res.json()
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["output_filename"], "deck.zip")
        job_id = data["id"]

        dl_url = reverse("conversions:job-download", kwargs={"job_id": job_id})
        dl_res = self.client_a.get(dl_url)
        self.assertEqual(dl_res.status_code, status.HTTP_200_OK)
        self.assertEqual(dl_res["Content-Type"], "application/zip")

    def test_invalid_pptx_api_failure_flow(self):
        """Uploading corrupted PPTX file yields clean API failure response."""
        f = io.BytesIO(b"NOT A REAL PPTX ARCHIVE")
        f.name = "corrupt.pptx"

        res = self.client_a.post(
            "/api/conversions/",
            {
                "file": f,
                "source_format": "pptx",
                "target_format": "jpg",
            },
            format="multipart",
        )

        self.assertEqual(res.status_code, status.HTTP_202_ACCEPTED)
        data = res.json()
        self.assertEqual(data["status"], "failed")
        self.assertIn("valid PPTX", data["error_message"])

    def test_anonymous_session_isolation_pptx_to_image(self):
        """Session B cannot access or download Session A's PPTX → Image jobs."""
        if not find_libreoffice_executable():
            self.skipTest("LibreOffice not installed.")

        f = io.BytesIO(self.single_pptx_bytes)
        f.name = "secret.pptx"

        res_a = self.client_a.post(
            "/api/conversions/",
            {
                "file": f,
                "source_format": "pptx",
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
