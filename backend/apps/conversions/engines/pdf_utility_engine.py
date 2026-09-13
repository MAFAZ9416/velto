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

