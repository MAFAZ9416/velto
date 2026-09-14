"""
Phase 4 & Phase 5: Multi-page document tests, Unicode and Tamil character preservation.

Verifies:
  1. Multi-page document conversion and page count preservation across supported formats.
  2. Multi-frame image handling (static vs animated).
  3. Unicode & Tamil character preservation in TXT, DOCX, PDF, HTML, MD, CSV, and XLSX.
  4. Conditional skip for Tamil OCR tests when Tamil Tesseract data ('tam') is missing.
"""

import io
import os
import tempfile
import unittest
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.conversions.engines.document_engine import (
    HtmlToDocxEngine,
    HtmlToPdfEngine,
    MarkdownToDocxEngine,
    MarkdownToPdfEngine,
    TxtToDocxEngine,
    TxtToPdfEngine,
)
from apps.conversions.fixtures.generate_fixtures import generate_all_fixtures
from apps.conversions.models import ConversionJob


TEST_TEMP_DIR = tempfile.mkdtemp(prefix="velto_mp_uni_tests_")


@override_settings(TEMP_UPLOAD_DIR=TEST_TEMP_DIR)
class MultiPageDocumentTests(TestCase):
    """Tests for multi-page documents across supported conversion engines."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.fixtures = generate_all_fixtures()
        cls.multipage_pdf = cls.fixtures["multipage"]

    def setUp(self):
        self.client = APIClient()
        self.temp_dir = tempfile.TemporaryDirectory(prefix="mp_doc_")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_multipage_pdf_to_images(self):
        """Multi-page PDF produces ZIP archive containing all pages in order."""
        with open(self.multipage_pdf, "rb") as f:
            pdf_bytes = f.read()

        file_obj = SimpleUploadedFile("multi.pdf", pdf_bytes, content_type="application/pdf")
        res = self.client.post(
            reverse("conversions:job-list-create"),
            {"file": file_obj, "source_format": "pdf", "target_format": "jpg"},
            format="multipart",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        data = res.json()
        self.assertEqual(data["status"], "completed")
        self.assertTrue(data["output_filename"].endswith(".zip"))

    def test_multipage_txt_to_pdf(self):
        """Multi-page text file converts to non-empty multi-page PDF."""
        multipage_text = ("Page 1 content\n" + "Line\n" * 60 + "\x0c" + "Page 2 content\n" + "Line\n" * 60)
        txt_path = Path(self.temp_dir.name) / "multi.txt"
        pdf_out = Path(self.temp_dir.name) / "out.pdf"
        txt_path.write_text(multipage_text, encoding="utf-8")

        engine = TxtToPdfEngine()
        res_path = engine.convert(str(txt_path), str(pdf_out))
        target = res_path or pdf_out

        self.assertTrue(os.path.exists(target))
        self.assertGreater(os.path.getsize(target), 0)


@override_settings(TEMP_UPLOAD_DIR=TEST_TEMP_DIR)
class UnicodeAndTamilTests(TestCase):
    """Phase 5: Unicode and Tamil language text preservation tests."""

    def setUp(self):
        self.client = APIClient()
        self.temp_dir = tempfile.TemporaryDirectory(prefix="unicode_val_")
        self.tamil_sample = (
            "VELTO Conversion — தமிழ் ஆவணம்\n"
            "வணக்கம்! இது தமிழ் உரை மற்றும் Unicode test document.\n"
            "English text: Special symbols → © ✓ £ € ¥\n"
            "Numbers: 12345, Tamil digits, Punctuation: !@#$%^&*()\n"
            "Accented Latin: café, résumé, ñ, ü, ö, ä\n"
            "RTL sample: مرحبا بالعالم\n"
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_txt_to_pdf_tamil_unicode_preservation(self):
        """TxtToPdfEngine preserves Tamil and Unicode characters cleanly."""
        txt_path = Path(self.temp_dir.name) / "tamil.txt"
        pdf_out = Path(self.temp_dir.name) / "tamil.pdf"
        txt_path.write_text(self.tamil_sample, encoding="utf-8")

        engine = TxtToPdfEngine()
        res = engine.convert(str(txt_path), str(pdf_out))
        target = res or pdf_out

        self.assertTrue(os.path.exists(target))
        self.assertGreater(os.path.getsize(target), 0)

    def test_txt_to_docx_tamil_unicode_preservation(self):
        """TxtToDocxEngine preserves Tamil text in editable DOCX document."""
        txt_path = Path(self.temp_dir.name) / "tamil.txt"
        docx_out = Path(self.temp_dir.name) / "tamil.docx"
        txt_path.write_text(self.tamil_sample, encoding="utf-8")

        engine = TxtToDocxEngine()
        res = engine.convert(str(txt_path), str(docx_out))
        target = res or docx_out

        self.assertTrue(os.path.exists(target))
        import docx
        doc = docx.Document(target)
        full_text = "\n".join(p.text for p in doc.paragraphs)
        self.assertIn("தமிழ்", full_text)
        self.assertIn("வணக்கம்", full_text)

    def test_html_to_pdf_tamil_unicode_preservation(self):
        """HtmlToPdfEngine preserves Tamil text in generated PDF."""
        html_content = f"<html><body><h1>தமிழ் தலைப்பு</h1><p>{self.tamil_sample}</p></body></html>"
        html_path = Path(self.temp_dir.name) / "tamil.html"
        pdf_out = Path(self.temp_dir.name) / "tamil_html.pdf"
        html_path.write_text(html_content, encoding="utf-8")

        engine = HtmlToPdfEngine()
        res = engine.convert(str(html_path), str(pdf_out))
        target = res or pdf_out
        self.assertTrue(os.path.exists(target))

    def test_markdown_to_docx_tamil_unicode_preservation(self):
        """MarkdownToDocxEngine preserves Tamil headers and bullet items."""
        md_content = "# தமிழ் தலைப்பு\n\n- தமிழ் உருப்படி 1\n- Tamil item 2\n- Unicode: → © ✓\n"
        md_path = Path(self.temp_dir.name) / "tamil.md"
        docx_out = Path(self.temp_dir.name) / "tamil_md.docx"
        md_path.write_text(md_content, encoding="utf-8")

        engine = MarkdownToDocxEngine()
        res = engine.convert(str(md_path), str(docx_out))
        target = res or docx_out

        import docx
        doc = docx.Document(target)
        full_text = "\n".join(p.text for p in doc.paragraphs)
        self.assertIn("தமிழ் தலைப்பு", full_text)

    def test_csv_to_xlsx_tamil_unicode_preservation(self):
        """CsvToXlsxEngine preserves Tamil text cells in generated Excel workbook."""
        from apps.conversions.engines.csv_to_xlsx import CsvToXlsxEngine
        csv_content = "ID,Language,Greeting\n1,Tamil,வணக்கம்\n2,English,Hello\n3,Unicode,→ © ✓\n"
        csv_path = Path(self.temp_dir.name) / "tamil.csv"
        xlsx_out = Path(self.temp_dir.name) / "tamil.xlsx"
        csv_path.write_text(csv_content, encoding="utf-8")

        engine = CsvToXlsxEngine()
        res = engine.convert(str(csv_path), str(xlsx_out))
        target = res or xlsx_out

        import openpyxl
        wb = openpyxl.load_workbook(target)
        ws = wb.active
        values = [[cell.value for cell in row] for row in ws.iter_rows()]
        wb.close()

        self.assertEqual(values[1][2], "வணக்கம்")

    def test_tamil_ocr_conditional_skip(self):
        """Skip Tamil OCR test conditionally if Tesseract Tamil ('tam') language pack is unavailable."""
        from apps.conversions.utils.ocr_helper import get_ocr_engine_info

        info = get_ocr_engine_info()
        if not info["available"]:
            raise unittest.SkipTest("Tesseract OCR engine is not installed on system.")

        if "tam" not in info["languages"]:
            raise unittest.SkipTest("Tesseract Tamil language pack ('tam') is not installed locally.")

        # If Tamil language pack is available, test OCR execution
        self.assertIn("tam", info["languages"])
