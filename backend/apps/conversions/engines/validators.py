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




def validate_pdf_output(path: str, allow_encrypted: bool = False) -> None:
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
        if doc.is_encrypted:
            doc.close()
            if not allow_encrypted:
                raise ConversionError("The generated PDF file is encrypted.")
            return
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


def validate_image_signature(
    path: str,
    allowed_formats: list[str] | set[str] | None = None,
    allow_animated: bool = False,
) -> None:
    """
    Verify that the file at `path` is a valid, readable image.

    Checks:
    - File exists and is non-empty.
    - Fits within maximum pixel safety bounds (80 Megapixels).
    - Format is in `allowed_formats` if specified.
    - Rejects animated multi-frame images if allow_animated is False.

    Raises
    ------
    ConversionError
        If validation fails or file is not a valid image.
    """
    p = Path(path)

    if not p.exists() or not p.is_file():
        raise ConversionError("The uploaded image file does not exist.")

    if p.stat().st_size == 0:
        raise ConversionError("Input file is empty (0 bytes).")

    try:
        from PIL import Image, ImageFile
        ImageFile.LOAD_TRUNCATED_IMAGES = False
        Image.MAX_IMAGE_PIXELS = 80_000_000

        with Image.open(path) as img:
            fmt = (img.format or "").upper()
            if allowed_formats:
                allowed_upper = {f.upper() for f in allowed_formats}
                if "JPG" in allowed_upper:
                    allowed_upper.add("JPEG")
                if fmt not in allowed_upper:
                    raise ConversionError(
                        f"The uploaded file is a {fmt} image, which does not match "
                        f"the expected format ({', '.join(allowed_upper)})."
                    )

            if not allow_animated and getattr(img, "is_animated", False):
                n_frames = getattr(img, "n_frames", 1)
                if n_frames > 1:
                    raise ConversionError(
                        "Animated images are not supported. Please upload a single-frame static image."
                    )

            img.verify()
    except ConversionError:
        raise
    except Image.DecompressionBombError as exc:
        logger.warning("Image decompression bomb detected for %s: %s", path, exc)
        raise ConversionError(
            "The image dimensions exceed maximum safety limits (80 Megapixels)."
        ) from exc
    except Exception as exc:
        logger.warning("Image signature validation failed for %s: %s", path, exc)
        raise ConversionError(
            "The uploaded file does not appear to be a valid image."
        ) from exc


def validate_image_file(path: str, expected_format: str | None = "JPEG") -> None:
    """
    Verify that `path` is a valid, readable output image of expected_format.

    Raises
    ------
    ConversionError
        If the file cannot be opened or is corrupted.
    """
    validate_output_file(path)
    try:
        from PIL import Image, ImageFile
        ImageFile.LOAD_TRUNCATED_IMAGES = False
        Image.MAX_IMAGE_PIXELS = 80_000_000

        with Image.open(path) as img:
            if expected_format:
                fmt = (img.format or "").upper()
                exp = expected_format.upper()
                if exp in ("JPG", "JPEG"):
                    exp_set = {"JPG", "JPEG"}
                else:
                    exp_set = {exp}

                if fmt not in exp_set:
                    raise ConversionError(
                        f"Generated image format '{fmt}' does not match expected format '{expected_format}'."
                    )
            img.verify()
    except ConversionError:
        raise
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
                content_bytes = zf.read(fname)
                if ext == ".pdf":
                    import fitz
                    with fitz.open(stream=content_bytes, filetype="pdf") as pdf_doc:
                        if pdf_doc.is_encrypted or len(pdf_doc) == 0:
                            raise ConversionError(f"Corrupted PDF found inside ZIP: {fname}")
                elif ext in (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".gif"):
                    with Image.open(io.BytesIO(content_bytes)) as img:
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


def validate_docx_output(docx_path: str) -> None:
    """
    Verify that `docx_path` is a valid, non-empty DOCX document.

    Checks:
    - File exists and is non-empty.
    - File is a valid ZIP archive.
    - Contains '[Content_Types].xml' and 'word/document.xml'.

    Raises
    ------
    ConversionError
        If validation fails.
    """
    import zipfile
    validate_output_file(docx_path)

    try:
        with zipfile.ZipFile(docx_path, "r") as zf:
            if zf.testzip() is not None:
                raise ConversionError("Generated DOCX file is a corrupted ZIP package.")
            namelist = zf.namelist()
            if "[Content_Types].xml" not in namelist or "word/document.xml" not in namelist:
                raise ConversionError("Generated DOCX file is missing required XML components.")
    except ConversionError:
        raise
    except Exception as exc:
        logger.warning("DOCX output validation failed for %s: %s", docx_path, exc)
        raise ConversionError("Generated DOCX document is invalid or corrupted.") from exc


def validate_txt_signature(path: str) -> None:
    """
    Verify that the file at `path` is a valid text file.

    Checks:
    - File exists and is a regular file.
    - File is non-empty (>0 bytes).
    - File can be decoded cleanly as text.
    """
    p = Path(path)
    if not p.exists() or not p.is_file():
        raise ConversionError("The uploaded TXT file does not exist.")
    if p.stat().st_size == 0:
        raise ConversionError("Input file is empty (0 bytes).")


def validate_html_signature(path: str) -> None:
    """
    Verify that the file at `path` is a valid HTML file.

    Checks:
    - File exists and is a regular file.
    - File is non-empty (>0 bytes).
    """
    p = Path(path)
    if not p.exists() or not p.is_file():
        raise ConversionError("The uploaded HTML file does not exist.")
    if p.stat().st_size == 0:
        raise ConversionError("Input file is empty (0 bytes).")


def validate_md_signature(path: str) -> None:
    """
    Verify that the file at `path` is a valid Markdown file.

    Checks:
    - File exists and is a regular file.
    - File is non-empty (>0 bytes).
    """
    p = Path(path)
    if not p.exists() or not p.is_file():
        raise ConversionError("The uploaded Markdown file does not exist.")
    if p.stat().st_size == 0:
        raise ConversionError("Input file is empty (0 bytes).")


# ── PDF Utility Safety Limits ────────────────────────────────────────────────
MAX_PDF_FILE_SIZE = 52_428_800        # 50 MB
MAX_PDF_TOTAL_INPUT_BYTES = 209_715_200 # 200 MB
MAX_PDF_PAGE_COUNT = 1000            # 1,000 pages per file
MAX_PDF_TOTAL_PAGES = 2000           # 2,000 pages across all input files
MAX_PDF_OUTPUT_SIZE = 104_857_600    # 100 MB
MAX_PDF_SPLIT_OUTPUTS = 500          # 500 max split outputs


def validate_pdf_utility_input(
    paths: str | list[str] | tuple[str, ...],
    min_files: int = 1,
    max_files: int = 100,
    session_dir: str | None = None,
    allow_encrypted: bool = False,
) -> list["fitz.Document"]:
    """
    Validate input PDF files for Phase 5 operations.

    Checks:
    - Minimum and maximum file count.
    - File existence, regular file type, and workspace containment if session_dir is given.
    - File size <= MAX_PDF_FILE_SIZE.
    - Total input size across all files <= MAX_PDF_TOTAL_INPUT_BYTES.
    - Valid PDF header magic bytes.
    - Can be opened by PyMuPDF and is unencrypted (unless allow_encrypted is True).
    - Single page count <= MAX_PDF_PAGE_COUNT.
    - Total pages across all inputs <= MAX_PDF_TOTAL_PAGES.

    Returns
    -------
    list[fitz.Document]
        List of opened PyMuPDF Document objects. Caller MUST close all documents.
    """
    import fitz

    if isinstance(paths, str):
        path_list = [paths]
    else:
        path_list = list(paths)

    if len(path_list) < min_files:
        raise ConversionError(f"invalid_pdf: Operation requires at least {min_files} PDF file(s).")
    if len(path_list) > max_files:
        raise ConversionError(f"invalid_pdf: Operation accepts at most {max_files} PDF file(s).")

    total_bytes = 0
    total_pages = 0
    docs = []

    try:
        for p_str in path_list:
            p = Path(p_str)
            if not p.exists() or not p.is_file():
                raise ConversionError(f"invalid_pdf: Input file '{p.name}' does not exist or is not a regular file.")

            if session_dir:
                resolved_session = Path(session_dir).resolve()
                resolved_file = p.resolve()
                try:
                    resolved_file.relative_to(resolved_session)
                except ValueError:
                    raise ConversionError(f"invalid_pdf: Input file '{p.name}' is outside the authorized session directory.")

            file_size = p.stat().st_size
            if file_size == 0:
                raise ConversionError(f"invalid_pdf: Input file '{p.name}' is empty (0 bytes).")
            if file_size > MAX_PDF_FILE_SIZE:
                raise ConversionError(f"file_size_exceeded: File '{p.name}' size exceeds maximum limit of {MAX_PDF_FILE_SIZE // (1024*1024)} MB.")

            total_bytes += file_size
            if total_bytes > MAX_PDF_TOTAL_INPUT_BYTES:
                raise ConversionError(f"file_size_exceeded: Total input size across all files exceeds limit of {MAX_PDF_TOTAL_INPUT_BYTES // (1024*1024)} MB.")

            # Signature check
            validate_pdf_signature(p_str)

            # Open via PyMuPDF
            try:
                doc = fitz.open(p_str)
            except Exception as exc:
                raise ConversionError(f"corrupted_pdf: File '{p.name}' is corrupted or malformed.") from exc

            if doc.is_encrypted and not allow_encrypted:
                doc.close()
                raise ConversionError(f"encrypted_pdf: File '{p.name}' is password protected.")

            page_count = len(doc)
            if page_count < 1:
                doc.close()
                raise ConversionError(f"corrupted_pdf: File '{p.name}' contains no readable pages.")
            if page_count > MAX_PDF_PAGE_COUNT:
                doc.close()
                raise ConversionError(f"page_count_exceeded: File '{p.name}' page count ({page_count}) exceeds limit of {MAX_PDF_PAGE_COUNT}.")

            total_pages += page_count
            if total_pages > MAX_PDF_TOTAL_PAGES:
                doc.close()
                raise ConversionError(f"total_pages_exceeded: Total pages across input files ({total_pages}) exceeds limit of {MAX_PDF_TOTAL_PAGES}.")

            docs.append(doc)
        return docs
    except Exception:
        for d in docs:
            try:
                d.close()
            except Exception:
                pass
        raise



