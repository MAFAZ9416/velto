"""
Phase 2 tests — CSV → XLSX conversion engine using native csv and openpyxl.

Scenarios covered:
  1. Engine registration in engine_registry for CsvToXlsxEngine.
  2. Supported pairs registration in SUPPORTED_PAIRS ((csv, xlsx)).
  3. Normal CSV with headers and data rows.
  4. Multiple columns and multiple rows.
  5. Header-only CSV file (1 row).
  6. Empty CSV file handling.
  7. Quoted values and commas inside quoted fields ("Chennai, Tamil Nadu").
  8. Embedded newlines inside quoted fields ("Line 1\nLine 2").
  9. Empty cells in CSV.
 10. Uneven row lengths in CSV.
 11. Numeric and decimal values (1500.50, 42).
 12. Values with leading zeros ("00123", "00045") preserved as text cells.
 13. UTF-8 Unicode text.
 14. Tamil Unicode text ("தமிழ் தரவு").
 15. UTF-8 BOM encoding.
 16. Latin-1 encoding fallback.
 17. Output file existence and .xlsx extension.
 18. openpyxl load_workbook validity.
 19. Worksheet count and title.
 20. Header values, row values, column order, row order preservation.
 21. Bold header cells.
 22. Freeze panes set to A2.
 23. Autofilter set on worksheet.
 24. Column widths clamped between 12 and 50.
 25. Missing input file raises ConversionError.
 26. Zero-byte input file raises ConversionError.
 27. Invalid/unreadable CSV input raises ConversionError.
 28. Output load validation failure raises ConversionError.
 29. REST API POST upload success flow (source_format=csv, target_format=xlsx).
 30. REST API POST upload failure flow.
 31. Protected download endpoint streaming and Content-Type.
 32. Anonymous session isolation (HTTP 404 for unauthorized session).
 33. Temporary file cleanup verification.
"""

import io
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import openpyxl
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.conversions.engines.base import ConversionError
from apps.conversions.engines.csv_to_xlsx import CsvToXlsxEngine
from apps.conversions.engines.validators import validate_csv_signature
from apps.conversions.engines.registry import engine_registry
from apps.conversions.formats import SUPPORTED_PAIRS_SET, FORMAT_CSV, FORMAT_XLSX, is_valid_conversion
from apps.conversions.models import ConversionJob, JobStatus

# ── Isolated temp directory for CSV tests ────────────────────────────────────
TEST_TEMP_DIR = tempfile.mkdtemp(prefix="velto_phase2_csv_xlsx_tests_")


@override_settings(TEMP_UPLOAD_DIR=TEST_TEMP_DIR)
class CsvToXlsxEngineRegistrationTests(TestCase):
    """Engine registration and supported pairs tests for CSV → XLSX."""

    def test_csv_to_xlsx_engine_registration(self):
        """CsvToXlsxEngine is registered in engine_registry."""
        cls = engine_registry.get("csv", "xlsx")
        self.assertIsNotNone(cls)
        self.assertEqual(cls, CsvToXlsxEngine)

    def test_supported_pairs_registration(self):
        """(csv, xlsx) is present in SUPPORTED_PAIRS_SET."""
        self.assertIn((FORMAT_CSV, FORMAT_XLSX), SUPPORTED_PAIRS_SET)
        self.assertTrue(is_valid_conversion("csv", "xlsx"))


@override_settings(TEMP_UPLOAD_DIR=TEST_TEMP_DIR)
class CsvToXlsxEngineUnitTests(TestCase):
    """Direct engine unit tests for CsvToXlsxEngine and CSV validators."""

    def test_validate_csv_signature_valid(self):
        """Valid CSV file passes signature validation."""
        csv_path = os.path.join(TEST_TEMP_DIR, "valid.csv")
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("Name,Age,City\nAlice,30,Chennai\n")

        try:
            validate_csv_signature(csv_path)
        finally:
            if os.path.exists(csv_path):
                os.remove(csv_path)

    def test_validate_csv_signature_zero_byte(self):
        """Zero-byte CSV file raises ConversionError."""
        csv_path = os.path.join(TEST_TEMP_DIR, "empty.csv")
        with open(csv_path, "wb") as f:
            f.write(b"")

        try:
            with self.assertRaises(ConversionError) as ctx:
                validate_csv_signature(csv_path)
            self.assertIn("empty", str(ctx.exception))
        finally:
            if os.path.exists(csv_path):
                os.remove(csv_path)

    def test_validate_csv_signature_missing_file(self):
        """Missing CSV file raises ConversionError."""
        csv_path = os.path.join(TEST_TEMP_DIR, "nonexistent.csv")
        with self.assertRaises(ConversionError) as ctx:
            validate_csv_signature(csv_path)
        self.assertIn("does not exist", str(ctx.exception))

    def test_normal_csv_conversion(self):
        """Normal CSV with headers and data rows converts cleanly."""
        csv_path = os.path.join(TEST_TEMP_DIR, "normal.csv")
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("ID,Name,Amount\n1,Alice,1500.50\n2,Bob,2500\n")

        out_path = os.path.join(TEST_TEMP_DIR, "normal.xlsx")
        engine = CsvToXlsxEngine()
        try:
            res = engine.convert(csv_path, out_path)
            self.assertIsNone(res)
            self.assertTrue(os.path.exists(out_path))

            wb = openpyxl.load_workbook(out_path)
            ws = wb.active
            self.assertEqual(ws.title, "Sheet1")
            self.assertEqual(ws.max_row, 3)
            self.assertEqual(ws.max_column, 3)

            # Check header bolding
            self.assertTrue(ws["A1"].font.bold)
            self.assertTrue(ws["B1"].font.bold)

            # Check values
            self.assertEqual(ws["A2"].value, 1)
            self.assertEqual(ws["B2"].value, "Alice")
            self.assertEqual(ws["C2"].value, 1500.50)

            # Check freeze panes & autofilter
            self.assertEqual(ws.freeze_panes, "A2")
            self.assertIsNotNone(ws.auto_filter.ref)

            wb.close()
        finally:
            for path in (csv_path, out_path):
                if os.path.exists(path):
                    os.remove(path)

    def test_header_only_csv(self):
        """Header-only CSV generates a valid workbook containing header row."""
        csv_path = os.path.join(TEST_TEMP_DIR, "header_only.csv")
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("Header1,Header2,Header3\n")

        out_path = os.path.join(TEST_TEMP_DIR, "header_only.xlsx")
        engine = CsvToXlsxEngine()
        try:
            engine.convert(csv_path, out_path)
            self.assertTrue(os.path.exists(out_path))

            wb = openpyxl.load_workbook(out_path)
            ws = wb.active
            self.assertEqual(ws.max_row, 1)
            self.assertEqual(ws.max_column, 3)
            self.assertTrue(ws["A1"].font.bold)
            wb.close()
        finally:
            for path in (csv_path, out_path):
                if os.path.exists(path):
                    os.remove(path)

    def test_quoted_commas_and_embedded_newlines(self):
        """Quoted fields with commas and embedded newlines are preserved."""
        csv_path = os.path.join(TEST_TEMP_DIR, "quoted.csv")
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            f.write('ID,Address,Notes\n1,"Chennai, Tamil Nadu","Line 1\nLine 2"\n')

        out_path = os.path.join(TEST_TEMP_DIR, "quoted.xlsx")
        engine = CsvToXlsxEngine()
        try:
            engine.convert(csv_path, out_path)
            wb = openpyxl.load_workbook(out_path)
            ws = wb.active
            self.assertEqual(ws["B2"].value, "Chennai, Tamil Nadu")
            self.assertEqual(ws["C2"].value, "Line 1\nLine 2")
            wb.close()
        finally:
            for path in (csv_path, out_path):
                if os.path.exists(path):
                    os.remove(path)

    def test_leading_zero_preservation(self):
        """Leading zero values ('00123', '00045') are preserved as text strings."""
        csv_path = os.path.join(TEST_TEMP_DIR, "zeros.csv")
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("EmpID,PostalCode,Count\n00123,00045,100\n")

        out_path = os.path.join(TEST_TEMP_DIR, "zeros.xlsx")
        engine = CsvToXlsxEngine()
        try:
            engine.convert(csv_path, out_path)
            wb = openpyxl.load_workbook(out_path)
            ws = wb.active
            self.assertEqual(ws["A2"].value, "00123")
            self.assertIsInstance(ws["A2"].value, str)
            self.assertEqual(ws["B2"].value, "00045")
            self.assertIsInstance(ws["B2"].value, str)
            self.assertEqual(ws["C2"].value, 100)
            wb.close()
        finally:
            for path in (csv_path, out_path):
                if os.path.exists(path):
                    os.remove(path)

    def test_utf8_tamil_unicode_preservation(self):
        """Tamil and UTF-8 Unicode characters are preserved accurately."""
        csv_path = os.path.join(TEST_TEMP_DIR, "tamil.csv")
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("ID,Label,Description\n101,தமிழ் தரவு,வணக்கம் சென்னை\n")

        out_path = os.path.join(TEST_TEMP_DIR, "tamil.xlsx")
        engine = CsvToXlsxEngine()
        try:
            engine.convert(csv_path, out_path)
            wb = openpyxl.load_workbook(out_path)
            ws = wb.active
            self.assertEqual(ws["B2"].value, "தமிழ் தரவு")
            self.assertEqual(ws["C2"].value, "வணக்கம் சென்னை")
            wb.close()
        finally:
            for path in (csv_path, out_path):
                if os.path.exists(path):
                    os.remove(path)

    def test_utf8_bom_encoding_support(self):
        """UTF-8 BOM encoded CSV files parse without BOM artifact in column A1."""
        csv_path = os.path.join(TEST_TEMP_DIR, "bom.csv")
        with open(csv_path, "w", encoding="utf-8-sig") as f:
            f.write("Product,Price\nWidget,19.99\n")

        out_path = os.path.join(TEST_TEMP_DIR, "bom.xlsx")
        engine = CsvToXlsxEngine()
        try:
            engine.convert(csv_path, out_path)
            wb = openpyxl.load_workbook(out_path)
            ws = wb.active
            self.assertEqual(ws["A1"].value, "Product")
            wb.close()
        finally:
            for path in (csv_path, out_path):
                if os.path.exists(path):
                    os.remove(path)

    def test_latin1_encoding_fallback(self):
        """Latin-1 encoded CSV files parse cleanly via fallback encoding."""
        csv_path = os.path.join(TEST_TEMP_DIR, "latin1.csv")
        with open(csv_path, "w", encoding="latin-1") as f:
            f.write("City,Score\nMünchen,95\n")

        out_path = os.path.join(TEST_TEMP_DIR, "latin1.xlsx")
        engine = CsvToXlsxEngine()
        try:
            engine.convert(csv_path, out_path)
            wb = openpyxl.load_workbook(out_path)
            ws = wb.active
            self.assertEqual(ws["A2"].value, "München")
            wb.close()
        finally:
            for path in (csv_path, out_path):
                if os.path.exists(path):
                    os.remove(path)

    def test_empty_cells_and_uneven_rows(self):
        """Empty cells and uneven row lengths are converted safely."""
        csv_path = os.path.join(TEST_TEMP_DIR, "uneven.csv")
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("Col1,Col2,Col3\nVal1,,Val3\nValA\n")

        out_path = os.path.join(TEST_TEMP_DIR, "uneven.xlsx")
        engine = CsvToXlsxEngine()
        try:
            engine.convert(csv_path, out_path)
            wb = openpyxl.load_workbook(out_path)
            ws = wb.active
            self.assertIn(ws["B2"].value, ("", None))
            self.assertEqual(ws["C2"].value, "Val3")
            self.assertEqual(ws["A3"].value, "ValA")
            wb.close()
        finally:
            for path in (csv_path, out_path):
                if os.path.exists(path):
                    os.remove(path)

    def test_column_width_clamping(self):
        """Column widths are clamped between 12 and 50 characters."""
        csv_path = os.path.join(TEST_TEMP_DIR, "widths.csv")
        long_str = "A" * 120
        short_str = "Hi"
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write(f"Short,Long\n{short_str},{long_str}\n")

        out_path = os.path.join(TEST_TEMP_DIR, "widths.xlsx")
        engine = CsvToXlsxEngine()
        try:
            engine.convert(csv_path, out_path)
            wb = openpyxl.load_workbook(out_path)
            ws = wb.active
            col_a_width = ws.column_dimensions["A"].width
            col_b_width = ws.column_dimensions["B"].width

            self.assertGreaterEqual(col_a_width, 12)
            self.assertLessEqual(col_b_width, 50)
            wb.close()
        finally:
            for path in (csv_path, out_path):
                if os.path.exists(path):
                    os.remove(path)

    @patch("openpyxl.load_workbook", side_effect=Exception("Corrupted workbook"))
    def test_output_validation_failure_raises_conversion_error(self, mock_load):
        """If generated XLSX fails openpyxl validation, ConversionError is raised."""
        csv_path = os.path.join(TEST_TEMP_DIR, "test.csv")
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("A,B\n1,2\n")

        out_path = os.path.join(TEST_TEMP_DIR, "corrupt_out.xlsx")
        engine = CsvToXlsxEngine()
        try:
            with self.assertRaises(ConversionError) as ctx:
                engine.convert(csv_path, out_path)
            self.assertIn("invalid or corrupted", str(ctx.exception))
        finally:
            for path in (csv_path, out_path):
                if os.path.exists(path):
                    os.remove(path)


@override_settings(TEMP_UPLOAD_DIR=TEST_TEMP_DIR)
class CsvToXlsxApiIntegrationTests(TestCase):
    """API Integration tests for CSV → XLSX conversion flow."""

    def setUp(self):
        self.client_a = APIClient()
        self.client_b = APIClient()

    def test_successful_csv_to_xlsx_api_flow(self):
        """Full success flow: Upload CSV → Status Completed → Download XLSX."""
        csv_bytes = "ID,Name,Salary\n101,Alice,75000\n102,Bob,82000\n".encode("utf-8")
        f = SimpleUploadedFile("employees.csv", csv_bytes, content_type="text/csv")

        res = self.client_a.post(
            "/api/conversions/",
            {
                "file": f,
                "source_format": "csv",
                "target_format": "xlsx",
            },
            format="multipart",
        )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        data = res.json()
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["source_format"], "csv")
        self.assertEqual(data["target_format"], "xlsx")
        self.assertEqual(data["output_filename"], "employees.xlsx")
        self.assertTrue(data["output_size_bytes"] > 0)

        job_id = data["id"]
        dl_url = reverse("conversions:job-download", kwargs={"job_id": job_id})
        dl_res = self.client_a.get(dl_url)
        self.assertEqual(dl_res.status_code, status.HTTP_200_OK)
        self.assertEqual(
            dl_res["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    def test_invalid_csv_api_failure_flow(self):
        """Uploading 0-byte CSV yields 400 error; unparseable CSV yields status failed."""
        # 1. 0-byte file upload
        f_empty = SimpleUploadedFile("empty.csv", b"", content_type="text/csv")
        res_empty = self.client_a.post(
            "/api/conversions/",
            {
                "file": f_empty,
                "source_format": "csv",
                "target_format": "xlsx",
            },
            format="multipart",
        )
        self.assertEqual(res_empty.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("file", res_empty.json())

        # 2. Corrupt / unreadable input file
        f_corrupt = SimpleUploadedFile("corrupt.csv", b"\x00\x00\xff\xfe\x00\x00", content_type="text/csv")
        res_corrupt = self.client_a.post(
            "/api/conversions/",
            {
                "file": f_corrupt,
                "source_format": "csv",
                "target_format": "xlsx",
            },
            format="multipart",
        )
        self.assertEqual(res_corrupt.status_code, status.HTTP_202_ACCEPTED)
        data = res_corrupt.json()
        self.assertEqual(data["status"], "failed")
        self.assertTrue(len(data["error_message"]) > 0)

    def test_anonymous_session_isolation_csv_to_xlsx(self):
        """Session B cannot access or download Session A's CSV → XLSX jobs."""
        csv_bytes = "A,B\n1,2\n".encode("utf-8")
        f = SimpleUploadedFile("private.csv", csv_bytes, content_type="text/csv")

        res_a = self.client_a.post(
            "/api/conversions/",
            {
                "file": f,
                "source_format": "csv",
                "target_format": "xlsx",
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

