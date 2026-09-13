"""
Tests for OCR Operations and Milestone Features:
  - Tesseract discovery, engine detection, and language diagnostics
  - Shared OCR validation (file sizes, image dimensions, PDF encryption, page limits, DPI/PSM options)
  - Operation 1: ocr_image_to_searchable_pdf (Image -> Searchable PDF)
  - Operation 2: ocr_image_to_txt (Image -> UTF-8 TXT)
  - Operation 3: ocr_pdf_to_txt (PDF -> TXT with hybrid native + OCR strategy)
  - Operation 4: ocr_scanned_pdf_to_searchable_pdf (Scanned PDF -> Searchable PDF)
  - API endpoint integration (POST /api/v1/ocr/)
  - Real Tesseract integration tests (skipped if Tesseract is not installed)
"""

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import fitz  # PyMuPDF
from PIL import Image

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.conversions.engines.base import ConversionError
from apps.conversions.engines.ocr_engine import (
    OcrImageToSearchablePdfEngine,
    OcrImageToTxtEngine,
    OcrPdfToTxtEngine,
    OcrScannedPdfToSearchablePdfEngine,
)
from apps.conversions.engines.validators import (
    MAX_OCR_IMAGE_DIM,
    MAX_OCR_IMAGE_SIZE,
    MAX_OCR_PDF_PAGES,
    MAX_OCR_PDF_SIZE,
    validate_ocr_input,
)
from apps.conversions.models import ConversionJob, JobStatus
from apps.conversions.services import ConversionService
from apps.conversions.utils.ocr_helper import (
    discover_tesseract_cmd,
    get_ocr_engine_info,
    validate_ocr_language,
)

User = get_user_model()


def is_tesseract_available() -> bool:
    """Return True if Tesseract executable is installed on this host."""
    info = get_ocr_engine_info()
    return info["available"]


def create_sample_pdf(path: str, page_count: int = 1, text_prefix: str = "Sample") -> None:
    """Helper to create a valid test PDF file using PyMuPDF."""
    doc = fitz.open()
    for i in range(page_count):
        page = doc.new_page(width=595, height=842)  # A4 size
        if text_prefix:
            page.insert_text((50, 50), f"{text_prefix} Page {i + 1}")
    doc.save(path)
    doc.close()


def create_sample_scanned_pdf(path: str, page_count: int = 1) -> None:
    """Helper to create an image-only (scanned) PDF file without native text."""
    doc = fitz.open()
    for i in range(page_count):
        # Create image with PIL
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_img:
            img = Image.new("RGB", (300, 400), color=(255, 255, 255))
            img.save(tmp_img.name)
            tmp_img_path = tmp_img.name

        try:
            page = doc.new_page(width=595, height=842)
            page.insert_image(page.rect, filename=tmp_img_path)
        finally:
            if os.path.exists(tmp_img_path):
                os.remove(tmp_img_path)
    doc.save(path)
    doc.close()


def create_sample_image(path: str, fmt: str = "PNG", size=(400, 300)) -> None:
    """Helper to create a sample image file."""
    img = Image.new("RGB", size, color=(240, 240, 240))
    img.save(path, format=fmt)


# ── 1. Engine Detection & Diagnostics Tests ────────────────────────────────────

class OcrEngineDiagnosticsTestCase(TestCase):
    """Tests for OCR discovery, diagnostics, and language validation."""

    def test_get_ocr_engine_info_structure(self):
        info = get_ocr_engine_info()
        self.assertIsInstance(info, dict)
        self.assertIn("available", info)
        self.assertIn("tesseract_cmd", info)
        self.assertIn("version", info)
        self.assertIn("languages", info)
        self.assertIn("has_tamil", info)
        self.assertIsInstance(info["available"], bool)
        self.assertIsInstance(info["languages"], list)

    @patch("apps.conversions.utils.ocr_helper.get_ocr_engine_info")
    def test_validate_ocr_language_success(self, mock_info):
        mock_info.return_value = {
            "available": True,
            "tesseract_cmd": "/usr/bin/tesseract",
            "version": "5.3.0",
            "languages": ["eng", "osd", "tam"],
            "has_tamil": True,
            "error": None,
        }
        res_eng = validate_ocr_language("eng")
        self.assertEqual(res_eng, "eng")

        res_tam = validate_ocr_language("tam")
        self.assertEqual(res_tam, "tam")

        res_combined = validate_ocr_language("eng+tam")
        self.assertEqual(res_combined, "eng+tam")

    @patch("apps.conversions.utils.ocr_helper.get_ocr_engine_info")
    def test_validate_ocr_language_missing_tamil(self, mock_info):
        mock_info.return_value = {
            "available": True,
            "tesseract_cmd": "/usr/bin/tesseract",
            "version": "5.3.0",
            "languages": ["eng", "osd"],
            "has_tamil": False,
            "error": None,
        }
        with self.assertRaises(ConversionError) as ctx:
            validate_ocr_language("tam")
        self.assertIn("ocr_language_unavailable", str(ctx.exception))
        self.assertIn("Tamil OCR language pack ('tam') is not installed", str(ctx.exception))

    @patch("apps.conversions.utils.ocr_helper.get_ocr_engine_info")
    def test_validate_ocr_engine_unavailable(self, mock_info):
        mock_info.return_value = {
            "available": False,
            "tesseract_cmd": None,
            "version": None,
            "languages": [],
            "has_tamil": False,
            "error": "ocr_engine_unavailable: Tesseract not found",
        }
        with self.assertRaises(ConversionError) as ctx:
            validate_ocr_language("eng")
        self.assertIn("ocr_engine_unavailable", str(ctx.exception))


# ── 2. Shared Validation Tests ────────────────────────────────────────────────

class OcrValidationTestCase(TestCase):
    """Tests for validate_ocr_input safety limits and option checks."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="velto_test_ocr_val_")
        self.sample_img = os.path.join(self.temp_dir.name, "test.png")
        create_sample_image(self.sample_img)

        self.sample_pdf = os.path.join(self.temp_dir.name, "test.pdf")
        create_sample_pdf(self.sample_pdf)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_validate_missing_file(self):
        with self.assertRaises(ConversionError) as ctx:
            validate_ocr_input(os.path.join(self.temp_dir.name, "nonexistent.png"))
        self.assertIn("invalid_file", str(ctx.exception))

    def test_validate_empty_file(self):
        empty_file = os.path.join(self.temp_dir.name, "empty.png")
        Path(empty_file).touch()
        with self.assertRaises(ConversionError) as ctx:
            validate_ocr_input(empty_file)
        self.assertIn("invalid_file", str(ctx.exception))

    def test_validate_outside_session_dir(self):
        with self.assertRaises(ConversionError) as ctx:
            validate_ocr_input(self.sample_img, session_dir=os.path.join(self.temp_dir.name, "other_session"))
        self.assertIn("invalid_file", str(ctx.exception))

    def test_validate_image_dimension_exceeded(self):
        with patch("PIL.Image.open") as mock_img:
            mock_obj = MagicMock()
            mock_obj.size = (15000, 2000)
            mock_img.return_value.__enter__.return_value = mock_obj

            with self.assertRaises(ConversionError) as ctx:
                validate_ocr_input(self.sample_img, is_pdf=False)
            self.assertIn("image_dimensions_exceeded", str(ctx.exception))

    def test_validate_pdf_page_count_exceeded(self):
        large_pdf = os.path.join(self.temp_dir.name, "large.pdf")
        create_sample_pdf(large_pdf, page_count=MAX_OCR_PDF_PAGES + 1)

        with self.assertRaises(ConversionError) as ctx:
            validate_ocr_input(large_pdf, is_pdf=True)
        self.assertIn("page_count_exceeded", str(ctx.exception))

    def test_validate_encrypted_pdf_rejection(self):
        enc_pdf = os.path.join(self.temp_dir.name, "encrypted.pdf")
        doc = fitz.open()
        doc.new_page()
        doc.save(enc_pdf, encryption=fitz.PDF_ENCRYPT_AES_256, user_pw="pass", owner_pw="pass")
        doc.close()

        with self.assertRaises(ConversionError) as ctx:
            validate_ocr_input(enc_pdf, is_pdf=True)
        self.assertIn("encrypted_pdf", str(ctx.exception))

    def test_validate_dpi_bounds(self):
        with self.assertRaises(ConversionError) as ctx:
            validate_ocr_input(self.sample_img, is_pdf=False, options={"dpi": 50})
        self.assertIn("invalid_dpi", str(ctx.exception))

        with self.assertRaises(ConversionError) as ctx:
            validate_ocr_input(self.sample_img, is_pdf=False, options={"dpi": 1000})
        self.assertIn("invalid_dpi", str(ctx.exception))

    def test_validate_psm_bounds(self):
        with self.assertRaises(ConversionError) as ctx:
            validate_ocr_input(self.sample_img, is_pdf=False, options={"psm": 15})
        self.assertIn("invalid_psm", str(ctx.exception))


# ── 3. Pipeline & Engine Tests (Mocked Tesseract) ─────────────────────────────

class OcrEnginesMockedPipelineTestCase(TestCase):
    """Unit tests for all 4 OCR engines using mocked Tesseract execution."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="velto_test_ocr_mock_")
        self.src_img = os.path.join(self.temp_dir.name, "sample.png")
        create_sample_image(self.src_img, fmt="PNG", size=(300, 200))

        self.src_pdf = os.path.join(self.temp_dir.name, "sample.pdf")
        create_sample_pdf(self.src_pdf, page_count=2, text_prefix="NativeText")

        self.scanned_pdf = os.path.join(self.temp_dir.name, "scanned.pdf")
        create_sample_scanned_pdf(self.scanned_pdf, page_count=2)

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch("apps.conversions.utils.ocr_helper.get_ocr_engine_info")
    @patch("pytesseract.image_to_pdf_or_hocr")
    def test_ocr_image_to_searchable_pdf_engine(self, mock_hocr, mock_info):
        mock_info.return_value = {
            "available": True,
            "tesseract_cmd": "/usr/bin/tesseract",
            "version": "5.3.0",
            "languages": ["eng"],
            "has_tamil": False,
            "error": None,
        }
        # Mock pytesseract returning a dummy searchable PDF byte stream
        dummy_pdf = fitz.open()
        p = dummy_pdf.new_page(width=300, height=200)
        p.insert_text((50, 50), "Searchable Text Layer")
        pdf_bytes = dummy_pdf.tobytes()
        dummy_pdf.close()

        mock_hocr.return_value = pdf_bytes

        out_pdf = os.path.join(self.temp_dir.name, "out_searchable.pdf")
        engine = OcrImageToSearchablePdfEngine()
        opts = {"language": "eng", "dpi": 300}

        res = engine.convert(self.src_img, out_pdf, options=opts)
        self.assertEqual(res, out_pdf)

        doc = fitz.open(out_pdf)
        self.assertEqual(len(doc), 1)
        self.assertIn("Searchable Text Layer", doc[0].get_text())
        doc.close()

        res_meta = opts.get("result_metadata")
        self.assertIsNotNone(res_meta)
        self.assertEqual(res_meta["language"], "eng")
        self.assertTrue(res_meta["has_searchable_text"])

    @patch("apps.conversions.utils.ocr_helper.get_ocr_engine_info")
    @patch("pytesseract.image_to_string")
    def test_ocr_image_to_txt_engine(self, mock_img_to_str, mock_info):
        mock_info.return_value = {
            "available": True,
            "tesseract_cmd": "/usr/bin/tesseract",
            "version": "5.3.0",
            "languages": ["eng"],
            "has_tamil": False,
            "error": None,
        }
        mock_img_to_str.return_value = "Extracted OCR Text from Image"

        out_txt = os.path.join(self.temp_dir.name, "out_ocr.txt")
        engine = OcrImageToTxtEngine()
        opts = {"language": "eng"}

        res = engine.convert(self.src_img, out_txt, options=opts)
        self.assertEqual(res, out_txt)

        with open(out_txt, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertEqual(content, "Extracted OCR Text from Image")

        res_meta = opts.get("result_metadata")
        self.assertIsNotNone(res_meta)
        self.assertEqual(res_meta["text_length"], len("Extracted OCR Text from Image"))
        self.assertTrue(res_meta["has_text"])

    @patch("apps.conversions.utils.ocr_helper.get_ocr_engine_info")
    @patch("pytesseract.image_to_string")
    def test_ocr_pdf_to_txt_hybrid_strategy(self, mock_img_to_str, mock_info):
        mock_info.return_value = {
            "available": True,
            "tesseract_cmd": "/usr/bin/tesseract",
            "version": "5.3.0",
            "languages": ["eng"],
            "has_tamil": False,
            "error": None,
        }
        mock_img_to_str.return_value = "Scanned Page OCR Output"

        # Hybrid PDF: Page 1 has native text, Page 2 is scanned (empty)
        hybrid_pdf = os.path.join(self.temp_dir.name, "hybrid.pdf")
        doc = fitz.open()
        p1 = doc.new_page(width=595, height=842)
        p1.insert_text((50, 50), "Native Text Content on Page One")
        p2 = doc.new_page(width=595, height=842)  # scanned (no text)
        doc.save(hybrid_pdf)
        doc.close()

        out_txt = os.path.join(self.temp_dir.name, "out_hybrid.txt")
        engine = OcrPdfToTxtEngine()
        opts = {"language": "eng"}

        res = engine.convert(hybrid_pdf, out_txt, options=opts)
        self.assertEqual(res, out_txt)

        with open(out_txt, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("--- Page 1 ---", content)
        self.assertIn("Native Text Content on Page One", content)
        self.assertIn("--- Page 2 ---", content)
        self.assertIn("Scanned Page OCR Output", content)

        res_meta = opts.get("result_metadata")
        self.assertEqual(res_meta["total_pages"], 2)
        self.assertEqual(res_meta["native_pages_count"], 1)
        self.assertEqual(res_meta["ocr_pages_count"], 1)

    @patch("apps.conversions.utils.ocr_helper.get_ocr_engine_info")
    @patch("pytesseract.image_to_pdf_or_hocr")
    def test_ocr_scanned_pdf_to_searchable_pdf_engine(self, mock_hocr, mock_info):
        mock_info.return_value = {
            "available": True,
            "tesseract_cmd": "/usr/bin/tesseract",
            "version": "5.3.0",
            "languages": ["eng"],
            "has_tamil": False,
            "error": None,
        }
        dummy_pdf = fitz.open()
        p = dummy_pdf.new_page(width=595, height=842)
        p.insert_text((50, 50), "Searchable Scanned Layer")
        pdf_bytes = dummy_pdf.tobytes()
        dummy_pdf.close()

        mock_hocr.return_value = pdf_bytes

        out_pdf = os.path.join(self.temp_dir.name, "out_searchable_scanned.pdf")
        engine = OcrScannedPdfToSearchablePdfEngine()
        opts = {"language": "eng"}

        res = engine.convert(self.scanned_pdf, out_pdf, options=opts)
        self.assertEqual(res, out_pdf)

        doc = fitz.open(out_pdf)
        self.assertEqual(len(doc), 2)
        doc.close()

        res_meta = opts.get("result_metadata")
        self.assertEqual(res_meta["total_pages"], 2)
        self.assertEqual(res_meta["scanned_pages_ocred"], 2)


# ── 4. API Endpoint Integration Tests ─────────────────────────────────────────

class OcrApiEndpointTestCase(TestCase):
    """API endpoint integration tests for POST /api/v1/ocr/."""

    def setUp(self):
        self.client = APIClient()
        self.temp_dir = tempfile.TemporaryDirectory(prefix="velto_test_ocr_api_")
        self.url = reverse("conversions:ocr-utilities")

        self.sample_img_path = os.path.join(self.temp_dir.name, "sample.png")
        create_sample_image(self.sample_img_path)

        self.sample_pdf_path = os.path.join(self.temp_dir.name, "sample.pdf")
        create_sample_pdf(self.sample_pdf_path, page_count=1, text_prefix="ApiDoc")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_api_ocr_invalid_operation(self):
        with open(self.sample_img_path, "rb") as f:
            resp = self.client.post(
                self.url,
                {"operation": "ocr_invalid_xyz", "file": f},
                format="multipart",
            )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("unsupported_operation", resp.data["message"])

    def test_api_ocr_missing_file(self):
        resp = self.client.post(
            self.url,
            {"operation": "ocr_image_to_txt"},
            format="multipart",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("invalid_file", resp.data["message"])

    @patch("apps.conversions.utils.ocr_helper.get_ocr_engine_info")
    @patch("pytesseract.image_to_string")
    def test_api_ocr_image_to_txt_success(self, mock_str, mock_info):
        mock_info.return_value = {
            "available": True,
            "tesseract_cmd": "/usr/bin/tesseract",
            "version": "5.3.0",
            "languages": ["eng"],
            "has_tamil": False,
            "error": None,
        }
        mock_str.return_value = "API OCR Extracted Content"

        with open(self.sample_img_path, "rb") as f:
            resp = self.client.post(
                self.url,
                {
                    "operation": "ocr_image_to_txt",
                    "file": f,
                    "language": "eng",
                    "dpi": 300,
                },
                format="multipart",
            )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["status"], "completed")

        job_id = resp.data["id"]
        job = ConversionJob.objects.get(id=job_id)
        self.assertEqual(job.target_format, "txt")
        self.assertTrue(os.path.exists(job.output_path))

    @patch("apps.conversions.utils.ocr_helper.get_ocr_engine_info")
    def test_api_ocr_engine_unavailable_handled_cleanly(self, mock_info):
        mock_info.return_value = {
            "available": False,
            "tesseract_cmd": None,
            "version": None,
            "languages": [],
            "has_tamil": False,
            "error": "ocr_engine_unavailable: Tesseract not found",
        }
        with open(self.sample_img_path, "rb") as f:
            resp = self.client.post(
                self.url,
                {
                    "operation": "ocr_image_to_txt",
                    "file": f,
                },
                format="multipart",
            )
        # Should return 202 with FAILED status and error message
        self.assertEqual(resp.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(resp.data["status"], "failed")
        self.assertIn("ocr_engine_unavailable", resp.data["error_message"])


# ── 5. Real Tesseract Engine Integration Tests (Conditional) ─────────────────

class OcrRealEngineIntegrationTestCase(TestCase):
    """Integration tests executing real Tesseract OCR (skipped if not installed)."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="velto_test_real_ocr_")
        self.sample_img = os.path.join(self.temp_dir.name, "real.png")
        create_sample_image(self.sample_img, fmt="PNG")

    def tearDown(self):
        self.temp_dir.cleanup()

    @unittest.skipUnless(is_tesseract_available(), "Tesseract OCR binary is not installed in the environment.")
    def test_real_ocr_image_to_txt(self):
        out_txt = os.path.join(self.temp_dir.name, "real_out.txt")
        engine = OcrImageToTxtEngine()
        opts = {"language": "eng"}
        res = engine.convert(self.sample_img, out_txt, options=opts)
        self.assertEqual(res, out_txt)
        self.assertTrue(os.path.exists(out_txt))
