"""
Tests for PDF Utilities Phase 5A:
  - Shared PDF validation
  - Page-range parser
  - PDF merge (pdf_merge)
  - PDF split (pdf_split: every_page, ranges, chunks)
  - PDF page extraction (pdf_extract_pages)
"""

import os
from pathlib import Path
import tempfile
import zipfile
import fitz  # PyMuPDF
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.conversions.engines.base import ConversionError
from apps.conversions.engines.pdf_utility_engine import (
    PdfExtractPagesEngine,
    PdfMergeEngine,
    PdfSplitEngine,
)
from apps.conversions.engines.validators import (
    validate_pdf_utility_input,
)
from apps.conversions.models import ConversionJob, JobStatus
from apps.conversions.services import ConversionService
from apps.conversions.utils.page_range import parse_page_range

User = get_user_model()


def create_dummy_pdf(path: str, page_count: int = 1, text_prefix: str = "Page") -> None:
    """Helper to create a valid test PDF file using PyMuPDF."""
    doc = fitz.open()
    for i in range(page_count):
        page = doc.new_page(width=595, height=842)  # A4 standard
        page.insert_text((50, 50), f"{text_prefix} {i + 1}")
    doc.save(path)
    doc.close()


class PageRangeParserTestCase(TestCase):
    """Unit tests for 1-based page-range parser."""

    def test_single_page(self):
        result = parse_page_range("1", total_pages=5)
        self.assertEqual(result, [0])

    def test_comma_separated_pages(self):
        result = parse_page_range("1,3,5", total_pages=5)
        self.assertEqual(result, [0, 2, 4])

    def test_page_range_hyphen(self):
        result = parse_page_range("1-4", total_pages=5)
        self.assertEqual(result, [0, 1, 2, 3])

    def test_complex_range_and_pages(self):
        result = parse_page_range("2-5,8,10-12", total_pages=15)
        self.assertEqual(result, [1, 2, 3, 4, 7, 9, 10, 11])

    def test_reject_zero_or_negative(self):
        with self.assertRaises(ConversionError) as ctx:
            parse_page_range("0", total_pages=5)
        self.assertIn("page_range_invalid", str(ctx.exception))

        with self.assertRaises(ConversionError) as ctx:
            parse_page_range("-1", total_pages=5)
        self.assertIn("page_range_invalid", str(ctx.exception))

    def test_reject_malformed_syntax(self):
        bad_expressions = ["abc", "1--3", "1-2-3", "1,2,", ",3"]
        for expr in bad_expressions:
            with self.assertRaises(ConversionError) as ctx:
                parse_page_range(expr, total_pages=10)
            self.assertIn("page_range_invalid", str(ctx.exception))

    def test_reject_reversed_ranges(self):
        with self.assertRaises(ConversionError) as ctx:
            parse_page_range("5-2", total_pages=10)
        self.assertIn("page_range_invalid", str(ctx.exception))

    def test_reject_out_of_bounds_pages(self):
        with self.assertRaises(ConversionError) as ctx:
            parse_page_range("10", total_pages=5)
        self.assertIn("page_count_exceeded", str(ctx.exception))

    def test_reject_empty_selection(self):
        with self.assertRaises(ConversionError) as ctx:
            parse_page_range("", total_pages=5)
        self.assertIn("page_range_invalid", str(ctx.exception))

    def test_preserve_order(self):
        result = parse_page_range("3,1,2", total_pages=5, allow_duplicates=True)
        self.assertEqual(result, [2, 0, 1])

    def test_reject_duplicates_when_prohibited(self):
        with self.assertRaises(ConversionError) as ctx:
            parse_page_range("1,1,2", total_pages=5, allow_duplicates=False)
        self.assertIn("page_range_invalid", str(ctx.exception))


class PdfValidationTestCase(TestCase):
    """Unit tests for shared PDF input validation rules."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_validate_pdf_utility_input_success(self):
        pdf_path = os.path.join(self.temp_dir.name, "valid.pdf")
        create_dummy_pdf(pdf_path, page_count=3)
        docs = validate_pdf_utility_input([pdf_path], session_dir=self.temp_dir.name)
        self.assertEqual(len(docs), 1)
        self.assertEqual(len(docs[0]), 3)
        docs[0].close()

    def test_validate_pdf_missing_file(self):
        pdf_path = os.path.join(self.temp_dir.name, "missing.pdf")
        with self.assertRaises(ConversionError) as ctx:
            validate_pdf_utility_input([pdf_path])
        self.assertIn("invalid_pdf", str(ctx.exception))

    def test_validate_pdf_outside_session(self):
        pdf_path = os.path.join(self.temp_dir.name, "valid.pdf")
        create_dummy_pdf(pdf_path, page_count=1)
        other_session = os.path.join(self.temp_dir.name, "other_session")
        os.makedirs(other_session, exist_ok=True)
        with self.assertRaises(ConversionError) as ctx:
            validate_pdf_utility_input([pdf_path], session_dir=other_session)
        self.assertIn("invalid_pdf", str(ctx.exception))

    def test_validate_pdf_corrupted(self):
        corrupt_path = os.path.join(self.temp_dir.name, "corrupt.pdf")
        with open(corrupt_path, "wb") as f:
            f.write(b"Not a valid PDF header or content")
        with self.assertRaises(ConversionError) as ctx:
            validate_pdf_utility_input([corrupt_path])
        self.assertTrue("Expected file header '%PDF'" in str(ctx.exception) or "invalid_pdf" in str(ctx.exception))

    def test_validate_pdf_encrypted(self):
        pdf_path = os.path.join(self.temp_dir.name, "encrypted.pdf")
        doc = fitz.open()
        doc.new_page()
        # Save with owner password encryption
        doc.save(pdf_path, encryption=fitz.PDF_ENCRYPT_AES_128, owner_pw="secret", user_pw="protected")
        doc.close()

        with self.assertRaises(ConversionError) as ctx:
            validate_pdf_utility_input([pdf_path])
        self.assertIn("encrypted_pdf", str(ctx.exception))


class PdfMergeEngineTestCase(TestCase):
    """Unit tests for PdfMergeEngine."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_pdf_merge_success_and_ordering(self):
        pdf1 = os.path.join(self.temp_dir.name, "doc1.pdf")
        pdf2 = os.path.join(self.temp_dir.name, "doc2.pdf")
        out_pdf = os.path.join(self.temp_dir.name, "merged.pdf")

        create_dummy_pdf(pdf1, page_count=2, text_prefix="Doc1Page")
        create_dummy_pdf(pdf2, page_count=3, text_prefix="Doc2Page")

        engine = PdfMergeEngine()
        res = engine.convert(pdf1, out_pdf, options={"input_paths": [pdf1, pdf2]})
        self.assertEqual(res, out_pdf)
        self.assertTrue(os.path.exists(out_pdf))

        # Check total page count & ordering
        merged_doc = fitz.open(out_pdf)
        self.assertEqual(len(merged_doc), 5)
        text_p1 = merged_doc[0].get_text()
        text_p3 = merged_doc[2].get_text()
        merged_doc.close()

        self.assertIn("Doc1Page 1", text_p1)
        self.assertIn("Doc2Page 1", text_p3)

    def test_pdf_merge_reject_fewer_than_two_files(self):
        pdf1 = os.path.join(self.temp_dir.name, "doc1.pdf")
        out_pdf = os.path.join(self.temp_dir.name, "merged.pdf")
        create_dummy_pdf(pdf1, page_count=1)

        engine = PdfMergeEngine()
        with self.assertRaises(ConversionError) as ctx:
            engine.convert(pdf1, out_pdf, options={"input_paths": [pdf1]})
        self.assertIn("invalid_pdf", str(ctx.exception))


class PdfSplitEngineTestCase(TestCase):
    """Unit tests for PdfSplitEngine (every_page, ranges, chunks)."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.src_pdf = os.path.join(self.temp_dir.name, "doc.pdf")
        create_dummy_pdf(self.src_pdf, page_count=5, text_prefix="SplitPage")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_split_every_page(self):
        out_zip = os.path.join(self.temp_dir.name, "split_every.zip")
        engine = PdfSplitEngine()
        res = engine.convert(self.src_pdf, out_zip, options={"split_mode": "every_page"})
        self.assertEqual(res, out_zip)

        with zipfile.ZipFile(out_zip, "r") as zf:
            names = sorted(zf.namelist())
            self.assertEqual(len(names), 5)
            self.assertEqual(names[0], "document-page-001.pdf")
            self.assertEqual(names[4], "document-page-005.pdf")

    def test_split_ranges(self):
        out_zip = os.path.join(self.temp_dir.name, "split_ranges.zip")
        engine = PdfSplitEngine()
        opts = {
            "split_mode": "ranges",
            "ranges": ["1-2", "3-5"],
        }
        res = engine.convert(self.src_pdf, out_zip, options=opts)
        self.assertEqual(res, out_zip)

        with zipfile.ZipFile(out_zip, "r") as zf:
            names = sorted(zf.namelist())
            self.assertEqual(len(names), 2)
            self.assertEqual(names[0], "document-part-001.pdf")
            self.assertEqual(names[1], "document-part-002.pdf")

    test_split_chunks = None

    def test_split_chunks_mode(self):
        out_zip = os.path.join(self.temp_dir.name, "split_chunks.zip")
        engine = PdfSplitEngine()
        opts = {
            "split_mode": "chunks",
            "pages_per_file": 2,
        }
        res = engine.convert(self.src_pdf, out_zip, options=opts)
        self.assertEqual(res, out_zip)

        with zipfile.ZipFile(out_zip, "r") as zf:
            names = sorted(zf.namelist())
            self.assertEqual(len(names), 3)  # [1,2], [3,4], [5]

    def test_split_reject_overlapping_ranges(self):
        out_zip = os.path.join(self.temp_dir.name, "split_overlap.zip")
        engine = PdfSplitEngine()
        opts = {
            "split_mode": "ranges",
            "ranges": ["1-3", "3-5"],
        }
        with self.assertRaises(ConversionError) as ctx:
            engine.convert(self.src_pdf, out_zip, options=opts)
        self.assertIn("invalid_ranges", str(ctx.exception))

    def test_split_reject_invalid_chunk_size(self):
        out_zip = os.path.join(self.temp_dir.name, "split_bad_chunk.zip")
        engine = PdfSplitEngine()
        opts = {
            "split_mode": "chunks",
            "pages_per_file": 0,
        }
        with self.assertRaises(ConversionError) as ctx:
            engine.convert(self.src_pdf, out_zip, options=opts)
        self.assertIn("invalid_chunk_size", str(ctx.exception))


class PdfExtractPagesEngineTestCase(TestCase):
    """Unit tests for PdfExtractPagesEngine."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.src_pdf = os.path.join(self.temp_dir.name, "doc.pdf")
        create_dummy_pdf(self.src_pdf, page_count=10, text_prefix="ExtractPage")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_extract_pages_success(self):
        out_pdf = os.path.join(self.temp_dir.name, "extracted.pdf")
        engine = PdfExtractPagesEngine()
        res = engine.convert(self.src_pdf, out_pdf, options={"pages": "1,3,5-7"})
        self.assertEqual(res, out_pdf)

        extracted_doc = fitz.open(out_pdf)
        self.assertEqual(len(extracted_doc), 5)  # 1, 3, 5, 6, 7
        t1 = extracted_doc[0].get_text()
        t2 = extracted_doc[1].get_text()
        extracted_doc.close()

        self.assertIn("ExtractPage 1", t1)
        self.assertIn("ExtractPage 3", t2)

    def test_extract_pages_reject_missing_pages_expr(self):
        out_pdf = os.path.join(self.temp_dir.name, "extracted.pdf")
        engine = PdfExtractPagesEngine()
        with self.assertRaises(ConversionError) as ctx:
            engine.convert(self.src_pdf, out_pdf, options={})
        self.assertIn("page_range_invalid", str(ctx.exception))


class PdfUtilitiesApiIntegrationTestCase(TestCase):
    """Integration tests for POST /api/v1/pdf/utilities/ API endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="pdfuser", password="password123")
        self.client.force_authenticate(user=self.user)
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _create_sample_pdf_bytes(self, page_count=2, text="Sample"):
        pdf_path = os.path.join(self.temp_dir.name, "sample.pdf")
        create_dummy_pdf(pdf_path, page_count=page_count, text_prefix=text)
        with open(pdf_path, "rb") as f:
            return f.read()

    def test_api_pdf_merge_success(self):
        f1_bytes = self._create_sample_pdf_bytes(2, "Merge1")
        f2_bytes = self._create_sample_pdf_bytes(3, "Merge2")

        file1 = SimpleUploadedFile("first.pdf", f1_bytes, content_type="application/pdf")
        file2 = SimpleUploadedFile("second.pdf", f2_bytes, content_type="application/pdf")

        url = "/api/v1/pdf/utilities/"
        response = self.client.post(
            url,
            {
                "operation": "pdf_merge",
                "files[]": [file1, file2],
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertIn("id", response.data)
        self.assertEqual(response.data["status"], "completed")

        job = ConversionJob.objects.get(id=response.data["id"])
        self.assertEqual(job.status, JobStatus.COMPLETED)
        self.assertTrue(os.path.exists(job.output_path))

        # Check history endpoint contains job
        hist_resp = self.client.get("/api/history/")
        self.assertEqual(hist_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(hist_resp.data["count"], 1)

    def test_api_pdf_split_every_page_success(self):
        pdf_bytes = self._create_sample_pdf_bytes(3, "SplitTest")
        file1 = SimpleUploadedFile("document.pdf", pdf_bytes, content_type="application/pdf")

        url = "/api/v1/pdf/utilities/"
        response = self.client.post(
            url,
            {
                "operation": "pdf_split",
                "file": file1,
                "split_mode": "every_page",
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["status"], "completed")

        job = ConversionJob.objects.get(id=response.data["id"])
        self.assertTrue(job.output_path.endswith(".zip"))
        self.assertTrue(os.path.exists(job.output_path))

    def test_api_pdf_extract_pages_success(self):
        pdf_bytes = self._create_sample_pdf_bytes(5, "ExtractTest")
        file1 = SimpleUploadedFile("document.pdf", pdf_bytes, content_type="application/pdf")

        url = "/api/v1/pdf/utilities/"
        response = self.client.post(
            url,
            {
                "operation": "pdf_extract_pages",
                "file": file1,
                "pages": "1-3,5",
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["status"], "completed")

        job = ConversionJob.objects.get(id=response.data["id"])
        self.assertTrue(job.output_path.endswith(".pdf"))

        extracted_doc = fitz.open(job.output_path)
        self.assertEqual(len(extracted_doc), 4)
        extracted_doc.close()

    def test_api_pdf_utilities_invalid_operation(self):
        pdf_bytes = self._create_sample_pdf_bytes(1)
        file1 = SimpleUploadedFile("document.pdf", pdf_bytes, content_type="application/pdf")

        url = "/api/v1/pdf/utilities/"
        response = self.client.post(
            url,
            {
                "operation": "pdf_rotate",
                "file": file1,
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertIn("unsupported_operation", response.data["message"])
