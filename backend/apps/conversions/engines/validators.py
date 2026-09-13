"""
File-level validators for uploaded files.

These run BEFORE any conversion engine touches the file.
They are intentionally kept separate from Django serializer validation
so they can be used independently (e.g. from the service layer or tests).
"""

import logging
import os
from pathlib import Path

from apps.conversions.engines.base import ConversionError

logger = logging.getLogger(__name__)

# ── PDF magic bytes ────────────────────────────────────────────────────────────
# The first 4 bytes of every valid PDF are %PDF (hex: 25 50 44 46).
_PDF_MAGIC = b"%PDF"
_PDF_MAGIC_LEN = len(_PDF_MAGIC)


def validate_pdf_signature(path: str) -> None:
    """
    Verify that the file at `path` begins with the PDF magic bytes.

    This prevents:
    - Files renamed to .pdf that are not actually PDFs.
    - Files containing only whitespace or HTML error pages.
    - Zero-byte / corrupted uploads.

    Raises
    ------
    ConversionError
        If the file does not look like a valid PDF.
    """
    p = Path(path)

    if not p.exists():
        raise ConversionError("The uploaded file does not exist.")

    if p.stat().st_size == 0:
        raise ConversionError("Input file is empty (0 bytes).")

    try:
        with open(path, "rb") as f:
            header = f.read(_PDF_MAGIC_LEN)
    except OSError as exc:
        logger.warning("Cannot read input PDF file at %s: %s", path, exc)
        raise ConversionError("Cannot read the uploaded file.") from exc

    if header != _PDF_MAGIC:
        raise ConversionError(
            "The uploaded file does not appear to be a valid PDF. "
            "Expected file header '%PDF' was not found. "
            "Please upload an unencrypted, standards-compliant PDF."
        )


def validate_docx_signature(path: str) -> None:
    """
    Verify that the file at `path` is a valid DOCX document.

    Checks:
    - File exists and is non-empty.
    - File is a valid ZIP archive.
    - File contains 'word/document.xml'.

    Raises
    ------
    ConversionError
        If the file does not appear to be a valid DOCX document.
    """
    import zipfile
    p = Path(path)

    if not p.exists():
        raise ConversionError("The uploaded DOCX file does not exist.")


    if p.stat().st_size == 0:
        raise ConversionError("Input file is empty (0 bytes).")

    try:
        with zipfile.ZipFile(path, "r") as zf:
            if zf.testzip() is not None:
                raise ConversionError(
                    "The uploaded file does not appear to be a valid DOCX document."
                )
            if "word/document.xml" not in zf.namelist():
                raise ConversionError(
                    "The uploaded file does not appear to be a valid DOCX document."
                )
    except ConversionError:
        raise
    except Exception as exc:
        logger.warning("DOCX validation failed for %s: %s", path, exc)
        raise ConversionError(
            "The uploaded file does not appear to be a valid DOCX document."
        ) from exc


def validate_pptx_signature(path: str) -> None:
    """
    Verify that the file at `path` is a valid PPTX document.

    Checks:
    - File exists and is non-empty.
    - File is a valid ZIP archive.
    - File contains 'ppt/presentation.xml'.

    Raises
    ------
    ConversionError
        If the file does not appear to be a valid PPTX document.
    """
    import zipfile
    p = Path(path)

    if not p.exists():
        raise ConversionError("The uploaded PPTX file does not exist.")

    if p.stat().st_size == 0:
        raise ConversionError("Input file is empty (0 bytes).")

    try:
        with zipfile.ZipFile(path, "r") as zf:
            if zf.testzip() is not None:
                raise ConversionError(
                    "The uploaded file does not appear to be a valid PPTX document."
                )
            if "ppt/presentation.xml" not in zf.namelist():
                raise ConversionError(
                    "The uploaded file does not appear to be a valid PPTX document."
                )
    except ConversionError:
        raise
    except Exception as exc:
        logger.warning("PPTX validation failed for %s: %s", path, exc)
        raise ConversionError(
            "The uploaded file does not appear to be a valid PPTX document."
        ) from exc


def validate_xlsx_signature(path: str) -> None:
    """
    Verify that the file at `path` is a valid XLSX document.

    Checks:
    - File exists and is non-empty.
    - File is a valid ZIP archive.
    - File contains 'xl/workbook.xml'.

    Raises
    ------
    ConversionError
        If the file does not appear to be a valid XLSX document.
    """
    import zipfile
    p = Path(path)

    if not p.exists():
        raise ConversionError("The uploaded XLSX file does not exist.")

    if p.stat().st_size == 0:
        raise ConversionError("Input file is empty (0 bytes).")

    try:
        with zipfile.ZipFile(path, "r") as zf:
            if zf.testzip() is not None:
                raise ConversionError(
                    "The uploaded file does not appear to be a valid XLSX document."
                )
            if "xl/workbook.xml" not in zf.namelist():
                raise ConversionError(
                    "The uploaded file does not appear to be a valid XLSX document."
                )
    except ConversionError:
        raise
    except Exception as exc:
        logger.warning("XLSX validation failed for %s: %s", path, exc)
        raise ConversionError(
            "The uploaded file does not appear to be a valid XLSX document."
        ) from exc


def validate_csv_signature(path: str) -> None:
    """
    Verify that the file at `path` is a valid, non-empty CSV document.

    Checks:
    - Path exists and is a file.
    - File is non-empty (>0 bytes).
    - File can be decoded using utf-8-sig, utf-8, or latin-1.

    Raises
    ------
    ConversionError
        If the file does not exist, is empty, or cannot be read/decoded.
    """
    p = Path(path)

    if not p.exists() or not p.is_file():
        raise ConversionError("The uploaded CSV file does not exist.")

    if p.stat().st_size == 0:
        raise ConversionError("Input file is empty (0 bytes).")

    try:
        with open(path, "rb") as f:
            raw_bytes = f.read(8192)

        decoded = None
        for encoding in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                decoded = raw_bytes.decode(encoding)
                break
            except UnicodeDecodeError:
                continue

        if decoded is None:
            raise ConversionError(
                "The uploaded file does not appear to be a valid CSV document."
            )
    except ConversionError:
        raise
    except Exception as exc:
        logger.warning("CSV validation failed for %s: %s", path, exc)
        raise ConversionError(
            "The uploaded file does not appear to be a valid CSV document."
        ) from exc




def validate_pdf_output(path: str) -> None:
    """
    Verify that `path` is a valid, non-empty PDF file containing at least 1 page.

    Raises
    ------
    ConversionError
        If output validation fails.
    """
    validate_output_file(path)
    validate_pdf_signature(path)

    try:
        import fitz
        doc = fitz.open(path)
        page_count = len(doc)
        doc.close()
        if page_count < 1:
            raise ConversionError("The generated PDF file is invalid or unreadable.")
    except ConversionError:
        raise
    except Exception as exc:
        logger.warning("PDF output validation failed for %s: %s", path, exc)
        raise ConversionError(
            "The generated PDF file is invalid or unreadable."
        ) from exc


def validate_output_file(path: str) -> None:
    """
    Verify that a conversion engine produced a non-empty output file.

    Raises
    ------
    ConversionError
        If the output file is missing or empty.
    """
    p = Path(path)
    if not p.exists():
        logger.error("Conversion engine did not produce output file at %s", path)
        raise ConversionError(
            "Conversion engine did not produce an output file."
        )
    size = p.stat().st_size
    if size == 0:
        raise ConversionError(
            "Conversion engine produced an empty output file. "
            "The PDF may be encrypted, password-protected, or contain only "
            "scanned images without embedded text."
        )
    logger.debug("Output file validated: %s (%d bytes)", path, size)


def validate_image_file(path: str, expected_format: str = "JPEG") -> None:
    """
    Verify that `path` is a valid, readable image of expected_format.

    Raises
    ------
    ConversionError
        If the file cannot be opened or is corrupted.
    """
    validate_output_file(path)
    try:
        from PIL import Image
        with Image.open(path) as img:
            img.verify()
    except Exception as exc:
        logger.warning("Image validation failed for %s: %s", path, exc)
        raise ConversionError(
            "The generated output image is invalid or corrupted."
        ) from exc


def validate_zip_archive(zip_path: str, expected_count: int, expected_ext: str) -> None:
    """
    Verify that `zip_path` is a valid, non-empty ZIP archive containing
    `expected_count` valid images ending with `expected_ext`.

    Raises
    ------
    ConversionError
        If the ZIP file is missing, corrupted, or has unexpected contents.
    """
    import io
    import zipfile
    from PIL import Image

    validate_output_file(zip_path)

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            corrupt = zf.testzip()
            if corrupt is not None:
                raise ConversionError(f"Corrupt file found in ZIP archive: {corrupt}")

            namelist = zf.namelist()
            if len(namelist) != expected_count:
                raise ConversionError(
                    f"ZIP archive contains {len(namelist)} items, expected {expected_count}."
                )

            ext = expected_ext.lower()
            for fname in namelist:
                if not fname.lower().endswith(ext):
                    raise ConversionError(
                        f"ZIP archive contains unexpected file extension: {fname} (expected {ext})"
                    )
                # Verify that every image inside the ZIP can be opened cleanly
                img_bytes = zf.read(fname)
                with Image.open(io.BytesIO(img_bytes)) as img:
                    img.verify()
    except ConversionError:
        raise
    except Exception as exc:
        logger.warning("ZIP archive validation failed for %s: %s", zip_path, exc)
        raise ConversionError(
            "The generated ZIP archive is invalid or corrupted."
        ) from exc



def validate_xlsx_workbook(xlsx_path: str) -> None:
    """
    Verify that `xlsx_path` is a valid, non-empty Excel (.xlsx) workbook.

    Validates:
      1. File exists and size > 0.
      2. File is a valid ZIP package (XLSX format requirement).
      3. Workbook can be opened cleanly by openpyxl.
      4. Workbook contains at least one sheet with non-empty cell data.

    Raises
    ------
    ConversionError
        If validation fails.
    """
    import zipfile
    validate_output_file(xlsx_path)

    # 1. Verify ZIP package
    try:
        with zipfile.ZipFile(xlsx_path, "r") as zf:
            if zf.testzip() is not None:
                raise ConversionError("Generated XLSX file is a corrupted ZIP package.")
    except Exception as exc:
        raise ConversionError(
            f"Generated XLSX file is not a valid ZIP package: {exc}"
        ) from exc

    # 2. Verify openpyxl can load the workbook
    try:
        import openpyxl
        wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
    except Exception as exc:
        raise ConversionError(
            f"Generated XLSX workbook could not be loaded by openpyxl: {exc}"
        ) from exc

    try:
        if not wb.sheetnames:
            raise ConversionError("Generated XLSX workbook contains no worksheets.")

        has_data = False
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            for row in ws.iter_rows(values_only=True):
                if any(v is not None and str(v).strip() != "" for v in row):
                    has_data = True
                    break
            if has_data:
                break

        if not has_data:
            raise ConversionError("Generated XLSX workbook contains no table cell data.")
    finally:
        wb.close()


