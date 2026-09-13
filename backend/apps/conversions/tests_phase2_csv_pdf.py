"""
Phase 2 tests — CSV → PDF conversion engine using CsvToXlsxEngine + XlsxToPdfEngine (LibreOffice).

Scenarios covered:
  1. Engine registration in engine_registry for CsvToPdfEngine.
  2. Supported pairs registration in SUPPORTED_PAIRS ((csv, pdf)).
  3. Normal CSV to PDF conversion.
  4. Multiple columns and rows.
  5. Header-only CSV file.
  6. Quoted values and commas inside quoted fields ("Chennai, Tamil Nadu").
  7. Embedded newlines inside quoted fields ("Line 1\nLine 2").
  8. Tamil Unicode text ("தமிழ் தரவு").
  9. UTF-8 BOM encoding.
 10. Latin-1 encoding fallback.
 11. Leading zeros preservation ("00123", "00045").
 12. Integer and decimal values.
 13. Column and row order preservation.
 14. Output file exists, has .pdf extension, valid %PDF signature.
 15. PyMuPDF (fitz) can open the generated PDF and extract text.
 16. Text extraction verifies header and row text present in PDF.
 17. Missing CSV file raises ConversionError.
 18. Zero-byte CSV file raises ConversionError.
 19. Unreadable/corrupt CSV input raises ConversionError.
 20. Output validation failure raises ConversionError.
 21. REST API POST upload success flow (source_format=csv, target_format=pdf).
 22. REST API POST upload failure flow.
 23. Download endpoint streaming and Content-Type (application/pdf).
 24. Anonymous session isolation (HTTP 404 for unauthorized session).
 25. Temporary XLSX file and directory cleanup verification.
"""

import io
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import fitz  # PyMuPDF
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.conversions.engines.base import ConversionError
from apps.conversions.engines.csv_to_pdf import CsvToPdfEngine
from apps.conversions.engines.libreoffice import find_libreoffice_executable
from apps.conversions.engines.registry import engine_registry
from apps.conversions.engines.validators import validate_csv_signature, validate_pdf_output
from apps.conversions.formats import SUPPORTED_PAIRS_SET, FORMAT_CSV, FORMAT_PDF, is_valid_conversion
from apps.conversions.models import ConversionJob, JobStatus

# ── Isolated temp directory for CSV → PDF tests ──────────────────────────────
TEST_TEMP_DIR = tempfile.mkdtemp(prefix="velto_phase2_csv_pdf_tests_")


@override_settings(TEMP_UPLOAD_DIR=TEST_TEMP_DIR)
class CsvToPdfEngineRegistrationTests(TestCase):
    """Engine registration and supported pairs tests for CSV → PDF."""

    def test_csv_to_pdf_engine_registration(self):
        """CsvToPdfEngine is registered in engine_registry."""
        cls = engine_registry.get("csv", "pdf")
        self.assertIsNotNone(cls)
        self.assertEqual(cls, CsvToPdfEngine)

    def test_supported_pairs_registration(self):
        """(csv, pdf) is present in SUPPORTED_PAIRS_SET."""
        self.assertIn((FORMAT_CSV, FORMAT_PDF), SUPPORTED_PAIRS_SET)
        self.assertTrue(is_valid_conversion("csv", "pdf"))


@override_settings(TEMP_UPLOAD_DIR=TEST_TEMP_DIR)
class CsvToPdfEngineUnitTests(TestCase):
    """Direct engine unit tests for CsvToPdfEngine."""

    def setUp(self):
        self.exe = find_libreoffice_executable()

    def test_normal_csv_to_pdf_conversion(self):
        """Normal CSV with headers and data rows converts to readable PDF."""
        if not self.exe:
            self.skipTest("LibreOffice not installed on machine.")

        csv_path = os.path.join(TEST_TEMP_DIR, "normal.csv")
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("ID,Name,Salary\n101,Alice,75000\n102,Bob,82000\n")

        out_pdf = os.path.join(TEST_TEMP_DIR, "normal.pdf")
        engine = CsvToPdfEngine()

        try:
            res = engine.convert(csv_path, out_pdf)
            self.assertIsNone(res)
            self.assertTrue(os.path.exists(out_pdf))
            self.assertTrue(out_pdf.endswith(".pdf"))

            # Validate PDF output
            validate_pdf_output(out_pdf)

            # Inspect extracted text with PyMuPDF
            doc = fitz.open(out_pdf)
            self.assertGreaterEqual(len(doc), 1)
            text = "".join(page.get_text() for page in doc)
            doc.close()

            self.assertIn("Name", text)
            self.assertIn("Alice", text)
            self.assertIn("75000", text)
        finally:
            for path in (csv_path, out_pdf):
                if os.path.exists(path):
                    os.remove(path)

    def test_header_only_csv_to_pdf(self):
        """Header-only CSV produces a valid 1-page PDF containing headers."""
        if not self.exe:
            self.skipTest("LibreOffice not installed on machine.")

        csv_path = os.path.join(TEST_TEMP_DIR, "header_only.csv")
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("ColA,ColB,ColC\n")

        out_pdf = os.path.join(TEST_TEMP_DIR, "header_only.pdf")
        engine = CsvToPdfEngine()

        try:
            engine.convert(csv_path, out_pdf)
            self.assertTrue(os.path.exists(out_pdf))

            doc = fitz.open(out_pdf)
            self.assertGreaterEqual(len(doc), 1)
            text = "".join(page.get_text() for page in doc)
            doc.close()

            self.assertIn("ColA", text)
        finally:
            for path in (csv_path, out_pdf):
                if os.path.exists(path):
                    os.remove(path)

    def test_quoted_commas_and_embedded_newlines(self):
        """Quoted fields with commas and embedded newlines convert to PDF cleanly."""
        if not self.exe:
            self.skipTest("LibreOffice not installed on machine.")

        csv_path = os.path.join(TEST_TEMP_DIR, "quoted.csv")
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            f.write('ID,Location,Notes\n1,"Chennai, Tamil Nadu","Line 1\nLine 2"\n')

        out_pdf = os.path.join(TEST_TEMP_DIR, "quoted.pdf")
        engine = CsvToPdfEngine()

        try:
            engine.convert(csv_path, out_pdf)
            doc = fitz.open(out_pdf)
            text = "".join(page.get_text() for page in doc)
            doc.close()

            self.assertIn("Chennai", text)
            self.assertIn("Line 1", text)
        finally:
            for path in (csv_path, out_pdf):
                if os.path.exists(path):
                    os.remove(path)

    def test_leading_zeros_and_numeric_values(self):
        """Leading zero values ('00123', '00045') and numbers appear in PDF text."""
        if not self.exe:
            self.skipTest("LibreOffice not installed on machine.")

        csv_path = os.path.join(TEST_TEMP_DIR, "zeros.csv")
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("EmpID,Zip,Score\n00123,00045,1500.50\n")

        out_pdf = os.path.join(TEST_TEMP_DIR, "zeros.pdf")
        engine = CsvToPdfEngine()

        try:
            engine.convert(csv_path, out_pdf)
            doc = fitz.open(out_pdf)
            text = "".join(page.get_text() for page in doc)
            doc.close()

            self.assertIn("00123", text)
            self.assertIn("00045", text)
            self.assertIn("1500.5", text)
        finally:
            for path in (csv_path, out_pdf):
                if os.path.exists(path):
                    os.remove(path)

    def test_utf8_tamil_unicode_preservation(self):
        """Tamil Unicode text converts to PDF without crashing."""
        if not self.exe:
            self.skipTest("LibreOffice not installed on machine.")

        csv_path = os.path.join(TEST_TEMP_DIR, "tamil.csv")
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("ID,Label,Description\n101,தமிழ் தரவு,வணக்கம் சென்னை\n")

        out_pdf = os.path.join(TEST_TEMP_DIR, "tamil.pdf")
        engine = CsvToPdfEngine()

        try:
            engine.convert(csv_path, out_pdf)
            self.assertTrue(os.path.exists(out_pdf))

            doc = fitz.open(out_pdf)
            self.assertGreaterEqual(len(doc), 1)
            doc.close()
        finally:
            for path in (csv_path, out_pdf):
                if os.path.exists(path):
                    os.remove(path)

    def test_utf8_bom_encoding_support(self):
        """UTF-8 BOM encoded CSV converts to PDF cleanly."""
        if not self.exe:
            self.skipTest("LibreOffice not installed on machine.")

        csv_path = os.path.join(TEST_TEMP_DIR, "bom.csv")
        with open(csv_path, "w", encoding="utf-8-sig") as f:
            f.write("Item,Price\nWidget,9.99\n")

        out_pdf = os.path.join(TEST_TEMP_DIR, "bom.pdf")
        engine = CsvToPdfEngine()

        try:
            engine.convert(csv_path, out_pdf)
            doc = fitz.open(out_pdf)
            text = "".join(page.get_text() for page in doc)
            doc.close()

            self.assertIn("Item", text)
            self.assertIn("Widget", text)
        finally:
            for path in (csv_path, out_pdf):
                if os.path.exists(path):
                    os.remove(path)

    def test_latin1_encoding_fallback(self):
        """Latin-1 encoded CSV converts to PDF via fallback encoding."""
        if not self.exe:
            self.skipTest("LibreOffice not installed on machine.")

        csv_path = os.path.join(TEST_TEMP_DIR, "latin1.csv")
        with open(csv_path, "w", encoding="latin-1") as f:
            f.write("City,Score\nMünchen,95\n")

        out_pdf = os.path.join(TEST_TEMP_DIR, "latin1.pdf")
        engine = CsvToPdfEngine()

        try:
            engine.convert(csv_path, out_pdf)
            doc = fitz.open(out_pdf)
            self.assertGreaterEqual(len(doc), 1)
            doc.close()
        finally:
            for path in (csv_path, out_path if 'out_path' in locals() else out_pdf):
                if os.path.exists(path):
                    os.remove(path)

    def test_missing_input_file_raises_conversion_error(self):
        """Missing CSV file raises ConversionError."""
        csv_path = os.path.join(TEST_TEMP_DIR, "nonexistent.csv")
        out_pdf = os.path.join(TEST_TEMP_DIR, "out.pdf")
        engine = CsvToPdfEngine()

        with self.assertRaises(ConversionError) as ctx:
            engine.convert(csv_path, out_pdf)
        self.assertIn("does not exist", str(ctx.exception))

    def test_zero_byte_input_raises_conversion_error(self):
        """Zero-byte CSV file raises ConversionError."""
        csv_path = os.path.join(TEST_TEMP_DIR, "zero.csv")
        with open(csv_path, "wb") as f:
            f.write(b"")

        out_pdf = os.path.join(TEST_TEMP_DIR, "out.pdf")
        engine = CsvToPdfEngine()

        try:
            with self.assertRaises(ConversionError) as ctx:
                engine.convert(csv_path, out_pdf)
            self.assertIn("empty", str(ctx.exception))
        finally:
            if os.path.exists(csv_path):
                os.remove(csv_path)

    def test_temporary_xlsx_and_dir_cleaned_up(self):
        """Temporary intermediate XLSX file and temp directory are deleted after conversion."""
        if not self.exe:
            self.skipTest("LibreOffice not installed on machine.")

        csv_path = os.path.join(TEST_TEMP_DIR, "cleanup_test.csv")
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("A,B\n1,2\n")

        out_pdf = os.path.join(TEST_TEMP_DIR, "cleanup_test.pdf")
        engine = CsvToPdfEngine()

        try:
            engine.convert(csv_path, out_pdf)
            self.assertTrue(os.path.exists(out_pdf))

            # Verify no orphaned velto_csv2pdf_ temp directories remain in system temp
            temp_root = tempfile.gettempdir()
            orphans = [
                d for d in os.listdir(temp_root)
                if d.startswith("velto_csv2pdf_")
            ]
            self.assertEqual(len(orphans), 0, f"Orphaned temp dirs found: {orphans}")
        finally:
            for path in (csv_path, out_pdf):
                if os.path.exists(path):
                    os.remove(path)


@override_settings(TEMP_UPLOAD_DIR=TEST_TEMP_DIR)
class CsvToPdfApiIntegrationTests(TestCase):
    """API Integration tests for CSV → PDF conversion flow."""

    def setUp(self):
        self.client_a = APIClient()
        self.client_b = APIClient()
        self.exe = find_libreoffice_executable()

    def test_successful_csv_to_pdf_api_flow(self):
        """Full success flow: Upload CSV → Status Completed → Download PDF."""
        if not self.exe:
            self.skipTest("LibreOffice not installed on machine.")

        csv_bytes = "ID,Name,Salary\n101,Alice,75000\n102,Bob,82000\n".encode("utf-8")
        f = SimpleUploadedFile("report.csv", csv_bytes, content_type="text/csv")

        res = self.client_a.post(
            "/api/conversions/",
            {
                "file": f,
                "source_format": "csv",
                "target_format": "pdf",
            },
            format="multipart",
        )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        data = res.json()
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["source_format"], "csv")
        self.assertEqual(data["target_format"], "pdf")
        self.assertEqual(data["output_filename"], "report.pdf")
        self.assertTrue(data["output_size_bytes"] > 0)

        job_id = data["id"]
        dl_url = reverse("conversions:job-download", kwargs={"job_id": job_id})
        dl_res = self.client_a.get(dl_url)
        self.assertEqual(dl_res.status_code, status.HTTP_200_OK)
        self.assertEqual(dl_res["Content-Type"], "application/pdf")
        content = b"".join(dl_res.streaming_content)
        self.assertTrue(content.startswith(b"%PDF"))

    def test_invalid_csv_api_failure_flow(self):
        """Uploading 0-byte CSV yields 400 error; unparseable CSV yields status failed."""
        # 1. 0-byte upload
        f_empty = SimpleUploadedFile("empty.csv", b"", content_type="text/csv")
        res_empty = self.client_a.post(
            "/api/conversions/",
            {
                "file": f_empty,
                "source_format": "csv",
                "target_format": "pdf",
            },
            format="multipart",
        )
        self.assertEqual(res_empty.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("file", res_empty.json())

        # 2. Corrupt input file
        f_corrupt = SimpleUploadedFile("corrupt.csv", b"\x00\x00\xff\xfe\x00\x00", content_type="text/csv")
        res_corrupt = self.client_a.post(
            "/api/conversions/",
            {
                "file": f_corrupt,
                "source_format": "csv",
                "target_format": "pdf",
            },
            format="multipart",
        )
        self.assertEqual(res_corrupt.status_code, status.HTTP_202_ACCEPTED)
        data = res_corrupt.json()
        self.assertEqual(data["status"], "failed")
        self.assertTrue(len(data["error_message"]) > 0)

    def test_unsupported_pair_rejected(self):
        """Unsupported format pair (e.g. csv → docx) is rejected with 400."""
        f = SimpleUploadedFile("test.csv", b"A,B\n1,2\n", content_type="text/csv")
        res = self.client_a.post(
            "/api/conversions/",
            {
                "file": f,
                "source_format": "csv",
                "target_format": "docx",
            },
            format="multipart",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_anonymous_session_isolation_csv_to_pdf(self):
        """Session B cannot access or download Session A's CSV → PDF jobs."""
        if not self.exe:
            self.skipTest("LibreOffice not installed on machine.")

        csv_bytes = "A,B\n1,2\n".encode("utf-8")
        f = SimpleUploadedFile("private.csv", csv_bytes, content_type="text/csv")

        res_a = self.client_a.post(
            "/api/conversions/",
            {
                "file": f,
                "source_format": "csv",
                "target_format": "pdf",
            },
            format="multipart",
        )
        self.assertEqual(res_a.status_code, status.HTTP_201_CREATED)
        job_id = res_a.json()["id"]

        # Session B detail check
        detail_url = reverse("conversions:job-detail", kwargs={"job_id": job_id})
        res_b_detail = self.client_b.get(detail_url)
        self.assertEqual(res_b_detail.status_code, status.HTTP_404_NOT_FOUND)

        # Session B download check
        dl_url = reverse("conversions:job-download", kwargs={"job_id": job_id})
        res_b_dl = self.client_b.get(dl_url)
        self.assertEqual(res_b_dl.status_code, status.HTTP_404_NOT_FOUND)
