"""
PdfToXlsxEngine — converts tables extracted from a PDF into an Excel (.xlsx) workbook.

Features & Design
-----------------
1. Table Extraction Strategy:
   - Primary: PyMuPDF table finder (`page.find_tables()`).
   - Fallback: pdfplumber (`page.extract_tables()`).
2. Row & Cell Normalization:
   - Equalizes row lengths, handles missing/None cells and empty tables.
   - Cleans multi-line cell text.
3. Safe Value Parsing:
   - Preserves text for strings with leading zeroes (e.g. "01234"), account numbers,
     ZIP codes, dates, and hyphenated IDs so original data meaning is never lost.
   - Converts clean numeric strings to int or float.
4. Worksheet Naming:
   - One worksheet per PDF page containing tables ("Page 1", "Page 2", ...).
   - Sanitizes titles (max 31 characters, removes invalid characters `\\ / ? * : [ ]`).
   - Guarantees unique, deterministic sheet names.
5. Honest No-Table Policy:
   - If no extractable tables are detected across all pages, raises `ConversionError("No extractable tables were found in this PDF.")`.
"""

import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Any, List, Optional

from apps.conversions.engines.base import BaseConversionEngine, ConversionError
from apps.conversions.engines.validators import (
    validate_pdf_signature,
    validate_xlsx_workbook,
)

logger = logging.getLogger(__name__)

# Regex for Excel invalid sheet title characters: \ / ? * : [ ]
_INVALID_SHEET_CHARS = re.compile(r"[\\/*?:\[\]]")

# Regex to detect strings that look like pure numbers with leading zeros (e.g., "01234" vs "0")
_LEADING_ZERO_NUM = re.compile(r"^0\d+$")

# Regex for dates, IDs, zip codes (e.g. "2026-09-13", "12-345", "02138")
_DATE_OR_ID_PATTERN = re.compile(r"^\d{1,4}[-/.]\d{1,4}[-/.]\d{1,4}$")


def _sanitize_sheet_title(title: str, existing_names: set) -> str:
    """
    Sanitize and truncate sheet title to Excel limits (max 31 chars, no invalid chars).
    Ensures uniqueness within existing_names.
    """
    safe_title = _INVALID_SHEET_CHARS.sub("_", title).strip()
    if not safe_title:
        safe_title = "Sheet"

    # Truncate to 31 chars max
    safe_title = safe_title[:31]

    # Ensure uniqueness
    base = safe_title[:25]
    counter = 1
    candidate = safe_title
    while candidate.lower() in {name.lower() for name in existing_names}:
        suffix = f" ({counter})"
        candidate = f"{base}{suffix}"
        counter += 1

    existing_names.add(candidate)
    return candidate


def _parse_cell_value(val: Any) -> Any:
    """
    Safely parse cell value into numeric or string representation.

    Preserves text for:
      - None or empty string
      - Strings with leading zeros (e.g. "01234")
      - Hyphenated IDs or dates (e.g. "2026-09-13", "12-34-56")
      - Strings containing non-numeric characters (currency symbols, letters)
    """
    if val is None:
        return None

    if not isinstance(val, str):
        val = str(val)

    s = val.strip()
    if not s:
        return None

    # Replace internal carriage returns or vertical tabs with space
    s = s.replace("\r\n", "\n").replace("\r", "\n")

    # 1. Preserve leading-zero numbers (ZIP codes, account numbers)
    if _LEADING_ZERO_NUM.match(s):
        return s

    # 2. Preserve date/ID formats
    if _DATE_OR_ID_PATTERN.match(s):
        return s

    # 3. Try integer conversion
    try:
        if s.lstrip("-").isdigit():
            return int(s)
    except (ValueError, OverflowError):
        pass

    # 4. Try float conversion
    try:
        # Check standard float formatting (e.g. "-123.45")
        if re.match(r"^-?\d+\.\d+$", s):
            return float(s)
    except (ValueError, OverflowError):
        pass

    return s


def _extract_tables_pymupdf(doc) -> List[tuple[int, List[List[List[Any]]]]]:
    """
    Extract tables from a PyMuPDF Document using page.find_tables().
    Returns list of (page_num_1_based, [table_2d_rows, ...]).
    """
    page_tables = []
    for page_idx in range(len(doc)):
        page = doc.load_page(page_idx)
        tables_on_page = []

        # Inspect if find_tables is available and safe to call
        if hasattr(page, "find_tables"):
            try:
                tabs = page.find_tables()
                if hasattr(tabs, "tables") and tabs.tables:
                    for table in tabs.tables:
                        extracted = table.extract()
                        if extracted and any(row for row in extracted):
                            tables_on_page.append(extracted)
            except Exception as exc:
                logger.debug(
                    "PyMuPDF find_tables failed on page %d: %s", page_idx + 1, exc
                )

        if tables_on_page:
            page_tables.append((page_idx + 1, tables_on_page))

    return page_tables


def _extract_tables_pdfplumber(input_path: str) -> List[tuple[int, List[List[List[Any]]]]]:
    """
    Extract tables from a PDF using pdfplumber as fallback.
    Returns list of (page_num_1_based, [table_2d_rows, ...]).
    """
    try:
        import pdfplumber
    except ImportError:
        return []

    page_tables = []
    try:
        with pdfplumber.open(input_path) as pdf:
            for page_idx, page in enumerate(pdf.pages):
                extracted_tables = page.extract_tables()
                valid_tables = [
                    t for t in (extracted_tables or [])
                    if t and any(row for row in t)
                ]
                if valid_tables:
                    page_tables.append((page_idx + 1, valid_tables))
    except Exception as exc:
        logger.debug("pdfplumber table extraction failed: %s", exc)

    return page_tables


class PdfToXlsxEngine(BaseConversionEngine):
    """
    Converts PDF documents containing tables into Excel (.xlsx) workbooks.

    Attributes
    ----------
    source_format : str
        "pdf"
    target_format : str
        "xlsx"
    """

    source_format = "pdf"
    target_format = "xlsx"

    def convert(self, input_path: str, output_path: str) -> str | None:
        # ── Step 1: Validate input PDF header ─────────────────────────────────
        validate_pdf_signature(input_path)

        # ── Step 2: Import PyMuPDF & openpyxl ─────────────────────────────────
        try:
            import pymupdf
        except ImportError as exc:
            raise ConversionError(
                "PyMuPDF is not installed. Run: pip install pymupdf"
            ) from exc

        try:
            import openpyxl
        except ImportError as exc:
            raise ConversionError(
                "openpyxl is not installed. Run: pip install openpyxl"
            ) from exc

        # ── Step 3: Open PDF document ─────────────────────────────────────────
        doc = None
        try:
            doc = pymupdf.open(input_path)
        except Exception as exc:
            raise ConversionError(
                f"Failed to open PDF document. The file may be corrupt: {exc}"
            ) from exc

        try:
            if doc.is_encrypted:
                if not doc.authenticate(""):
                    raise ConversionError(
                        "The PDF is password-protected or encrypted. Please provide an unlocked PDF."
                    )

            if len(doc) == 0:
                raise ConversionError("The PDF contains no pages (0 pages).")

            # ── Step 4: Extract tables using PyMuPDF primary, pdfplumber fallback ─
            page_tables = _extract_tables_pymupdf(doc)

            # Fallback to pdfplumber if PyMuPDF returned no tables
            if not page_tables:
                page_tables = _extract_tables_pdfplumber(input_path)

            # Honest No-Table Check
            if not page_tables:
                raise ConversionError("No extractable tables were found in this PDF.")

            # ── Step 5: Build OpenPyXL Workbook ───────────────────────────────
            wb = openpyxl.Workbook()
            # Remove default initial sheet
            wb.remove(wb.active)

            existing_sheet_names = set()
            total_tables_written = 0

            for page_num, tables in page_tables:
                sheet_title = _sanitize_sheet_title(
                    f"Page {page_num}", existing_sheet_names
                )
                ws = wb.create_sheet(title=sheet_title)

                current_row = 1

                for table_idx, table_data in enumerate(tables):
                    if not table_data:
                        continue

                    # Equalize row lengths across table
                    max_cols = max((len(r) for r in table_data if r), default=0)
                    if max_cols == 0:
                        continue

                    # If writing multiple tables on the same page, add separating gap
                    if table_idx > 0:
                        current_row += 2  # Leave a blank row separator

                    table_has_content = False
                    for raw_row in table_data:
                        if not raw_row:
                            continue

                        # Pad shorter rows to max_cols
                        padded_row = list(raw_row) + [None] * (max_cols - len(raw_row))

                        # Parse values
                        parsed_row = [_parse_cell_value(cell) for cell in padded_row]

                        # Skip completely empty rows
                        if not any(c is not None for c in parsed_row):
                            continue

                        for col_idx, cell_value in enumerate(parsed_row, start=1):
                            if cell_value is not None:
                                ws.cell(
                                    row=current_row, column=col_idx, value=cell_value
                                )
                        current_row += 1
                        table_has_content = True

                    if table_has_content:
                        total_tables_written += 1

            if total_tables_written == 0:
                raise ConversionError("No extractable tables were found in this PDF.")

            # Ensure output directory exists
            out_p = Path(output_path)
            out_p.parent.mkdir(parents=True, exist_ok=True)

            wb.save(str(out_p))

            # ── Step 6: Validate output XLSX file ─────────────────────────────
            validate_xlsx_workbook(str(out_p))

            logger.info(
                "PdfToXlsxEngine: successfully converted PDF to XLSX (%d tables): %s",
                total_tables_written,
                out_p,
            )
            return str(out_p)

        finally:
            if doc is not None:
                try:
                    doc.close()
                except Exception:  # noqa: BLE001
                    pass
