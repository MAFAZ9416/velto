"""
OCR Conversion Engines for VELTO Conversion.

Operations Implemented:
  - ocr_image_to_searchable_pdf      (Image -> PDF with searchable text layer)
  - ocr_image_to_txt                 (Image -> UTF-8 text file via OCR)
  - ocr_pdf_to_txt                   (PDF -> TXT using hybrid native + OCR strategy)
  - ocr_scanned_pdf_to_searchable_pdf (Scanned PDF -> PDF with searchable text layer)
"""

import logging
import os
from pathlib import Path
import tempfile

import fitz  # PyMuPDF
from PIL import Image

from apps.conversions.engines.base import BaseConversionEngine, ConversionError
from apps.conversions.engines.validators import (
    MAX_OCR_TEXT_OUTPUT_SIZE,
    validate_ocr_input,
    validate_output_file,
    validate_pdf_output,
)
from apps.conversions.formats import FORMAT_JPG, FORMAT_PDF, FORMAT_PNG, FORMAT_TXT
from apps.conversions.utils.ocr_helper import (
    configure_pytesseract,
    get_ocr_engine_info,
    validate_ocr_language,
)

logger = logging.getLogger(__name__)


# ── Helper: Safe pytesseract import & config ──────────────────────────────────

def _get_pytesseract():
    configure_pytesseract()
    try:
        import pytesseract
        return pytesseract
    except ImportError:
        raise ConversionError(
            "ocr_wrapper_missing: Python library 'pytesseract' is not installed."
        )


# ── 1. Image → Searchable PDF Engine ──────────────────────────────────────────

class OcrImageToSearchablePdfEngine(BaseConversionEngine):
    source_format = FORMAT_JPG
    target_format = FORMAT_PDF
    operation = "ocr_image_to_searchable_pdf"
    output_extension = ".pdf"
    mime_type = "application/pdf"

    def convert(self, input_path: str, output_path: str, options: dict | None = None) -> str | None:
        opts = options if options is not None else {}
        validate_ocr_input(input_path, is_pdf=False, options=opts)
        validated_lang = validate_ocr_language(opts.get("language"))

        pytesseract = _get_pytesseract()

        dpi = int(opts.get("dpi", 300))
        psm = int(opts.get("page_segmentation_mode", opts.get("psm", 3)))
        custom_config = f"--dpi {dpi} --psm {psm}"

        try:
            with Image.open(input_path) as img:
                # Convert palette or RGBA to RGB for PDF generation
                if img.mode not in ("RGB", "L"):
                    img_rgb = img.convert("RGB")
                else:
                    img_rgb = img

                pdf_bytes = pytesseract.image_to_pdf_or_hocr(
                    img_rgb,
                    lang=validated_lang,
                    config=custom_config,
                    extension="pdf",
                )

            out_dir = Path(output_path).parent
            out_dir.mkdir(parents=True, exist_ok=True)

            with open(output_path, "wb") as f:
                f.write(pdf_bytes)

        except ConversionError:
            raise
        except Exception as exc:
            logger.error("OcrImageToSearchablePdfEngine failed: %s", exc)
            raise ConversionError("ocr_processing_failed: Failed to generate searchable PDF from image.") from exc

        validate_pdf_output(output_path)

        # Confirm text layer searchability
        check_doc = fitz.open(output_path)
        try:
            extracted_text = check_doc[0].get_text() if len(check_doc) > 0 else ""
            has_searchable_text = bool(extracted_text and len(extracted_text.strip()) > 0)
        finally:
            check_doc.close()

        opts["result_metadata"] = {
            "language": validated_lang,
            "dpi": dpi,
            "psm": psm,
            "has_searchable_text": has_searchable_text,
        }

        return output_path


# ── 2. Image → TXT Engine ──────────────────────────────────────────────────────

class OcrImageToTxtEngine(BaseConversionEngine):
    source_format = FORMAT_JPG
    target_format = FORMAT_TXT
    operation = "ocr_image_to_txt"
    output_extension = ".txt"
    mime_type = "text/plain"

    def convert(self, input_path: str, output_path: str, options: dict | None = None) -> str | None:
        opts = options if options is not None else {}
        validate_ocr_input(input_path, is_pdf=False, options=opts)
        validated_lang = validate_ocr_language(opts.get("language"))

        pytesseract = _get_pytesseract()

        dpi = int(opts.get("dpi", 300))
        psm = int(opts.get("page_segmentation_mode", opts.get("psm", 3)))
        custom_config = f"--dpi {dpi} --psm {psm}"

        try:
            with Image.open(input_path) as img:
                if img.mode not in ("RGB", "L"):
                    img_rgb = img.convert("RGB")
                else:
                    img_rgb = img

                raw_text = pytesseract.image_to_string(
                    img_rgb,
                    lang=validated_lang,
                    config=custom_config,
                )

            clean_text = raw_text if raw_text else ""

            out_dir = Path(output_path).parent
            out_dir.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(clean_text)

        except ConversionError:
            raise
        except Exception as exc:
            logger.error("OcrImageToTxtEngine failed: %s", exc)
            raise ConversionError("ocr_processing_failed: Failed to extract text from image.") from exc

        validate_output_file(output_path)

        out_size = Path(output_path).stat().st_size
        if out_size > MAX_OCR_TEXT_OUTPUT_SIZE:
            raise ConversionError(f"file_size_exceeded: Generated text file ({out_size} bytes) exceeds safety limit.")

        opts["result_metadata"] = {
            "language": validated_lang,
            "dpi": dpi,
            "psm": psm,
            "text_length": len(clean_text),
            "image_count": 1,
            "has_text": bool(clean_text.strip()),
        }

        return output_path


# ── 3. PDF → TXT Engine (Hybrid Strategy) ──────────────────────────────────────

class OcrPdfToTxtEngine(BaseConversionEngine):
    source_format = FORMAT_PDF
    target_format = FORMAT_TXT
    operation = "ocr_pdf_to_txt"
    output_extension = ".txt"
    mime_type = "text/plain"

    def convert(self, input_path: str, output_path: str, options: dict | None = None) -> str | None:
        opts = options if options is not None else {}
        validate_ocr_input(input_path, is_pdf=True, options=opts)

        dpi = int(opts.get("dpi", 300))
        psm = int(opts.get("page_segmentation_mode", opts.get("psm", 3)))
        custom_config = f"--dpi {dpi} --psm {psm}"

        doc = fitz.open(input_path)
        total_pages = len(doc)
        native_count = 0
        ocr_count = 0
        page_chunks = []

        validated_lang = None

        try:
            for idx in range(total_pages):
                page = doc[idx]
                native_text = page.get_text()

                if native_text and len(native_text.strip()) >= 20:
                    page_text = native_text
                    native_count += 1
                else:
                    if validated_lang is None:
                        validated_lang = validate_ocr_language(opts.get("language"))
                    pytesseract = _get_pytesseract()

                    pix = page.get_pixmap(dpi=dpi)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    ocr_text = pytesseract.image_to_string(
                        img,
                        lang=validated_lang,
                        config=custom_config,
                    )
                    page_text = ocr_text if ocr_text else ""
                    ocr_count += 1

                page_header = f"--- Page {idx + 1} ---\n"
                page_chunks.append(f"{page_header}{page_text.strip()}\n")

            full_text = "\n".join(page_chunks)

            out_dir = Path(output_path).parent
            out_dir.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(full_text)

        except ConversionError:
            raise
        except Exception as exc:
            logger.error("OcrPdfToTxtEngine failed: %s", exc)
            raise ConversionError("ocr_processing_failed: Failed to extract text from PDF document.") from exc
        finally:
            doc.close()

        validate_output_file(output_path)

        out_size = Path(output_path).stat().st_size
        if out_size > MAX_OCR_TEXT_OUTPUT_SIZE:
            raise ConversionError(f"file_size_exceeded: Generated text file ({out_size} bytes) exceeds safety limit.")

        opts["result_metadata"] = {
            "language": validated_lang or opts.get("language", "eng"),
            "total_pages": total_pages,
            "native_pages_count": native_count,
            "ocr_pages_count": ocr_count,
            "text_length": len(full_text),
        }

        return output_path


# ── 4. Scanned PDF → Searchable PDF Engine ────────────────────────────────────

class OcrScannedPdfToSearchablePdfEngine(BaseConversionEngine):
    source_format = FORMAT_PDF
    target_format = FORMAT_PDF
    operation = "ocr_scanned_pdf_to_searchable_pdf"
    output_extension = ".pdf"
    mime_type = "application/pdf"

    def convert(self, input_path: str, output_path: str, options: dict | None = None) -> str | None:
        opts = options if options is not None else {}
        validate_ocr_input(input_path, is_pdf=True, options=opts)

        dpi = int(opts.get("dpi", 300))
        psm = int(opts.get("page_segmentation_mode", opts.get("psm", 3)))
        custom_config = f"--dpi {dpi} --psm {psm}"

        src_doc = fitz.open(input_path)
        total_pages = len(src_doc)
        out_doc = fitz.open()

        scanned_count = 0
        native_count = 0
        validated_lang = None

        try:
            for idx in range(total_pages):
                page = src_doc[idx]
                native_text = page.get_text()

                if native_text and len(native_text.strip()) >= 20:
                    # Preserve native page with existing text & layout
                    out_doc.insert_pdf(src_doc, from_page=idx, to_page=idx)
                    native_count += 1
                else:
                    if validated_lang is None:
                        validated_lang = validate_ocr_language(opts.get("language"))
                    pytesseract = _get_pytesseract()

                    pix = page.get_pixmap(dpi=dpi)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

                    page_pdf_bytes = pytesseract.image_to_pdf_or_hocr(
                        img,
                        lang=validated_lang,
                        config=custom_config,
                        extension="pdf",
                    )

                    page_pdf = fitz.open("pdf", page_pdf_bytes)
                    out_doc.insert_pdf(page_pdf)
                    page_pdf.close()
                    scanned_count += 1

            out_dir = Path(output_path).parent
            out_dir.mkdir(parents=True, exist_ok=True)
            out_doc.save(output_path, garbage=4, deflate=True)

        except ConversionError:
            raise
        except Exception as exc:
            logger.error("OcrScannedPdfToSearchablePdfEngine failed: %s", exc)
            raise ConversionError("ocr_processing_failed: Failed to generate searchable PDF from scanned PDF.") from exc
        finally:
            src_doc.close()
            out_doc.close()

        validate_pdf_output(output_path)

        # Confirm output page count and text searchability
        check_doc = fitz.open(output_path)
        try:
            if len(check_doc) != total_pages:
                raise ConversionError(f"corrupted_pdf: Output page count ({len(check_doc)}) does not match input page count ({total_pages}).")
            searchable_text = check_doc[0].get_text() if len(check_doc) > 0 else ""
            has_text = bool(searchable_text and len(searchable_text.strip()) > 0)
        finally:
            check_doc.close()

        opts["result_metadata"] = {
            "language": validated_lang or opts.get("language", "eng"),
            "total_pages": total_pages,
            "scanned_pages_ocred": scanned_count,
            "native_pages_preserved": native_count,
            "has_searchable_text": has_text,
        }

        return output_path
