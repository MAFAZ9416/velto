"""
Page Range Parsing Service for VELTO Conversion PDF Utilities.

Parses human-readable 1-based page range expressions:
  - "1"
  - "1,3,5"
  - "1-4"
  - "2-5,8,10-12"

Converts 1-based API page numbers to 0-based internal document indices.
"""

import re
from apps.conversions.engines.base import ConversionError


def parse_page_range(range_expr: str | list | None, total_pages: int, allow_duplicates: bool = False) -> list[int]:
    """
    Parse a page range expression into a list of 0-based page indices.

    Parameters
    ----------
    range_expr : str | list | None
        Page selection input, e.g. "1-4,7,9-10" or ["1-3", "4-6"].
    total_pages : int
        Total number of pages in the target PDF document.
    allow_duplicates : bool, default False
        If False, raises ConversionError if duplicate page numbers are selected.

    Returns
    -------
    list[int]
        List of 0-based page indices in exact requested order.

    Raises
    ------
    ConversionError
        If range_expr is empty, malformed, out-of-bounds, reversed, or invalid.
    """
    if range_expr is None:
        raise ConversionError("page_range_invalid: Page range expression is required.")

    if isinstance(range_expr, (list, tuple)):
        # Join list of range strings with commas
        range_str = ",".join(str(item).strip() for item in range_expr)
    else:
        range_str = str(range_expr).strip()

    if not range_str:
        raise ConversionError("page_range_invalid: Empty page selection.")

    # Remove extra spaces around commas and dashes
    clean_expr = re.sub(r"\s*", "", range_str)

    # Validate characters (only digits, commas, and hyphens allowed)
    if not re.match(r"^[0-9,-]+$", clean_expr):
        raise ConversionError(f"page_range_invalid: Invalid characters in range expression '{range_str}'.")

    parts = clean_expr.split(",")
    indices = []
    seen = set()

    for part in parts:
        if not part:
            raise ConversionError(f"page_range_invalid: Empty segment in range expression '{range_str}'.")

        if "-" in part:
            # Handle range segment like "2-5"
            range_parts = part.split("-")
            if len(range_parts) != 2 or not range_parts[0] or not range_parts[1]:
                raise ConversionError(f"page_range_invalid: Malformed range segment '{part}'.")

            try:
                start_p = int(range_parts[0])
                end_p = int(range_parts[1])
            except ValueError:
                raise ConversionError(f"page_range_invalid: Invalid integers in range segment '{part}'.")

            if start_p < 1 or end_p < 1:
                raise ConversionError(f"page_range_invalid: Page numbers must be 1-based positive integers (got '{part}').")

            if start_p > end_p:
                raise ConversionError(f"page_range_invalid: Reversed range segment '{part}' (start page {start_p} > end page {end_p}).")

            if end_p > total_pages:
                raise ConversionError(f"page_count_exceeded: Selected page {end_p} exceeds total document page count ({total_pages}).")

            for p in range(start_p, end_p + 1):
                idx = p - 1
                if not allow_duplicates and idx in seen:
                    raise ConversionError(f"page_range_invalid: Duplicate page selection for page {p}.")
                seen.add(idx)
                indices.append(idx)
        else:
            # Handle single page number like "7"
            try:
                p = int(part)
            except ValueError:
                raise ConversionError(f"page_range_invalid: Invalid page number '{part}'.")

            if p < 1:
                raise ConversionError(f"page_range_invalid: Page number '{part}' must be a 1-based positive integer.")

            if p > total_pages:
                raise ConversionError(f"page_count_exceeded: Selected page {p} exceeds total document page count ({total_pages}).")

            idx = p - 1
            if not allow_duplicates and idx in seen:
                raise ConversionError(f"page_range_invalid: Duplicate page selection for page {p}.")
            seen.add(idx)
            indices.append(idx)

    if not indices:
        raise ConversionError("page_range_invalid: Page range selected zero pages.")

    return indices
