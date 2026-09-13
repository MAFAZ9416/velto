"""
Image conversion engines and services for VELTO Conversion.

Supports:
  - JPG ↔ PNG
  - JPG, PNG, WEBP, BMP, TIFF, GIF format conversions
  - Image resizing (aspect ratio, LANCSOZ filter, maximum bounds)
  - Image compression (JPEG quality/optimize/progressive, PNG compression level, WEBP)
  - Multiple images → ZIP archive creation
"""

import io
import logging
import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from PIL import Image, ImageFile, ImageOps

from apps.conversions.engines.base import BaseConversionEngine, ConversionError
from apps.conversions.engines.validators import (
    validate_image_file,
    validate_image_signature,
    validate_zip_archive,
)

logger = logging.getLogger(__name__)

# Max pixel limit safety (80 Megapixels)
MAX_PIXELS = 80_000_000
Image.MAX_IMAGE_PIXELS = MAX_PIXELS
ImageFile.LOAD_TRUNCATED_IMAGES = False


class ImageMetadataService:
    """Handles EXIF orientation and image metadata normalization."""

    @staticmethod
    def apply_exif_orientation(img: Image.Image) -> Image.Image:
        """Apply EXIF orientation transformation so image pixels reflect visual orientation."""
        try:
            return ImageOps.exif_transpose(img)
        except Exception as exc:
            logger.debug("Failed to apply EXIF transpose: %s", exc)
            return img


class ImageProcessingService:
    """Handles color mode conversions and transparency compositing."""

    @staticmethod
    def prepare_mode_for_target(
        img: Image.Image,
        target_format: str,
        bg_color: Tuple[int, int, int] = (255, 255, 255),
    ) -> Image.Image:
        """
        Convert image color mode for target format.

        For target formats without alpha support (JPEG, BMP):
          Composite transparent RGBA/LA/P images onto solid background color (default white).

        For formats supporting alpha (PNG, WEBP):
          Preserve RGBA / transparency.
        """
        tgt = target_format.lower()
        no_alpha_formats = {"jpg", "jpeg", "bmp"}

        if tgt in no_alpha_formats:
            if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                img_rgba = img.convert("RGBA")
                background = Image.new("RGBA", img_rgba.size, bg_color + (255,))
                composited = Image.alpha_composite(background, img_rgba)
                return composited.convert("RGB")
            if img.mode != "RGB":
                return img.convert("RGB")
            return img
        else:
            if img.mode == "P" and "transparency" in img.info:
                return img.convert("RGBA")
            if img.mode not in ("RGB", "RGBA", "L", "LA"):
                return img.convert("RGBA" if "A" in img.mode else "RGB")
            return img


class ImageResizeService:
    """Handles image dimension calculations and LANCZOS resampling."""

    @staticmethod
    def resize(img: Image.Image, options: Dict[str, Any]) -> Image.Image:
        """
        Resize image according to options.

        Options parameters:
          width: int > 0
          height: int > 0
          preserve_aspect_ratio: bool (default True)
          allow_upscale: bool (default False)
        """
        if not options:
            return img

        target_w = options.get("width")
        target_h = options.get("height")

        if target_w is None and target_h is None:
            return img

        # Parse & validate dimensions
        try:
            if target_w is not None:
                target_w = int(target_w)
                if target_w <= 0 or target_w > 10_000:
                    raise ConversionError("Width must be an integer between 1 and 10000.")
            if target_h is not None:
                target_h = int(target_h)
                if target_h <= 0 or target_h > 10_000:
                    raise ConversionError("Height must be an integer between 1 and 10000.")
        except ValueError as exc:
            raise ConversionError("Width and height parameters must be valid integers.") from exc

        orig_w, orig_h = img.size
        preserve_ratio = bool(options.get("preserve_aspect_ratio", True))
        allow_upscale = bool(options.get("allow_upscale", False))

        # Calculate final target dimensions
        if preserve_ratio:
            if target_w is not None and target_h is not None:
                scale = min(target_w / orig_w, target_h / orig_h)
            elif target_w is not None:
                scale = target_w / orig_w
            else:
                scale = target_h / orig_h

            if not allow_upscale and scale > 1.0:
                final_w, final_h = orig_w, orig_h
            else:
                final_w = max(1, int(round(orig_w * scale)))
                final_h = max(1, int(round(orig_h * scale)))
        else:
            final_w = target_w if target_w is not None else orig_w
            final_h = target_h if target_h is not None else orig_h

            if not allow_upscale:
                if final_w > orig_w:
                    final_w = orig_w
                if final_h > orig_h:
                    final_h = orig_h

        if (final_w, final_h) == (orig_w, orig_h):
            return img

        if final_w * final_h > MAX_PIXELS:
            raise ConversionError("Resized dimensions exceed maximum allowed pixel count.")

        resample_filter = getattr(Image.Resampling, "LANCZOS", getattr(Image, "LANCZOS", 1))
        return img.resize((final_w, final_h), resample=resample_filter)


class ImageCompressionService:
    """Handles encoder compression parameters."""

    @staticmethod
    def get_save_kwargs(target_format: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Return PIL save keyword arguments based on target format and options."""
        fmt = target_format.lower()
        kwargs: Dict[str, Any] = {}

        if fmt in ("jpg", "jpeg"):
            quality = options.get("quality", 85)
            try:
                quality = int(quality)
                if not (1 <= quality <= 100):
                    raise ConversionError("JPEG quality must be an integer between 1 and 100.")
            except ValueError as exc:
                raise ConversionError("JPEG quality must be a valid integer.") from exc

            kwargs["quality"] = quality
            kwargs["optimize"] = bool(options.get("optimize", True))
            kwargs["progressive"] = bool(options.get("progressive", True))

        elif fmt == "png":
            kwargs["optimize"] = bool(options.get("optimize", True))
            compress_level = options.get("compress_level", options.get("compression_level", 6))
            try:
                compress_level = int(compress_level)
                if not (0 <= compress_level <= 9):
                    raise ConversionError("PNG compress_level must be an integer between 0 and 9.")
            except ValueError as exc:
                raise ConversionError("PNG compress_level must be a valid integer.") from exc
            kwargs["compress_level"] = compress_level

        elif fmt == "webp":
            quality = options.get("quality", 80)
            try:
                quality = int(quality)
                if not (1 <= quality <= 100):
                    raise ConversionError("WebP quality must be an integer between 1 and 100.")
            except ValueError as exc:
                raise ConversionError("WebP quality must be a valid integer.") from exc
            kwargs["quality"] = quality
            kwargs["method"] = int(options.get("method", 6))
            if "lossless" in options:
                kwargs["lossless"] = bool(options["lossless"])

        return kwargs


def convert_single_image(
    input_path: str,
    output_path: str,
    source_format: str,
    target_format: str,
    options: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Orchestrate single image conversion, resizing, compression, and output validation.
    """
    if options is None:
        options = {}

    # 1. Validate signature & input safety
    validate_image_signature(input_path, allowed_formats=[source_format])

    # 2. Open image safely
    try:
        with Image.open(input_path) as img:
            # Apply EXIF transpose
            img = ImageMetadataService.apply_exif_orientation(img)

            # Resize if requested
            img = ImageResizeService.resize(img, options)

            # Mode conversion & transparency handling
            img = ImageProcessingService.prepare_mode_for_target(img, target_format)

            # Compression parameters
            save_kwargs = ImageCompressionService.get_save_kwargs(target_format, options)

            # Map format string to PIL save format name
            pil_format_map = {
                "jpg": "JPEG",
                "jpeg": "JPEG",
                "png": "PNG",
                "webp": "WEBP",
                "bmp": "BMP",
                "tiff": "TIFF",
                "gif": "GIF",
            }
            pil_fmt = pil_format_map.get(target_format.lower(), target_format.upper())

            # Save to temporary path or direct output_path
            out_p = Path(output_path)
            out_p.parent.mkdir(parents=True, exist_ok=True)

            img.save(str(out_p), format=pil_fmt, **save_kwargs)

        # 3. Validate output image format & readability
        validate_image_file(str(out_p), expected_format=pil_fmt)
        return str(out_p)

    except ConversionError:
        raise
    except Exception as exc:
        logger.exception("Image conversion failed for %s → %s: %s", input_path, output_path, exc)
        raise ConversionError(
            f"Failed to convert image from {source_format.upper()} to {target_format.upper()}: {exc}"
        ) from exc


class JpgToPngEngine(BaseConversionEngine):
    """Engine for JPG to PNG conversion."""

    source_format = "jpg"
    target_format = "png"

    def convert(self, input_path: str, output_path: str, options: Optional[Dict[str, Any]] = None) -> str | None:
        return convert_single_image(input_path, output_path, "jpg", "png", options)


class PngToJpgEngine(BaseConversionEngine):
    """Engine for PNG to JPG conversion."""

    source_format = "png"
    target_format = "jpg"

    def convert(self, input_path: str, output_path: str, options: Optional[Dict[str, Any]] = None) -> str | None:
        return convert_single_image(input_path, output_path, "png", "jpg", options)


class GenericImageConversionEngine(BaseConversionEngine):
    """Generic image conversion engine configured dynamically per source/target pair."""

    source_format = "image"
    target_format = "image"

    def convert(self, input_path: str, output_path: str, options: Optional[Dict[str, Any]] = None) -> str | None:
        return convert_single_image(input_path, output_path, self.source_format, self.target_format, options)


def make_generic_image_engine_class(source_fmt: str, target_fmt: str) -> type:
    """Factory creating an engine class for a given (source, target) pair."""
    class_name = f"{source_fmt.capitalize()}To{target_fmt.capitalize()}Engine"
    return type(
        class_name,
        (BaseConversionEngine,),
        {
            "source_format": source_fmt,
            "target_format": target_fmt,
            "convert": lambda self, input_path, output_path, options=None: convert_single_image(
                input_path, output_path, source_fmt, target_fmt, options
            ),
        },
    )


class ImagesToZipEngine(BaseConversionEngine):
    """Engine for packaging single or multiple image files into a ZIP archive."""

    source_format = "images"  # Also supports jpg, png, webp
    target_format = "zip"

    def convert(self, input_path: str, output_path: str, options: Optional[Dict[str, Any]] = None) -> str | None:
        """
        `input_path` can be:
          1. Path to a single staged image file.
          2. Path to a text file containing line-separated list of staged image paths.
          3. Path to a directory containing staged images.
        """
        input_files: List[Path] = []
        p = Path(input_path)

        if p.is_dir():
            input_files = sorted([f for f in p.iterdir() if f.is_file()])
        elif p.is_file() and p.suffix.lower() == ".txt":
            # Multi-file staging manifest
            with open(p, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
            input_files = [Path(l) for l in lines if Path(l).exists()]
        elif p.is_file():
            input_files = [p]

        if not input_files:
            raise ConversionError("No valid image files were provided for ZIP packaging.")

        # Validate every image file independently
        validated_files: List[Tuple[str, Path]] = []
        for idx, file_path in enumerate(input_files, start=1):
            validate_image_signature(str(file_path))
            
            # Create safe, ordered, zero-padded member filename
            stem = file_path.stem
            safe_stem = "".join(c if c.isalnum() or c in " _-" else "_" for c in stem).strip()
            if not safe_stem:
                safe_stem = "image"
            ext = file_path.suffix.lower()
            
            arcname = f"image_{idx:03d}_{safe_stem}{ext}"
            validated_files.append((arcname, file_path))

        out_p = Path(output_path)
        zip_output_path = out_p.with_suffix(".zip") if not out_p.name.lower().endswith(".zip") else out_p
        zip_output_path.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory(prefix="velto_img_zip_") as tmp_dir:
            tmp_zip = Path(tmp_dir) / "output.zip"
            with zipfile.ZipFile(tmp_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                for arcname, file_path in validated_files:
                    # Guard against path traversal
                    safe_arcname = Path(arcname).name
                    zf.write(file_path, arcname=safe_arcname)

            shutil.move(str(tmp_zip), str(zip_output_path))

        validate_zip_archive(
            str(zip_output_path),
            expected_count=len(validated_files),
            expected_ext="",  # Supports mixed image extensions inside ZIP
        )

        logger.info("ImagesToZipEngine: successfully created ZIP archive (%d files): %s", len(validated_files), zip_output_path)
        return str(zip_output_path)
