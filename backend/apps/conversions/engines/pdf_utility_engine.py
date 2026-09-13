"""
PDF Utilities Engine Implementation for VELTO Conversion (Phase 5A).

Operations Implemented:
  - pdf_merge          (Merge 2+ PDFs in exact order)
  - pdf_split          (Split PDF by every_page / ranges / chunks into ZIP)
  - pdf_extract_pages  (Extract specific page ranges into single PDF)
"""

import logging
import os
from pathlib import Path
import tempfile
import zipfile

import fitz  # PyMuPDF

from apps.conversions.engines.base import BaseConversionEngine, ConversionError
from apps.conversions.engines.validators import (
    MAX_PDF_SPLIT_OUTPUTS,
    validate_docx_output,
    validate_output_file,
    validate_pdf_output,
    validate_pdf_utility_input,
    validate_zip_archive,
)
from apps.conversions.formats import FORMAT_PDF, FORMAT_ZIP
from apps.conversions.utils.page_range import parse_page_range

logger = logging.getLogger(__name__)


# ── PDF Merge Engine ──────────────────────────────────────────────────────────

class PdfMergeEngine(BaseConversionEngine):
    source_format = FORMAT_PDF
    target_format = FORMAT_PDF
    operation = "pdf_merge"
    output_extension = ".pdf"
    mime_type = "application/pdf"

    def convert(self, input_path: str, output_path: str, options: dict | None = None) -> str | None:
        opts = options or {}
        input_paths = opts.get("input_paths")
        if not input_paths or not isinstance(input_paths, (list, tuple)):
            if input_path.endswith("_staged_manifest.txt") and Path(input_path).exists():
                with open(input_path, "r", encoding="utf-8") as mf:
                    input_paths = [line.strip() for line in mf if line.strip()]
            else:
                input_paths = [input_path]

        docs = validate_pdf_utility_input(input_paths, min_files=2, max_files=100)
        total_expected_pages = sum(len(d) for d in docs)

        merged_doc = fitz.open()
        try:
            for doc in docs:
                merged_doc.insert_pdf(doc)
                doc.close()

            out_dir = Path(output_path).parent
            out_dir.mkdir(parents=True, exist_ok=True)
            merged_doc.save(output_path, garbage=4, deflate=True)
        except Exception as exc:
            logger.error("PdfMergeEngine failed: %s", exc)
            raise ConversionError("pdf_merge_failed: Failed to merge PDF files.") from exc
        finally:
            merged_doc.close()
            for doc in docs:
                try:
                    doc.close()
                except Exception:
                    pass

        validate_pdf_output(output_path)

        # Verify page count
        out_doc = fitz.open(output_path)
        out_count = len(out_doc)
        out_doc.close()
        if out_count != total_expected_pages:
            raise ConversionError(f"corrupted_pdf: Merged PDF page count ({out_count}) does not match total input pages ({total_expected_pages}).")

        return output_path


# ── PDF Split Engine ──────────────────────────────────────────────────────────

class PdfSplitEngine(BaseConversionEngine):
    source_format = FORMAT_PDF
    target_format = FORMAT_ZIP
    operation = "pdf_split"
    output_extension = ".zip"
    mime_type = "application/zip"

    def convert(self, input_path: str, output_path: str, options: dict | None = None) -> str | None:
        opts = options or {}
        split_mode = opts.get("split_mode", "every_page").lower()

        docs = validate_pdf_utility_input(input_path, min_files=1, max_files=1)
        src_doc = docs[0]
        total_pages = len(src_doc)

        split_parts = []  # List of (filename, page_indices_list)

        try:
            if split_mode == "every_page":
                for idx in range(total_pages):
                    fname = f"document-page-{idx + 1:03d}.pdf"
                    split_parts.append((fname, [idx]))
            elif split_mode == "ranges":
                ranges_input = opts.get("ranges")
                if not ranges_input or not isinstance(ranges_input, (list, tuple)):
                    raise ConversionError("invalid_ranges: Range list is required for 'ranges' split mode.")

                used_pages = set()
                for r_idx, range_item in enumerate(ranges_input, start=1):
                    indices = parse_page_range(range_item, total_pages, allow_duplicates=False)
                    for idx in indices:
                        if idx in used_pages:
                            raise ConversionError(f"invalid_ranges: Overlapping range detected for page {idx + 1}.")
                        used_pages.add(idx)

                    fname = f"document-part-{r_idx:03d}.pdf"
                    split_parts.append((fname, indices))
            elif split_mode == "chunks":
                pages_per_file = opts.get("pages_per_file")
                if not pages_per_file or not isinstance(pages_per_file, int) or pages_per_file < 1:
                    raise ConversionError("invalid_chunk_size: pages_per_file must be a positive integer.")

                part_num = 1
                for start_idx in range(0, total_pages, pages_per_file):
                    end_idx = min(start_idx + pages_per_file, total_pages)
                    indices = list(range(start_idx, end_idx))
                    fname = f"document-part-{part_num:03d}.pdf"
                    split_parts.append((fname, indices))
                    part_num += 1
            else:
                raise ConversionError(f"unsupported_operation: Invalid split mode '{split_mode}'. Supported modes: 'every_page', 'ranges', 'chunks'.")

            if len(split_parts) > MAX_PDF_SPLIT_OUTPUTS:
                raise ConversionError(f"page_count_exceeded: Split operation yields {len(split_parts)} output files (exceeds safety limit of {MAX_PDF_SPLIT_OUTPUTS}).")

            # Create split PDF files in isolated temporary directory
            with tempfile.TemporaryDirectory(prefix="velto_pdf_split_", ignore_cleanup_errors=True) as temp_dir:
                generated_files = []
                for fname, indices in split_parts:
                    part_pdf_path = os.path.join(temp_dir, fname)
                    part_doc = fitz.open()
                    for page_idx in indices:
                        part_doc.insert_pdf(src_doc, from_page=page_idx, to_page=page_idx)
                    part_doc.save(part_pdf_path, garbage=4, deflate=True)
                    part_doc.close()

                    validate_pdf_output(part_pdf_path)
                    generated_files.append((fname, part_pdf_path))

                # Package into deterministic ZIP archive
                out_dir = Path(output_path).parent
                out_dir.mkdir(parents=True, exist_ok=True)

                with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
                    for fname, part_path in sorted(generated_files, key=lambda x: x[0]):
                        # Security check: sanitize zip member name (prevent path traversal)
                        safe_arcname = Path(fname).name
                        if ".." in safe_arcname or safe_arcname.startswith(("/", "\\")):
                            raise ConversionError("invalid_pdf: Unsafe member filename detected.")
                        zf.write(part_path, arcname=safe_arcname)

            validate_zip_archive(output_path, len(split_parts), ".pdf")
            return output_path
        finally:
            src_doc.close()


# ── PDF Extract Pages Engine ──────────────────────────────────────────────────

class PdfExtractPagesEngine(BaseConversionEngine):
    source_format = FORMAT_PDF
    target_format = FORMAT_PDF
    operation = "pdf_extract_pages"
    output_extension = ".pdf"
    mime_type = "application/pdf"

    def convert(self, input_path: str, output_path: str, options: dict | None = None) -> str | None:
        opts = options or {}
        pages_expr = opts.get("pages")
        if not pages_expr:
            raise ConversionError("page_range_invalid: Page selection 'pages' option is required for page extraction.")

        docs = validate_pdf_utility_input(input_path, min_files=1, max_files=1)
        src_doc = docs[0]

        try:
            indices = parse_page_range(pages_expr, len(src_doc), allow_duplicates=False)
            extracted_doc = fitz.open()
            for idx in indices:
                extracted_doc.insert_pdf(src_doc, from_page=idx, to_page=idx)

            out_dir = Path(output_path).parent
            out_dir.mkdir(parents=True, exist_ok=True)
            extracted_doc.save(output_path, garbage=4, deflate=True)
            extracted_doc.close()
        except ConversionError:
            raise
        except Exception as exc:
            logger.error("PdfExtractPagesEngine failed: %s", exc)
            raise ConversionError("pdf_extract_failed: Failed to extract selected pages from PDF.") from exc
        finally:
            src_doc.close()

        validate_pdf_output(output_path)

        out_doc = fitz.open(output_path)
        out_count = len(out_doc)
        out_doc.close()
        if out_count != len(indices):
            raise ConversionError(f"corrupted_pdf: Extracted PDF page count ({out_count}) does not match requested count ({len(indices)}).")

        return output_path


# ── PDF Rotate Engine ─────────────────────────────────────────────────────────

class PdfRotateEngine(BaseConversionEngine):
    source_format = FORMAT_PDF
    target_format = FORMAT_PDF
    operation = "pdf_rotate"
    output_extension = ".pdf"
    mime_type = "application/pdf"

    def convert(self, input_path: str, output_path: str, options: dict | None = None) -> str | None:
        opts = options or {}

        # 1. Validate rotation parameter
        raw_rotation = opts.get("rotation")
        if raw_rotation is None:
            raise ConversionError("invalid_rotation: Rotation parameter 'rotation' is required.")
        try:
            rotation = int(raw_rotation)
        except (ValueError, TypeError):
            raise ConversionError(f"invalid_rotation: Invalid rotation value '{raw_rotation}'. Must be 90, 180, or 270.")

        if rotation not in (90, 180, 270):
            raise ConversionError(f"invalid_rotation: Rotation angle must be 90, 180, or 270 degrees (got {rotation}).")

        # 2. Validate scope parameter
        raw_scope = opts.get("scope", "all")
        scope = str(raw_scope).lower().strip() if raw_scope is not None else "all"
        if scope not in ("all", "selected"):
            raise ConversionError(f"invalid_scope: Invalid scope '{raw_scope}'. Must be 'all' or 'selected'.")

        pages_expr = opts.get("pages")
        if scope == "selected" and not pages_expr:
            raise ConversionError("pages_required: Page range selection 'pages' is required when scope is 'selected'.")

        # 3. Validate input PDF file
        docs = validate_pdf_utility_input(input_path, min_files=1, max_files=1)
        src_doc = docs[0]
        total_pages = len(src_doc)

        try:
            # Resolve page indices to rotate
            if scope == "all":
                target_indices = set(range(total_pages))
            else:
                target_indices = set(parse_page_range(pages_expr, total_pages, allow_duplicates=False))

            original_rotations = []
            expected_rotations = []

            for idx in range(total_pages):
                page = src_doc[idx]
                orig_rot = page.rotation
                original_rotations.append(orig_rot)

                if idx in target_indices:
                    new_rot = (orig_rot + rotation) % 360
                    page.set_rotation(new_rot)
                    expected_rotations.append(new_rot)
                else:
                    expected_rotations.append(orig_rot)

            out_dir = Path(output_path).parent
            out_dir.mkdir(parents=True, exist_ok=True)
            src_doc.save(output_path, garbage=4, deflate=True)
        except ConversionError:
            raise
        except Exception as exc:
            logger.error("PdfRotateEngine failed: %s", exc)
            raise ConversionError("pdf_rotate_failed: Failed to rotate PDF pages.") from exc
        finally:
            src_doc.close()

        # 4. Validate output PDF file
        validate_pdf_output(output_path)

        # 5. Verify page rotations, page count, and text extractability
        out_doc = fitz.open(output_path)
        try:
            if len(out_doc) != total_pages:
                raise ConversionError(f"corrupted_pdf: Rotated PDF page count ({len(out_doc)}) does not match input page count ({total_pages}).")

            for idx in range(total_pages):
                out_page = out_doc[idx]
                actual_rot = out_page.rotation
                expected_rot = expected_rotations[idx]
                if actual_rot != expected_rot:
                    raise ConversionError(f"corrupted_pdf: Page {idx + 1} rotation is {actual_rot}°, expected {expected_rot}°.")

                # Confirm text extraction works cleanly without error
                _ = out_page.get_text()
        finally:
            out_doc.close()

        return output_path


# ── PDF Compress Engine ───────────────────────────────────────────────────────

class PdfCompressEngine(BaseConversionEngine):
    source_format = FORMAT_PDF
    target_format = FORMAT_PDF
    operation = "pdf_compress"
    output_extension = ".pdf"
    mime_type = "application/pdf"

    SUPPORTED_PROFILES = ("lossless", "balanced", "strong")

    def convert(self, input_path: str, output_path: str, options: dict | None = None) -> str | None:
        opts = options if options is not None else {}

        # 1. Validate profile parameter
        raw_profile = opts.get("profile", "lossless")
        profile = str(raw_profile).lower().strip() if raw_profile is not None else "lossless"
        if not profile:
            profile = "lossless"

        if profile not in self.SUPPORTED_PROFILES:
            raise ConversionError(
                f"invalid_profile: Invalid compression profile '{raw_profile}'. "
                f"Supported profiles: lossless, balanced, strong."
            )

        # 2. Measure input file size & validate PDF input
        original_size = Path(input_path).stat().st_size if Path(input_path).exists() else 0
        docs = validate_pdf_utility_input(input_path, min_files=1, max_files=1)
        src_doc = docs[0]
        total_pages = len(src_doc)

        input_rects = [src_doc[i].rect for i in range(total_pages)]

        try:
            # 3. Apply profile-specific compression optimizations
            if profile == "strong":
                for page in src_doc:
                    try:
                        for img_info in page.get_images():
                            xref = img_info[0]
                            try:
                                pix = fitz.Pixmap(src_doc, xref)
                                if pix.colorspace and pix.colorspace.name in (fitz.csGRAY.name, fitz.csRGB.name):
                                    if pix.width > 1024 or pix.height > 1024:
                                        scale = min(1024 / pix.width, 1024 / pix.height)
                                        new_w = max(1, int(pix.width * scale))
                                        new_h = max(1, int(pix.height * scale))
                                        scaled_pix = fitz.Pixmap(pix, new_w, new_h, None)
                                        jpeg_bytes = scaled_pix.tobytes("jpeg", jpg_quality=70)
                                        src_doc.update_stream(xref, jpeg_bytes)
                                        scaled_pix = None
                                    elif getattr(pix, "alpha", 0) == 0:
                                        jpeg_bytes = pix.tobytes("jpeg", jpg_quality=70)
                                        if len(jpeg_bytes) < len(pix.samples):
                                            src_doc.update_stream(xref, jpeg_bytes)
                                pix = None
                            except Exception:
                                pass
                    except Exception:
                        pass

                out_dir = Path(output_path).parent
                out_dir.mkdir(parents=True, exist_ok=True)
                src_doc.save(
                    output_path,
                    garbage=4,
                    deflate=True,
                    clean=True,
                    deflate_images=True,
                    deflate_fonts=True,
                )

            elif profile == "balanced":
                out_dir = Path(output_path).parent
                out_dir.mkdir(parents=True, exist_ok=True)
                src_doc.save(
                    output_path,
                    garbage=4,
                    deflate=True,
                    clean=True,
                    deflate_images=True,
                    deflate_fonts=True,
                )

            else:  # lossless
                out_dir = Path(output_path).parent
                out_dir.mkdir(parents=True, exist_ok=True)
                src_doc.save(
                    output_path,
                    garbage=4,
                    deflate=True,
                    clean=True,
                )
        except ConversionError:
            raise
        except Exception as exc:
            logger.error("PdfCompressEngine failed: %s", exc)
            raise ConversionError("compression_failed: Failed to compress PDF document.") from exc
        finally:
            src_doc.close()

        # 4. Validate output PDF file
        try:
            validate_pdf_output(output_path)
        except ConversionError as exc:
            if Path(output_path).exists():
                try:
                    os.remove(output_path)
                except OSError:
                    pass
            raise ConversionError(f"output_validation_failed: Compressed PDF output failed validation ({exc}).") from exc

        # 5. Verify page count, page dimensions, text searchability, and measure output size
        output_size = Path(output_path).stat().st_size
        out_doc = fitz.open(output_path)
        try:
            if len(out_doc) != total_pages:
                raise ConversionError(
                    f"output_validation_failed: Compressed PDF page count ({len(out_doc)}) "
                    f"does not match input ({total_pages})."
                )

            for idx in range(total_pages):
                out_page = out_doc[idx]
                in_rect = input_rects[idx]
                out_rect = out_page.rect

                if abs(in_rect.width - out_rect.width) > 1.0 or abs(in_rect.height - out_rect.height) > 1.0:
                    raise ConversionError(
                        f"output_validation_failed: Page {idx + 1} dimensions changed during compression."
                    )

                _ = out_page.get_text()
        except ConversionError:
            out_doc.close()
            if Path(output_path).exists():
                try:
                    os.remove(output_path)
                except OSError:
                    pass
            raise
        finally:
            out_doc.close()

        # 6. Build compression result metadata
        saved_bytes = original_size - output_size
        if original_size > 0:
            saved_percent = round((saved_bytes / original_size) * 100.0, 2)
        else:
            saved_percent = 0.0

        compression_reduced_size = bool(saved_bytes > 0)

        metadata = {
            "profile": profile,
            "original_size": original_size,
            "output_size": output_size,
            "saved_bytes": saved_bytes,
            "saved_percent": saved_percent,
            "compression_reduced_size": compression_reduced_size,
        }

        opts["compression_metadata"] = metadata
        opts["result_metadata"] = metadata

        logger.info(
            "PdfCompressEngine (%s): original=%d bytes, output=%d bytes, saved=%d bytes (%.2f%%)",
            profile,
            original_size,
            output_size,
            saved_bytes,
            saved_percent,
        )

        return output_path


# ── PDF Watermark Engine ──────────────────────────────────────────────────────

class PdfWatermarkEngine(BaseConversionEngine):
    source_format = FORMAT_PDF
    target_format = FORMAT_PDF
    operation = "pdf_watermark"
    output_extension = ".pdf"
    mime_type = "application/pdf"

    def convert(self, input_path: str, output_path: str, options: dict | None = None) -> str | None:
        opts = options if options is not None else {}
        text = opts.get("text")
        if not text or not isinstance(text, str) or not text.strip():
            raise ConversionError("watermark_text_required: Watermark text 'text' option is required.")

        text = text.strip()
        if len(text) > 500:
            raise ConversionError("watermark_text_too_long: Watermark text must not exceed 500 characters.")

        raw_scope = opts.get("scope", "all")
        scope = str(raw_scope).lower().strip() if raw_scope else "all"
        if scope not in ("all", "selected"):
            raise ConversionError(f"invalid_scope: Invalid scope '{raw_scope}'. Must be 'all' or 'selected'.")

        pages_expr = opts.get("pages")
        if scope == "selected" and not pages_expr:
            raise ConversionError("pages_required: Page range selection 'pages' is required when scope is 'selected'.")

        position = str(opts.get("position", "center")).lower().strip()
        valid_positions = ("top-left", "top-center", "top-right", "center", "bottom-left", "bottom-center", "bottom-right")
        if position not in valid_positions:
            raise ConversionError(f"invalid_position: Position must be one of {', '.join(valid_positions)}.")

        try:
            opacity = float(opts.get("opacity", 0.3))
        except (ValueError, TypeError):
            raise ConversionError("invalid_opacity: Opacity must be a number between 0.0 and 1.0.")
        if opacity < 0.0 or opacity > 1.0:
            raise ConversionError(f"invalid_opacity: Opacity {opacity} is out of bounds [0.0, 1.0].")

        try:
            rotation = float(opts.get("rotation", 45.0))
        except (ValueError, TypeError):
            raise ConversionError("invalid_rotation: Rotation must be a number.")
        if rotation < -360.0 or rotation > 360.0:
            raise ConversionError(f"invalid_rotation: Rotation angle {rotation} is out of bounds [-360, 360].")

        try:
            font_size = float(opts.get("font_size", 36.0))
        except (ValueError, TypeError):
            raise ConversionError("invalid_font_size: Font size must be a number.")
        if font_size < 8.0 or font_size > 144.0:
            raise ConversionError(f"invalid_font_size: Font size {font_size} is out of bounds [8, 144].")

        hex_color = str(opts.get("color", "#808080")).strip()
        color_tuple = self._parse_hex_color(hex_color)

        docs = validate_pdf_utility_input(input_path, min_files=1, max_files=1)
        src_doc = docs[0]
        total_pages = len(src_doc)
        input_rects = [src_doc[i].rect for i in range(total_pages)]

        try:
            if scope == "all":
                target_indices = set(range(total_pages))
            else:
                target_indices = set(parse_page_range(pages_expr, total_pages, allow_duplicates=False))

            for idx in target_indices:
                page = src_doc[idx]
                rect = page.rect
                w, h = rect.width, rect.height

                if position == "top-left":
                    pt = fitz.Point(rect.x0 + 36, rect.y0 + 36 + font_size)
                elif position == "top-center":
                    pt = fitz.Point(rect.x0 + w / 2, rect.y0 + 36 + font_size)
                elif position == "top-right":
                    pt = fitz.Point(rect.x0 + w - 36, rect.y0 + 36 + font_size)
                elif position == "bottom-left":
                    pt = fitz.Point(rect.x0 + 36, rect.y0 + h - 36)
                elif position == "bottom-center":
                    pt = fitz.Point(rect.x0 + w / 2, rect.y0 + h - 36)
                elif position == "bottom-right":
                    pt = fitz.Point(rect.x0 + w - 36, rect.y0 + h - 36)
                else:  # center
                    pt = fitz.Point(rect.x0 + w / 2, rect.y0 + h / 2)

                kwargs = {
                    "fontsize": font_size,
                    "color": color_tuple,
                    "fill_opacity": opacity,
                    "overlay": True,
                }
                rot_int = int(rotation)
                if rot_int in (0, 90, 180, 270) and float(rot_int) == rotation:
                    kwargs["rotate"] = rot_int
                else:
                    kwargs["morph"] = (pt, fitz.Matrix(rotation))

                page.insert_text(pt, text, **kwargs)

            out_dir = Path(output_path).parent
            out_dir.mkdir(parents=True, exist_ok=True)
            src_doc.save(output_path, garbage=4, deflate=True)
        except ConversionError:
            raise
        except Exception as exc:
            logger.error("PdfWatermarkEngine failed: %s", exc)
            raise ConversionError("pdf_watermark_failed: Failed to apply watermark to PDF.") from exc
        finally:
            src_doc.close()

        validate_pdf_output(output_path)

        out_doc = fitz.open(output_path)
        try:
            if len(out_doc) != total_pages:
                raise ConversionError(f"corrupted_pdf: Watermarked PDF page count ({len(out_doc)}) does not match input ({total_pages}).")
            for idx in range(total_pages):
                in_rect = input_rects[idx]
                out_rect = out_doc[idx].rect
                if abs(in_rect.width - out_rect.width) > 1.0 or abs(in_rect.height - out_rect.height) > 1.0:
                    raise ConversionError(f"corrupted_pdf: Page {idx+1} dimensions changed during watermarking.")
        finally:
            out_doc.close()

        return output_path

    @staticmethod
    def _parse_hex_color(color_str: str) -> tuple[float, float, float]:
        cs = color_str.lstrip("#")
        if len(cs) == 3:
            cs = "".join(c * 2 for c in cs)
        if len(cs) != 6:
            return (0.5, 0.5, 0.5)
        try:
            r = int(cs[0:2], 16) / 255.0
            g = int(cs[2:4], 16) / 255.0
            b = int(cs[4:6], 16) / 255.0
            return (r, g, b)
        except ValueError:
            return (0.5, 0.5, 0.5)


# ── PDF Password Protect Engine ───────────────────────────────────────────────

class PdfProtectEngine(BaseConversionEngine):
    source_format = FORMAT_PDF
    target_format = FORMAT_PDF
    operation = "pdf_protect"
    output_extension = ".pdf"
    mime_type = "application/pdf"

    def convert(self, input_path: str, output_path: str, options: dict | None = None) -> str | None:
        opts = options if options is not None else {}
        password = opts.get("password") or opts.get("user_password")
        if not password or not isinstance(password, str):
            raise ConversionError("password_required: Password parameter 'password' is required.")

        owner_password = opts.get("owner_password") or password
        if not isinstance(owner_password, str):
            owner_password = password

        docs = validate_pdf_utility_input(input_path, min_files=1, max_files=1, allow_encrypted=False)
        src_doc = docs[0]

        try:
            out_dir = Path(output_path).parent
            out_dir.mkdir(parents=True, exist_ok=True)

            perm = opts.get("permissions")
            perm_int = int(perm) if perm is not None and str(perm).isdigit() else -1

            src_doc.save(
                output_path,
                encryption=fitz.PDF_ENCRYPT_AES_256,
                user_pw=password,
                owner_pw=owner_password,
                permissions=perm_int,
                garbage=4,
                deflate=True,
            )
        except ConversionError:
            raise
        except Exception as exc:
            logger.error("PdfProtectEngine failed: %s", exc)
            raise ConversionError("pdf_protect_failed: Failed to protect PDF document.") from exc
        finally:
            src_doc.close()

        # Redact plaintext password fields from options
        for pw_key in ("password", "user_password", "owner_password"):
            if pw_key in opts:
                opts[pw_key] = "[REDACTED]"

        validate_pdf_output(output_path, allow_encrypted=True)

        check_doc = fitz.open(output_path)
        try:
            if not check_doc.is_encrypted:
                raise ConversionError("pdf_protect_failed: Output PDF file is not encrypted.")
            auth_result = check_doc.authenticate(password)
            if auth_result == 0:
                raise ConversionError("pdf_protect_failed: Output PDF password verification failed.")
        finally:
            check_doc.close()

        return output_path


# ── PDF Password Unlock Engine ────────────────────────────────────────────────

class PdfUnlockEngine(BaseConversionEngine):
    source_format = FORMAT_PDF
    target_format = FORMAT_PDF
    operation = "pdf_unlock"
    output_extension = ".pdf"
    mime_type = "application/pdf"

    def convert(self, input_path: str, output_path: str, options: dict | None = None) -> str | None:
        opts = options if options is not None else {}
        password = opts.get("password") or opts.get("user_password")

        docs = validate_pdf_utility_input(input_path, min_files=1, max_files=1, allow_encrypted=True)
        src_doc = docs[0]

        try:
            if src_doc.is_encrypted:
                if not password or not isinstance(password, str):
                    raise ConversionError("password_required: Password is required to unlock this encrypted PDF.")

                auth_result = src_doc.authenticate(password)
                if auth_result == 0:
                    raise ConversionError("invalid_password: The provided password is incorrect for this encrypted PDF.")

            out_dir = Path(output_path).parent
            out_dir.mkdir(parents=True, exist_ok=True)

            src_doc.save(output_path, garbage=4, deflate=True)
        except ConversionError:
            raise
        except Exception as exc:
            logger.error("PdfUnlockEngine failed: %s", exc)
            raise ConversionError("pdf_unlock_failed: Failed to unlock PDF document.") from exc
        finally:
            src_doc.close()

        # Redact plaintext password fields
        for pw_key in ("password", "user_password", "owner_password"):
            if pw_key in opts:
                opts[pw_key] = "[REDACTED]"

        validate_pdf_output(output_path, allow_encrypted=False)

        check_doc = fitz.open(output_path)
        try:
            if check_doc.is_encrypted:
                raise ConversionError("pdf_unlock_failed: Output PDF is still encrypted.")
        finally:
            check_doc.close()

        return output_path


# ── PDF Metadata Editor Engine ────────────────────────────────────────────────

class PdfMetadataEngine(BaseConversionEngine):
    source_format = FORMAT_PDF
    target_format = FORMAT_PDF
    operation = "pdf_metadata"
    output_extension = ".pdf"
    mime_type = "application/pdf"

    ALLOWED_FIELDS = ("title", "author", "subject", "keywords", "creator", "producer")

    def convert(self, input_path: str, output_path: str, options: dict | None = None) -> str | None:
        opts = options if options is not None else {}
        mode = str(opts.get("mode", "write")).lower().strip()
        if mode not in ("read", "write"):
            raise ConversionError(f"invalid_mode: Invalid metadata mode '{mode}'. Must be 'read' or 'write'.")

        docs = validate_pdf_utility_input(input_path, min_files=1, max_files=1)
        src_doc = docs[0]
        total_pages = len(src_doc)

        try:
            existing_meta = src_doc.metadata or {}

            if mode == "write":
                updated_meta = dict(existing_meta)
                for field in self.ALLOWED_FIELDS:
                    if field in opts:
                        val = opts.get(field)
                        if val is None:
                            val = ""
                        val_str = str(val).strip()
                        if len(val_str) > 500:
                            raise ConversionError(f"metadata_field_too_long: Metadata field '{field}' exceeds max length of 500 characters.")
                        val_str = "".join(c for c in val_str if ord(c) >= 32 or c in "\n\r\t")
                        updated_meta[field] = val_str

                src_doc.set_metadata(updated_meta)

            out_dir = Path(output_path).parent
            out_dir.mkdir(parents=True, exist_ok=True)
            src_doc.save(output_path, garbage=4, deflate=True)
        except ConversionError:
            raise
        except Exception as exc:
            logger.error("PdfMetadataEngine failed: %s", exc)
            raise ConversionError("pdf_metadata_failed: Failed to process PDF metadata.") from exc
        finally:
            src_doc.close()

        validate_pdf_output(output_path)

        out_doc = fitz.open(output_path)
        try:
            if len(out_doc) != total_pages:
                raise ConversionError("corrupted_pdf: PDF page count changed during metadata processing.")
            meta_result = dict(out_doc.metadata or {})
            opts["result_metadata"] = {
                "mode": mode,
                "title": meta_result.get("title", ""),
                "author": meta_result.get("author", ""),
                "subject": meta_result.get("subject", ""),
                "keywords": meta_result.get("keywords", ""),
                "creator": meta_result.get("creator", ""),
                "producer": meta_result.get("producer", ""),
            }
        finally:
            out_doc.close()

        return output_path


# ── PDF Page Numbering Engine ─────────────────────────────────────────────────

class PdfPageNumbersEngine(BaseConversionEngine):
    source_format = FORMAT_PDF
    target_format = FORMAT_PDF
    operation = "pdf_page_numbers"
    output_extension = ".pdf"
    mime_type = "application/pdf"

    def convert(self, input_path: str, output_path: str, options: dict | None = None) -> str | None:
        opts = options if options is not None else {}
        raw_scope = opts.get("scope", "all")
        scope = str(raw_scope).lower().strip() if raw_scope else "all"
        if scope not in ("all", "selected"):
            raise ConversionError(f"invalid_scope: Invalid scope '{raw_scope}'. Must be 'all' or 'selected'.")

        pages_expr = opts.get("pages")
        if scope == "selected" and not pages_expr:
            raise ConversionError("pages_required: Page range selection 'pages' is required when scope is 'selected'.")

        position = str(opts.get("position", "bottom-center")).lower().strip()
        valid_positions = ("top-left", "top-center", "top-right", "bottom-left", "bottom-center", "bottom-right")
        if position not in valid_positions:
            raise ConversionError(f"invalid_position: Position must be one of {', '.join(valid_positions)}.")

        try:
            start_number = int(opts.get("start_number", 1))
        except (ValueError, TypeError):
            raise ConversionError("invalid_start_number: start_number must be an integer >= 1.")
        if start_number < 1:
            raise ConversionError("invalid_start_number: start_number must be an integer >= 1.")

        prefix = str(opts.get("prefix", ""))
        suffix = str(opts.get("suffix", ""))
        if len(prefix) > 50 or len(suffix) > 50:
            raise ConversionError("text_too_long: Prefix and suffix strings must not exceed 50 characters.")

        format_style = str(opts.get("format_style", "number")).lower().strip()
        if format_style not in ("number", "total"):
            format_style = "number"

        try:
            font_size = float(opts.get("font_size", 10.0))
        except (ValueError, TypeError):
            raise ConversionError("invalid_font_size: Font size must be a number.")
        if font_size < 8.0 or font_size > 72.0:
            raise ConversionError(f"invalid_font_size: Font size {font_size} is out of bounds [8, 72].")

        hex_color = str(opts.get("color", "#000000")).strip()
        color_tuple = PdfWatermarkEngine._parse_hex_color(hex_color)

        docs = validate_pdf_utility_input(input_path, min_files=1, max_files=1)
        src_doc = docs[0]
        total_pages = len(src_doc)

        try:
            if scope == "all":
                target_indices = list(range(total_pages))
            else:
                target_indices = parse_page_range(pages_expr, total_pages, allow_duplicates=False)

            for order_idx, page_idx in enumerate(target_indices):
                page = src_doc[page_idx]
                rect = page.rect
                w, h = rect.width, rect.height

                curr_num = start_number + order_idx
                if format_style == "total":
                    label_text = f"{prefix}{curr_num} of {total_pages}{suffix}"
                else:
                    label_text = f"{prefix}{curr_num}{suffix}".replace("{total}", str(total_pages))

                if position == "top-left":
                    pt = fitz.Point(rect.x0 + 36, rect.y0 + 24)
                elif position == "top-center":
                    pt = fitz.Point(rect.x0 + w / 2, rect.y0 + 24)
                elif position == "top-right":
                    pt = fitz.Point(rect.x0 + w - 36, rect.y0 + 24)
                elif position == "bottom-left":
                    pt = fitz.Point(rect.x0 + 36, rect.y0 + h - 24)
                elif position == "bottom-right":
                    pt = fitz.Point(rect.x0 + w - 36, rect.y0 + h - 24)
                else:  # bottom-center
                    pt = fitz.Point(rect.x0 + w / 2, rect.y0 + h - 24)

                page.insert_text(
                    pt,
                    label_text,
                    fontsize=font_size,
                    color=color_tuple,
                    overlay=True,
                )

            out_dir = Path(output_path).parent
            out_dir.mkdir(parents=True, exist_ok=True)
            src_doc.save(output_path, garbage=4, deflate=True)
        except ConversionError:
            raise
        except Exception as exc:
            logger.error("PdfPageNumbersEngine failed: %s", exc)
            raise ConversionError("pdf_page_numbers_failed: Failed to add page numbers to PDF.") from exc
        finally:
            src_doc.close()

        validate_pdf_output(output_path)
        return output_path


# ── PDF Repair & Validation Engine ────────────────────────────────────────────

class PdfRepairEngine(BaseConversionEngine):
    source_format = FORMAT_PDF
    target_format = FORMAT_PDF
    operation = "pdf_repair"
    output_extension = ".pdf"
    mime_type = "application/pdf"

    def convert(self, input_path: str, output_path: str, options: dict | None = None) -> str | None:
        opts = options if options is not None else {}

        docs = validate_pdf_utility_input(input_path, min_files=1, max_files=1)
        src_doc = docs[0]
        initial_page_count = len(src_doc)
        initial_rects = [src_doc[i].rect for i in range(initial_page_count)]

        try:
            out_dir = Path(output_path).parent
            out_dir.mkdir(parents=True, exist_ok=True)

            # Rebuild document structure safely
            src_doc.save(output_path, garbage=4, deflate=True, clean=True)
            repair_status = "valid"
        except Exception as exc:
            logger.error("PdfRepairEngine failed: %s", exc)
            raise ConversionError("pdf_repair_failed: PDF is irrecoverably corrupt and cannot be repaired.") from exc
        finally:
            src_doc.close()

        validate_pdf_output(output_path)

        out_doc = fitz.open(output_path)
        try:
            final_page_count = len(out_doc)
            if final_page_count != initial_page_count:
                raise ConversionError(f"repair_validation_failed: Repaired PDF page count ({final_page_count}) differs from original ({initial_page_count}).")

            for idx in range(final_page_count):
                in_r = initial_rects[idx]
                out_r = out_doc[idx].rect
                if abs(in_r.width - out_r.width) > 1.0 or abs(in_r.height - out_r.height) > 1.0:
                    raise ConversionError(f"repair_validation_failed: Page {idx+1} dimensions altered during repair.")
                _ = out_doc[idx].get_text()

            opts["result_metadata"] = {
                "repair_status": repair_status,
                "initial_page_count": initial_page_count,
                "final_page_count": final_page_count,
            }
        finally:
            out_doc.close()

        return output_path
