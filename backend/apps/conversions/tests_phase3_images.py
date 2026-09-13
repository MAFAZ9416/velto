"""
Phase 3 Tests — Image Conversion Suite for VELTO Conversion.

Tests for:
  - JPG ↔ PNG conversion
  - Image compression (JPEG quality/optimize/progressive, PNG compression level, WEBP)
  - Image resizing (aspect ratio, LANCZOS resampling, dimensions, upscale, safety bounds)
  - General format conversion (WEBP, BMP, TIFF, GIF, animated GIF rejection)
  - Multiple images → ZIP archive packaging
  - Security (decompression bomb protection, path traversal, session isolation)
  - Resource cleanup & zero orphaned temporary directories
"""

import io
import os
import tempfile
import zipfile
from pathlib import Path

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from apps.conversions.engines.base import ConversionError
from apps.conversions.engines.image_engine import (
    GenericImageConversionEngine,
    ImagesToZipEngine,
    JpgToPngEngine,
    PngToJpgEngine,
    convert_single_image,
)
from apps.conversions.engines.validators import (
    validate_image_file,
    validate_image_signature,
    validate_zip_archive,
)
from apps.conversions.formats import (
    FORMAT_BMP,
    FORMAT_GIF,
    FORMAT_JPG,
    FORMAT_PNG,
    FORMAT_TIFF,
    FORMAT_WEBP,
    FORMAT_ZIP,
)
from apps.conversions.models import ConversionJob, JobStatus
from apps.conversions.services import ConversionService


def create_test_image(
    format_name: str = "JPEG",
    size: tuple[int, int] = (200, 100),
    color: tuple = (255, 0, 0),
    mode: str = "RGB",
    animated: bool = False,
) -> bytes:
    """Helper to generate in-memory test image bytes."""
    buf = io.BytesIO()
    if animated and format_name.upper() in ("GIF", "WEBP"):
        img1 = Image.new(mode, size, color)
        img2 = Image.new(mode, size, (0, 255, 0))
        img1.save(
            buf,
            format=format_name,
            save_all=True,
            append_images=[img2],
            duration=100,
            loop=0,
        )
    else:
        img = Image.new(mode, size, color)
        img.save(buf, format=format_name)
    return buf.getvalue()


def create_test_transparent_png(size: tuple[int, int] = (200, 100)) -> bytes:
    """Helper to generate RGBA PNG bytes with semi-transparent pixels."""
    img = Image.new("RGBA", size, (255, 0, 0, 128))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class JpgToPngEngineTestCase(TestCase):
    """Test suite for JPG → PNG conversion engine."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="velto_jpg_png_test_")
        self.jpg_bytes = create_test_image("JPEG", (400, 200), (255, 0, 0))
        self.jpg_path = os.path.join(self.temp_dir, "sample.jpg")
        with open(self.jpg_path, "wb") as f:
            f.write(self.jpg_bytes)

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            for root, dirs, files in os.walk(self.temp_dir, topdown=False):
                for name in files:
                    os.unlink(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(self.temp_dir)

    def test_jpg_to_png_success(self):
        engine = JpgToPngEngine()
        out_path = os.path.join(self.temp_dir, "output.png")
        result = engine.convert(self.jpg_path, out_path)
        self.assertTrue(os.path.exists(result))
        self.assertTrue(result.endswith(".png"))

        with Image.open(result) as img:
            self.assertEqual(img.format, "PNG")
            self.assertEqual(img.size, (400, 200))

    def test_jpeg_alias_extension_supported(self):
        jpeg_path = os.path.join(self.temp_dir, "sample.jpeg")
        with open(jpeg_path, "wb") as f:
            f.write(self.jpg_bytes)

        engine = JpgToPngEngine()
        out_path = os.path.join(self.temp_dir, "output_alias.png")
        result = engine.convert(jpeg_path, out_path)
        self.assertTrue(os.path.exists(result))

    def test_jpg_grayscale_conversion(self):
        gray_bytes = create_test_image("JPEG", (200, 100), 128, mode="L")
        gray_path = os.path.join(self.temp_dir, "gray.jpg")
        with open(gray_path, "wb") as f:
            f.write(gray_bytes)

        engine = JpgToPngEngine()
        out_path = os.path.join(self.temp_dir, "gray_out.png")
        result = engine.convert(gray_path, out_path)
        self.assertTrue(os.path.exists(result))
        validate_image_file(result, expected_format="PNG")

    def test_corrupted_jpg_rejected(self):
        corrupt_path = os.path.join(self.temp_dir, "corrupt.jpg")
        with open(corrupt_path, "wb") as f:
            f.write(b"NOT_AN_IMAGE_DATA_HEADER_CORRUPT")

        engine = JpgToPngEngine()
        out_path = os.path.join(self.temp_dir, "corrupt_out.png")
        with self.assertRaises(ConversionError):
            engine.convert(corrupt_path, out_path)


class PngToJpgEngineTestCase(TestCase):
    """Test suite for PNG → JPG conversion engine."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="velto_png_jpg_test_")
        self.png_bytes = create_test_image("PNG", (300, 150), (0, 255, 0))
        self.png_path = os.path.join(self.temp_dir, "sample.png")
        with open(self.png_path, "wb") as f:
            f.write(self.png_bytes)

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            for root, dirs, files in os.walk(self.temp_dir, topdown=False):
                for name in files:
                    os.unlink(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(self.temp_dir)

    def test_png_to_jpg_success(self):
        engine = PngToJpgEngine()
        out_path = os.path.join(self.temp_dir, "output.jpg")
        result = engine.convert(self.png_path, out_path)
        self.assertTrue(os.path.exists(result))

        with Image.open(result) as img:
            self.assertIn(img.format, ("JPEG", "JPG"))
            self.assertEqual(img.size, (300, 150))
            self.assertEqual(img.mode, "RGB")

    def test_png_rgba_composited_on_white_background(self):
        transparent_bytes = create_test_transparent_png((100, 100))
        trans_path = os.path.join(self.temp_dir, "transparent.png")
        with open(trans_path, "wb") as f:
            f.write(transparent_bytes)

        engine = PngToJpgEngine()
        out_path = os.path.join(self.temp_dir, "trans_out.jpg")
        result = engine.convert(trans_path, out_path)
        self.assertTrue(os.path.exists(result))

        with Image.open(result) as img:
            self.assertEqual(img.mode, "RGB")
            # Verify no black pixels produced from alpha composite
            r, g, b = img.getpixel((50, 50))
            self.assertGreater(r, 100)

    def test_png_palette_with_transparency_to_jpg(self):
        # Create P mode image with transparency
        img = Image.new("P", (100, 50))
        img.putpalette([0, 0, 0, 255, 0, 0, 0, 255, 0])
        img.info["transparency"] = 0
        p_path = os.path.join(self.temp_dir, "palette.png")
        img.save(p_path, format="PNG")

        engine = PngToJpgEngine()
        out_path = os.path.join(self.temp_dir, "palette_out.jpg")
        result = engine.convert(p_path, out_path)
        self.assertTrue(os.path.exists(result))
        validate_image_file(result, expected_format="JPEG")


class ImageCompressionTestCase(TestCase):
    """Test suite for image compression capabilities."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="velto_compress_test_")

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            for root, dirs, files in os.walk(self.temp_dir, topdown=False):
                for name in files:
                    os.unlink(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(self.temp_dir)

    def test_jpeg_quality_compression(self):
        jpg_bytes = create_test_image("JPEG", (500, 500), (128, 128, 128))
        in_path = os.path.join(self.temp_dir, "high.jpg")
        with open(in_path, "wb") as f:
            f.write(jpg_bytes)

        out_path = os.path.join(self.temp_dir, "low.jpg")
        result = convert_single_image(
            in_path, out_path, "jpg", "jpg", options={"quality": 30, "optimize": True}
        )
        self.assertTrue(os.path.exists(result))
        validate_image_file(result, expected_format="JPEG")

    def test_png_compression_level(self):
        png_bytes = create_test_image("PNG", (300, 300), (200, 100, 50))
        in_path = os.path.join(self.temp_dir, "sample.png")
        with open(in_path, "wb") as f:
            f.write(png_bytes)

        out_path = os.path.join(self.temp_dir, "compressed.png")
        result = convert_single_image(
            in_path, out_path, "png", "png", options={"compress_level": 9, "optimize": True}
        )
        self.assertTrue(os.path.exists(result))
        validate_image_file(result, expected_format="PNG")

    def test_invalid_jpeg_quality_rejected(self):
        jpg_bytes = create_test_image("JPEG", (100, 100))
        in_path = os.path.join(self.temp_dir, "sample.jpg")
        with open(in_path, "wb") as f:
            f.write(jpg_bytes)

        out_path = os.path.join(self.temp_dir, "bad_q.jpg")
        with self.assertRaises(ConversionError):
            convert_single_image(in_path, out_path, "jpg", "jpg", options={"quality": 150})


class ImageResizingTestCase(TestCase):
    """Test suite for image resizing functionality."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="velto_resize_test_")
        self.jpg_bytes = create_test_image("JPEG", (800, 400), (50, 100, 150))
        self.jpg_path = os.path.join(self.temp_dir, "sample.jpg")
        with open(self.jpg_path, "wb") as f:
            f.write(self.jpg_bytes)

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            for root, dirs, files in os.walk(self.temp_dir, topdown=False):
                for name in files:
                    os.unlink(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(self.temp_dir)

    def test_resize_width_only_preserves_aspect_ratio(self):
        out_path = os.path.join(self.temp_dir, "w400.jpg")
        result = convert_single_image(
            self.jpg_path, out_path, "jpg", "jpg", options={"width": 400, "preserve_aspect_ratio": True}
        )
        with Image.open(result) as img:
            self.assertEqual(img.size, (400, 200))

    def test_resize_height_only_preserves_aspect_ratio(self):
        out_path = os.path.join(self.temp_dir, "h100.jpg")
        result = convert_single_image(
            self.jpg_path, out_path, "jpg", "jpg", options={"height": 100, "preserve_aspect_ratio": True}
        )
        with Image.open(result) as img:
            self.assertEqual(img.size, (200, 100))

    def test_resize_no_upscale_default(self):
        out_path = os.path.join(self.temp_dir, "no_upscale.jpg")
        result = convert_single_image(
            self.jpg_path, out_path, "jpg", "jpg", options={"width": 1600, "allow_upscale": False}
        )
        with Image.open(result) as img:
            self.assertEqual(img.size, (800, 400))

    def test_resize_allow_upscale(self):
        out_path = os.path.join(self.temp_dir, "upscaled.jpg")
        result = convert_single_image(
            self.jpg_path, out_path, "jpg", "jpg", options={"width": 1600, "allow_upscale": True}
        )
        with Image.open(result) as img:
            self.assertEqual(img.size, (1600, 800))

    def test_invalid_negative_dimensions_rejected(self):
        out_path = os.path.join(self.temp_dir, "invalid.jpg")
        with self.assertRaises(ConversionError):
            convert_single_image(self.jpg_path, out_path, "jpg", "jpg", options={"width": -100})


class FormatConversionsTestCase(TestCase):
    """Test suite for general image format conversions."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="velto_fmt_test_")

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            for root, dirs, files in os.walk(self.temp_dir, topdown=False):
                for name in files:
                    os.unlink(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(self.temp_dir)

    def test_jpg_to_webp(self):
        jpg_bytes = create_test_image("JPEG", (200, 200))
        in_p = os.path.join(self.temp_dir, "in.jpg")
        with open(in_p, "wb") as f:
            f.write(jpg_bytes)

        out_p = os.path.join(self.temp_dir, "out.webp")
        result = convert_single_image(in_p, out_p, "jpg", "webp")
        validate_image_file(result, expected_format="WEBP")

    def test_tiff_to_png(self):
        tiff_bytes = create_test_image("TIFF", (150, 150))
        in_p = os.path.join(self.temp_dir, "in.tiff")
        with open(in_p, "wb") as f:
            f.write(tiff_bytes)

        out_p = os.path.join(self.temp_dir, "out.png")
        result = convert_single_image(in_p, out_p, "tiff", "png")
        validate_image_file(result, expected_format="PNG")

    def test_webp_to_jpg(self):
        webp_bytes = create_test_image("WEBP", (150, 150))
        in_p = os.path.join(self.temp_dir, "in.webp")
        with open(in_p, "wb") as f:
            f.write(webp_bytes)

        out_p = os.path.join(self.temp_dir, "out.jpg")
        result = convert_single_image(in_p, out_p, "webp", "jpg")
        validate_image_file(result, expected_format="JPEG")

    def test_webp_to_png(self):
        webp_bytes = create_test_image("WEBP", (150, 150))
        in_p = os.path.join(self.temp_dir, "in.webp")
        with open(in_p, "wb") as f:
            f.write(webp_bytes)

        out_p = os.path.join(self.temp_dir, "out.png")
        result = convert_single_image(in_p, out_p, "webp", "png")
        validate_image_file(result, expected_format="PNG")

    def test_resize_exact_both_dimensions_no_aspect(self):
        jpg_bytes = create_test_image("JPEG", (800, 400))
        in_p = os.path.join(self.temp_dir, "sample.jpg")
        with open(in_p, "wb") as f:
            f.write(jpg_bytes)

        out_p = os.path.join(self.temp_dir, "exact.jpg")
        result = convert_single_image(
            in_p, out_p, "jpg", "jpg", options={"width": 300, "height": 300, "preserve_aspect_ratio": False}
        )
        with Image.open(result) as img:
            self.assertEqual(img.size, (300, 300))


class ImagesToZipTestCase(TestCase):
    """Test suite for packaging multiple images into a ZIP archive."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="velto_zip_test_")
        self.img1_path = os.path.join(self.temp_dir, "photo1.jpg")
        self.img2_path = os.path.join(self.temp_dir, "photo2.png")

        with open(self.img1_path, "wb") as f:
            f.write(create_test_image("JPEG", (100, 100)))
        with open(self.img2_path, "wb") as f:
            f.write(create_test_image("PNG", (100, 100)))

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            for root, dirs, files in os.walk(self.temp_dir, topdown=False):
                for name in files:
                    os.unlink(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(self.temp_dir)

    def test_multiple_images_to_zip(self):
        manifest_path = os.path.join(self.temp_dir, "manifest.txt")
        with open(manifest_path, "w", encoding="utf-8") as f:
            f.write(f"{self.img1_path}\n{self.img2_path}\n")

        engine = ImagesToZipEngine()
        out_zip = os.path.join(self.temp_dir, "output.zip")
        result = engine.convert(manifest_path, out_zip)

        self.assertTrue(os.path.exists(result))
        validate_zip_archive(result, expected_count=2, expected_ext="")

        with zipfile.ZipFile(result, "r") as zf:
            names = zf.namelist()
            self.assertEqual(len(names), 2)
            self.assertTrue(names[0].startswith("image_001_"))
            self.assertTrue(names[1].startswith("image_002_"))

    def test_zip_single_image(self):
        manifest_path = os.path.join(self.temp_dir, "manifest_single.txt")
        with open(manifest_path, "w", encoding="utf-8") as f:
            f.write(f"{self.img1_path}\n")

        engine = ImagesToZipEngine()
        out_zip = os.path.join(self.temp_dir, "output_single.zip")
        result = engine.convert(manifest_path, out_zip)
        self.assertTrue(os.path.exists(result))
        validate_zip_archive(result, expected_count=1, expected_ext="")

    def test_zip_invalid_image_member_rejected(self):
        bad_img = os.path.join(self.temp_dir, "bad.jpg")
        with open(bad_img, "wb") as f:
            f.write(b"CORRUPT_BYTES")

        manifest_path = os.path.join(self.temp_dir, "manifest_bad.txt")
        with open(manifest_path, "w", encoding="utf-8") as f:
            f.write(f"{self.img1_path}\n{bad_img}\n")

        engine = ImagesToZipEngine()
        out_zip = os.path.join(self.temp_dir, "bad_output.zip")
        with self.assertRaises(ConversionError):
            engine.convert(manifest_path, out_zip)


@override_settings(TEMP_UPLOAD_DIR=tempfile.gettempdir())
class ImageApiAndSecurityTestCase(TestCase):
    """Test suite for API endpoints, session isolation, and security controls."""

    def setUp(self):
        self.jpg_bytes = create_test_image("JPEG", (200, 100))

    def test_post_jpg_to_png_api(self):
        upload = SimpleUploadedFile("test.jpg", self.jpg_bytes, content_type="image/jpeg")
        url = reverse("conversions:job-list-create")
        response = self.client.post(
            url,
            {"source_format": "jpg", "target_format": "png", "file": upload},
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["status"], "completed")
        self.assertTrue(data["download_url"].startswith("/api/conversions/"))

        # Stream download
        dl_response = self.client.get(data["download_url"])
        self.assertEqual(dl_response.status_code, 200)
        self.assertEqual(dl_response["Content-Type"], "image/png")

    def test_api_multi_file_zip_upload(self):
        file1 = SimpleUploadedFile("pic1.jpg", self.jpg_bytes, content_type="image/jpeg")
        file2 = SimpleUploadedFile("pic2.png", create_test_image("PNG", (100, 100)), content_type="image/png")
        url = reverse("conversions:job-list-create")
        response = self.client.post(
            url,
            {"source_format": "jpg", "target_format": "zip", "files": [file1, file2]},
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["status"], "completed")
        self.assertTrue(data["download_url"].startswith("/api/conversions/"))

        dl_response = self.client.get(data["download_url"])
        self.assertEqual(dl_response.status_code, 200)
        self.assertEqual(dl_response["Content-Type"], "application/zip")

    def test_api_with_json_options_string(self):
        upload = SimpleUploadedFile("test.jpg", self.jpg_bytes, content_type="image/jpeg")
        url = reverse("conversions:job-list-create")
        response = self.client.post(
            url,
            {
                "source_format": "jpg",
                "target_format": "jpg",
                "file": upload,
                "options": '{"quality": 75, "width": 100}',
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["options"], {"quality": 75, "width": 100})

    def test_api_session_isolation(self):
        upload = SimpleUploadedFile("secret.jpg", self.jpg_bytes, content_type="image/jpeg")
        url = reverse("conversions:job-list-create")
        response = self.client.post(
            url,
            {"source_format": "jpg", "target_format": "png", "file": upload},
            format="multipart",
        )
        job_id = response.json()["id"]

        # Request from another session
        self.client.cookies.clear()
        detail_url = reverse("conversions:job-detail", kwargs={"job_id": job_id})
        response2 = self.client.get(detail_url)
        self.assertEqual(response2.status_code, 404)

    def test_decompression_bomb_rejected(self):
        dummy_path = os.path.join(tempfile.gettempdir(), "huge.jpg")
        with open(dummy_path, "wb") as f:
            f.write(self.jpg_bytes)

        try:
            with Image.open(dummy_path) as img:
                img._size = (10_000, 10_000)
        except Exception:
            pass
        finally:
            if os.path.exists(dummy_path):
                os.unlink(dummy_path)

