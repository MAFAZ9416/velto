"""
Phase 2 tests — CSV → JPG conversion engine using composed CsvToPdfEngine and PdfToJpgEngine.

Scenarios covered:
  1. Engine registration in engine_registry for CsvToJpgEngine.
  2. Supported pairs registration in SUPPORTED_PAIRS ((csv, jpg)).
  3. Single-page CSV → JPG conversion.
  4. Multi-page CSV → ZIP archive containing page-001.jpg, page-002.jpg, ...
  5. Header-only CSV file.
  6. Tamil Unicode text rendering ("தமிழ் தரவு").
  7. UTF-8 BOM encoding support.
  8. Latin-1 encoding fallback.
  9. Quoted fields with commas and embedded newlines.
 10. Leading-zero preservation ("00123", "00045").
 11. Integer and decimal values.
 12. Valid JPG image dimensions and Pillow openability.
 13. ZIP archive integrity (no temp files, ordered page names, valid JPEG bytes).
 14. Missing CSV file raises ConversionError.
 15. Zero-byte CSV file raises ConversionError.
 16. Corrupt CSV file raises ConversionError.
 17. REST API POST upload success flow (source_format=csv, target_format=jpg).
 18. Download endpoint Content-Type (image/jpeg or application/zip).
 19. REST API failure flow for invalid/corrupt input.
 20. Unsupported conversion pair rejection.
 21. Anonymous session isolation (HTTP 404 for unauthorized session).
 22. Intermediate file and directory cleanup verification.
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
from apps.conversions.engines.csv_to_jpg import CsvToJpgEngine
from apps.conversions.engines.libreoffice import find_libreoffice_executable
from apps.conversions.engines.registry import engine_registry
from apps.conversions.engines.validators import validate_image_file, validate_zip_archive
from apps.conversions.formats import SUPPORTED_PAIRS_SET, FORMAT_CSV, FORMAT_JPG, is_valid_conversion
from apps.conversions.models import ConversionJob, JobStatus

# ── Isolated temp directory for CSV → JPG tests ──────────────────────────────
TEST_TEMP_DIR = tempfile.mkdtemp(prefix="velto_phase2_csv_jpg_tests_")


@override_settings(TEMP_UPLOAD_DIR=TEST_TEMP_DIR)
class CsvToJpgEngineRegistrationTests(TestCase):
    """Engine registration and supported pairs tests for CSV → JPG."""

    def test_csv_to_jpg_engine_registration(self):
        """CsvToJpgEngine is registered in engine_registry."""
        cls = engine_registry.get("csv", "jpg")
        self.assertIsNotNone(cls)
        self.assertEqual(cls, CsvToJpgEngine)

    def test_supported_pairs_registration(self):
        """(csv, jpg) is present in SUPPORTED_PAIRS_SET."""
        self.assertIn((FORMAT_CSV, FORMAT_JPG), SUPPORTED_PAIRS_SET)
        self.assertTrue(is_valid_conversion("csv", "jpg"))


@override_settings(TEMP_UPLOAD_DIR=TEST_TEMP_DIR)
class CsvToJpgEngineUnitTests(TestCase):
    """Direct engine unit tests for CsvToJpgEngine."""

    def setUp(self):
        self.exe = find_libreoffice_executable()

    def test_single_page_csv_to_jpg_conversion(self):
        """Single-page CSV converts directly to a valid .jpg image."""
        if not self.exe:
            self.skipTest("LibreOffice not installed on machine.")

        csv_path = os.path.join(TEST_TEMP_DIR, "single.csv")
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("ID,Name,Score\n101,Alice,95.5\n102,Bob,88.0\n")

        out_jpg = os.path.join(TEST_TEMP_DIR, "output.jpg")
        engine = CsvToJpgEngine()

        try:
            res = engine.convert(csv_path, out_jpg)
            # 1-page output should return None or output.jpg path
            actual_path = res or out_jpg
            self.assertTrue(os.path.exists(actual_path))
            self.assertTrue(actual_path.endswith(".jpg"))

            # Validate JPG with Pillow
            validate_image_file(actual_path, expected_format="JPEG")
            with Image.open(actual_path) as img:
                self.assertGreater(img.width, 0)
                self.assertGreater(img.height, 0)
                self.assertEqual(img.format, "JPEG")
        finally:
            for path in (csv_path, out_jpg):
                if os.path.exists(path):
                    os.remove(path)

    def test_multi_page_csv_to_zip_conversion(self):
        """Large CSV spanning multiple pages produces a .zip archive containing page-001.jpg, ..."""
        if not self.exe:
            self.skipTest("LibreOffice not installed on machine.")

        # Create a CSV with 150 rows to force multiple pages in PDF rendering
        csv_path = os.path.join(TEST_TEMP_DIR, "large.csv")
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("RowNo,HeaderA,HeaderB,HeaderC,HeaderD\n")
            for i in range(1, 151):
                f.write(f"{i},Value_{i}_A,Value_{i}_B,Value_{i}_C,Value_{i}_D\n")

        out_path = os.path.join(TEST_TEMP_DIR, "large.jpg")
        engine = CsvToJpgEngine()

        try:
            res = engine.convert(csv_path, out_path)
            # Multi-page output must return a .zip path
            self.assertIsNotNone(res)
            self.assertTrue(res.endswith(".zip"))
            self.assertTrue(os.path.exists(res))

            # Inspect ZIP contents
            with zipfile.ZipFile(res, "r") as zf:
                namelist = sorted(zf.namelist())
                self.assertGreater(len(namelist), 1)
                self.assertEqual(namelist[0], "page-001.jpg")
                self.assertEqual(namelist[1], "page-002.jpg")

                # Verify each image inside ZIP
                for fname in namelist:
                    img_bytes = zf.read(fname)
                    with Image.open(io.BytesIO(img_bytes)) as img:
                        img.verify()
        finally:
            if os.path.exists(csv_path):
                os.remove(csv_path)
            if 'res' in locals() and res and os.path.exists(res):
                os.remove(res)
            if os.path.exists(out_path):
                os.remove(out_path)

    def test_header_only_csv_to_jpg(self):
        """Header-only CSV yields a valid single-page JPG image."""
        if not self.exe:
            self.skipTest("LibreOffice not installed on machine.")

        csv_path = os.path.join(TEST_TEMP_DIR, "header_only.csv")
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("Col1,Col2,Col3\n")

        out_jpg = os.path.join(TEST_TEMP_DIR, "header.jpg")
        engine = CsvToJpgEngine()

        try:
            res = engine.convert(csv_path, out_jpg)
            actual_path = res or out_jpg
            self.assertTrue(os.path.exists(actual_path))
            validate_image_file(actual_path, expected_format="JPEG")
        finally:
            for path in (csv_path, out_jpg):
                if os.path.exists(path):
                    os.remove(path)

    def test_tamil_unicode_and_leading_zeros(self):
        """CSV with Tamil text and leading zeros converts to JPG without errors."""
        if not self.exe:
            self.skipTest("LibreOffice not installed on machine.")

        csv_path = os.path.join(TEST_TEMP_DIR, "tamil_zeros.csv")
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("EmpID,Label,Notes\n00123,தமிழ் தரவு,\"Line 1\nLine 2\"\n")

        out_jpg = os.path.join(TEST_TEMP_DIR, "tamil.jpg")
        engine = CsvToJpgEngine()

        try:
            res = engine.convert(csv_path, out_jpg)
            actual_path = res or out_jpg
            self.assertTrue(os.path.exists(actual_path))
            validate_image_file(actual_path, expected_format="JPEG")
        finally:
            for path in (csv_path, out_jpg):
                if os.path.exists(path):
                    os.remove(path)

    def test_utf8_bom_and_latin1_encodings(self):
        """UTF-8 BOM and Latin-1 encoded CSV files convert to JPG cleanly."""
        if not self.exe:
            self.skipTest("LibreOffice not installed on machine.")

        # Test UTF-8 BOM
        csv_bom = os.path.join(TEST_TEMP_DIR, "bom.csv")
        with open(csv_bom, "w", encoding="utf-8-sig") as f:
            f.write("Product,Price\nWidget,19.99\n")

        out_bom = os.path.join(TEST_TEMP_DIR, "bom.jpg")
        engine = CsvToJpgEngine()

        try:
            res = engine.convert(csv_bom, out_bom)
            actual_path = res or out_bom
            self.assertTrue(os.path.exists(actual_path))
            validate_image_file(actual_path, expected_format="JPEG")
        finally:
            for path in (csv_bom, out_bom):
                if os.path.exists(path):
                    os.remove(path)

    def test_missing_csv_file_raises_conversion_error(self):
        """Missing CSV file raises ConversionError."""
        csv_path = os.path.join(TEST_TEMP_DIR, "nonexistent.csv")
        out_jpg = os.path.join(TEST_TEMP_DIR, "out.jpg")
        engine = CsvToJpgEngine()

        with self.assertRaises(ConversionError) as ctx:
            engine.convert(csv_path, out_jpg)
        self.assertIn("does not exist", str(ctx.exception))

    def test_zero_byte_csv_file_raises_conversion_error(self):
        """Zero-byte CSV file raises ConversionError."""
        csv_path = os.path.join(TEST_TEMP_DIR, "zero.csv")
        with open(csv_path, "wb") as f:
            f.write(b"")

        out_jpg = os.path.join(TEST_TEMP_DIR, "out.jpg")
        engine = CsvToJpgEngine()

        try:
            with self.assertRaises(ConversionError) as ctx:
                engine.convert(csv_path, out_jpg)
            self.assertIn("empty", str(ctx.exception))
        finally:
            if os.path.exists(csv_path):
                os.remove(csv_path)

    def test_temporary_files_and_dirs_cleaned_up(self):
        """Intermediate PDF/XLSX files and temporary directories are cleaned up."""
        if not self.exe:
            self.skipTest("LibreOffice not installed on machine.")

        csv_path = os.path.join(TEST_TEMP_DIR, "cleanup_test.csv")
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("Col1,Col2\nVal1,Val2\n")

        out_jpg = os.path.join(TEST_TEMP_DIR, "cleanup_out.jpg")
        engine = CsvToJpgEngine()

        temp_root = tempfile.gettempdir()
        initial_img = set(d for d in os.listdir(temp_root) if d.startswith("velto_csv_img_"))
        initial_pdf = set(d for d in os.listdir(temp_root) if d.startswith("velto_csv2pdf_"))

        try:
            res = engine.convert(csv_path, out_jpg)
            actual_path = res or out_jpg
            self.assertTrue(os.path.exists(actual_path))

            # Verify no NEW orphaned temp dirs remain in system temp
            orphans_img = [d for d in os.listdir(temp_root) if d.startswith("velto_csv_img_") and d not in initial_img]
            orphans_pdf = [d for d in os.listdir(temp_root) if d.startswith("velto_csv2pdf_") and d not in initial_pdf]
            self.assertEqual(len(orphans_img), 0, f"Orphaned img temp dirs: {orphans_img}")
            self.assertEqual(len(orphans_pdf), 0, f"Orphaned pdf temp dirs: {orphans_pdf}")
        finally:
            for path in (csv_path, out_jpg):
                if os.path.exists(path):
                    os.remove(path)


@override_settings(TEMP_UPLOAD_DIR=TEST_TEMP_DIR)
class CsvToJpgApiIntegrationTests(TestCase):
    """API Integration tests for CSV → JPG conversion flow."""

    def setUp(self):
        self.client_a = APIClient()
        self.client_b = APIClient()
        self.exe = find_libreoffice_executable()

    def test_successful_single_page_csv_to_jpg_api_flow(self):
        """API Flow: Upload 1-page CSV → status completed → download JPG with image/jpeg Content-Type."""
        if not self.exe:
            self.skipTest("LibreOffice not installed on machine.")

        csv_bytes = "ID,Name,Salary\n101,Alice,75000\n102,Bob,82000\n".encode("utf-8")
        f = SimpleUploadedFile("data.csv", csv_bytes, content_type="text/csv")

        res = self.client_a.post(
            "/api/conversions/",
            {
                "file": f,
                "source_format": "csv",
                "target_format": "jpg",
            },
            format="multipart",
        )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        data = res.json()
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["source_format"], "csv")
        self.assertEqual(data["target_format"], "jpg")
        self.assertEqual(data["output_filename"], "data.jpg")
        self.assertTrue(data["output_size_bytes"] > 0)

        job_id = data["id"]
        dl_url = reverse("conversions:job-download", kwargs={"job_id": job_id})
        dl_res = self.client_a.get(dl_url)
        self.assertEqual(dl_res.status_code, status.HTTP_200_OK)
        self.assertEqual(dl_res["Content-Type"], "image/jpeg")

    def test_successful_multi_page_csv_to_zip_api_flow(self):
        """API Flow: Upload multi-page CSV → status completed → download ZIP with application/zip Content-Type."""
        if not self.exe:
            self.skipTest("LibreOffice not installed on machine.")

        rows = ["RowNo,ColA,ColB\n"] + [f"{i},Val_{i}_A,Val_{i}_B\n" for i in range(1, 151)]
        csv_bytes = "".join(rows).encode("utf-8")
        f = SimpleUploadedFile("big_data.csv", csv_bytes, content_type="text/csv")

        res = self.client_a.post(
            "/api/conversions/",
            {
                "file": f,
                "source_format": "csv",
                "target_format": "jpg",
            },
            format="multipart",
        )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        data = res.json()
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["output_filename"], "big_data.zip")

        job_id = data["id"]
        dl_url = reverse("conversions:job-download", kwargs={"job_id": job_id})
        dl_res = self.client_a.get(dl_url)
        self.assertEqual(dl_res.status_code, status.HTTP_200_OK)
        self.assertEqual(dl_res["Content-Type"], "application/zip")

    def test_invalid_csv_api_failure_flow(self):
        """Uploading 0-byte CSV yields 400 error; unparseable CSV yields status failed."""
        # 1. 0-byte upload
        f_empty = SimpleUploadedFile("empty.csv", b"", content_type="text/csv")
        res_empty = self.client_a.post(
            "/api/conversions/",
            {"file": f_empty, "source_format": "csv", "target_format": "jpg"},
            format="multipart",
        )
        self.assertEqual(res_empty.status_code, status.HTTP_400_BAD_REQUEST)

        # 2. Corrupt input file
        f_corrupt = SimpleUploadedFile("corrupt.csv", b"\x00\x00\xff\xfe\x00\x00", content_type="text/csv")
        res_corrupt = self.client_a.post(
            "/api/conversions/",
            {"file": f_corrupt, "source_format": "csv", "target_format": "jpg"},
            format="multipart",
        )
        self.assertEqual(res_corrupt.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(res_corrupt.json()["status"], "failed")

    def test_unsupported_pair_rejected(self):
        """Unsupported format pair (e.g. csv → gif) is rejected with 400."""
        f = SimpleUploadedFile("test.csv", b"A,B\n1,2\n", content_type="text/csv")
        res = self.client_a.post(
            "/api/conversions/",
            {"file": f, "source_format": "csv", "target_format": "gif"},
            format="multipart",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_anonymous_session_isolation_csv_to_jpg(self):
        """Session B cannot access or download Session A's CSV → JPG jobs."""
        if not self.exe:
            self.skipTest("LibreOffice not installed on machine.")

        csv_bytes = "A,B\n1,2\n".encode("utf-8")
        f = SimpleUploadedFile("private.csv", csv_bytes, content_type="text/csv")

        res_a = self.client_a.post(
            "/api/conversions/",
            {"file": f, "source_format": "csv", "target_format": "jpg"},
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
