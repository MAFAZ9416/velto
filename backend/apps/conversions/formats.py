"""
Supported file formats and format-pair definitions for VELTO Conversion.

This is the single source of truth for:
  - Which source formats exist.
  - Which target formats exist.
  - Which (source → target) conversions are valid.
  - Which MIME types are allowed for each source format.
  - Friendly display labels.

Adding a new supported conversion is a one-line change to SUPPORTED_PAIRS.
"""

# ── Format identifiers (internal keys) ────────────────────────────────────────
# These are stored in the database; do not rename without a migration.

FORMAT_PDF = "pdf"
FORMAT_DOCX = "docx"
FORMAT_XLSX = "xlsx"
FORMAT_PPTX = "pptx"
FORMAT_JPG = "jpg"
FORMAT_PNG = "png"
FORMAT_CSV = "csv"
FORMAT_WEBP = "webp"
FORMAT_BMP = "bmp"
FORMAT_TIFF = "tiff"
FORMAT_GIF = "gif"
FORMAT_ZIP = "zip"
FORMAT_TXT = "txt"
FORMAT_HTML = "html"
FORMAT_MD = "md"

# ── Human-readable labels ──────────────────────────────────────────────────────
FORMAT_LABELS = {
    FORMAT_PDF: "PDF",
    FORMAT_DOCX: "Word (DOCX)",
    FORMAT_XLSX: "Excel (XLSX)",
    FORMAT_PPTX: "PowerPoint (PPTX)",
    FORMAT_JPG: "JPG Image",
    FORMAT_PNG: "PNG Image",
    FORMAT_CSV: "CSV Document",
    FORMAT_WEBP: "WebP Image",
    FORMAT_BMP: "BMP Image",
    FORMAT_TIFF: "TIFF Image",
    FORMAT_GIF: "GIF Image",
    FORMAT_ZIP: "ZIP Archive",
    FORMAT_TXT: "Text File (TXT)",
    FORMAT_HTML: "HTML Document",
    FORMAT_MD: "Markdown Document",
}

# ── Django field choices ───────────────────────────────────────────────────────
FORMAT_CHOICES = [(k, v) for k, v in FORMAT_LABELS.items()]

# ── Allowed MIME types per source format ──────────────────────────────────────
# Used to validate uploaded files at the API boundary.
ALLOWED_MIME_TYPES: dict[str, list[str]] = {
    FORMAT_PDF: ["application/pdf"],
    FORMAT_DOCX: [
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    ],
    FORMAT_XLSX: [
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
    ],
    FORMAT_PPTX: [
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/vnd.ms-powerpoint",
    ],
    FORMAT_JPG: ["image/jpeg", "image/pjpeg"],
    FORMAT_PNG: ["image/png"],
    FORMAT_CSV: ["text/csv", "text/plain", "application/csv"],
    FORMAT_WEBP: ["image/webp"],
    FORMAT_BMP: ["image/bmp", "image/x-ms-bmp"],
    FORMAT_TIFF: ["image/tiff"],
    FORMAT_GIF: ["image/gif"],
    FORMAT_ZIP: ["application/zip", "application/x-zip-compressed"],
    FORMAT_TXT: ["text/plain"],
    FORMAT_HTML: ["text/html", "application/xhtml+xml"],
    FORMAT_MD: ["text/markdown", "text/x-markdown", "text/plain"],
}

# ── Allowed file extensions per source format ──────────────────────────────────
ALLOWED_EXTENSIONS: dict[str, list[str]] = {
    FORMAT_PDF: [".pdf"],
    FORMAT_DOCX: [".docx", ".doc"],
    FORMAT_XLSX: [".xlsx", ".xls"],
    FORMAT_PPTX: [".pptx", ".ppt"],
    FORMAT_JPG: [".jpg", ".jpeg"],
    FORMAT_PNG: [".png"],
    FORMAT_CSV: [".csv"],
    FORMAT_WEBP: [".webp"],
    FORMAT_BMP: [".bmp"],
    FORMAT_TIFF: [".tiff", ".tif"],
    FORMAT_GIF: [".gif"],
    FORMAT_ZIP: [".zip"],
    FORMAT_TXT: [".txt"],
    FORMAT_HTML: [".html", ".htm"],
    FORMAT_MD: [".md", ".markdown"],
}

# ── Valid conversion pairs (source_format, target_format) ─────────────────────
# Order determines display order in the API response.
SUPPORTED_PAIRS: list[tuple[str, str]] = [
    (FORMAT_PDF, FORMAT_DOCX),
    (FORMAT_DOCX, FORMAT_PDF),
    (FORMAT_PDF, FORMAT_XLSX),
    (FORMAT_XLSX, FORMAT_PDF),
    (FORMAT_PDF, FORMAT_PPTX),
    (FORMAT_PPTX, FORMAT_PDF),
    (FORMAT_PDF, FORMAT_JPG),
    (FORMAT_PDF, FORMAT_PNG),
    (FORMAT_DOCX, FORMAT_JPG),
    (FORMAT_DOCX, FORMAT_PNG),
    (FORMAT_PPTX, FORMAT_JPG),
    (FORMAT_PPTX, FORMAT_PNG),
    (FORMAT_XLSX, FORMAT_JPG),
    (FORMAT_XLSX, FORMAT_PNG),
    (FORMAT_CSV, FORMAT_XLSX),
    (FORMAT_CSV, FORMAT_PDF),
    (FORMAT_CSV, FORMAT_JPG),
    (FORMAT_CSV, FORMAT_PNG),
    (FORMAT_JPG, FORMAT_PDF),
    (FORMAT_PNG, FORMAT_PDF),
    (FORMAT_JPG, FORMAT_PNG),
    (FORMAT_PNG, FORMAT_JPG),
    (FORMAT_JPG, FORMAT_WEBP),
    (FORMAT_PNG, FORMAT_WEBP),
    (FORMAT_WEBP, FORMAT_JPG),
    (FORMAT_WEBP, FORMAT_PNG),
    (FORMAT_BMP, FORMAT_PNG),
    (FORMAT_BMP, FORMAT_JPG),
    (FORMAT_TIFF, FORMAT_PNG),
    (FORMAT_TIFF, FORMAT_JPG),
    (FORMAT_GIF, FORMAT_PNG),
    (FORMAT_GIF, FORMAT_JPG),
    (FORMAT_JPG, FORMAT_JPG),
    (FORMAT_PNG, FORMAT_PNG),
    (FORMAT_WEBP, FORMAT_WEBP),
    (FORMAT_JPG, FORMAT_ZIP),
    (FORMAT_PNG, FORMAT_ZIP),
    (FORMAT_WEBP, FORMAT_ZIP),
    (FORMAT_TXT, FORMAT_PDF),
    (FORMAT_TXT, FORMAT_DOCX),
    (FORMAT_HTML, FORMAT_PDF),
    (FORMAT_HTML, FORMAT_DOCX),
    (FORMAT_MD, FORMAT_PDF),
    (FORMAT_MD, FORMAT_DOCX),
]


# ── Derived helpers ────────────────────────────────────────────────────────────

# Set of all source formats that appear in at least one pair
VALID_SOURCE_FORMATS: set[str] = {src for src, _ in SUPPORTED_PAIRS}

# Set of all target formats that appear in at least one pair
VALID_TARGET_FORMATS: set[str] = {tgt for _, tgt in SUPPORTED_PAIRS}

# Fast O(1) membership test
SUPPORTED_PAIRS_SET: set[tuple[str, str]] = set(SUPPORTED_PAIRS)


def is_valid_conversion(source_format: str, target_format: str) -> bool:
    """Return True if the given source→target pair is supported."""
    return (source_format, target_format) in SUPPORTED_PAIRS_SET


def get_supported_formats_response() -> list[dict]:
    """
    Build the list of dicts returned by GET /api/conversions/supported-formats/.
    """
    return [
        {
            "source_format": src,
            "source_label": FORMAT_LABELS[src],
            "target_format": tgt,
            "target_label": FORMAT_LABELS[tgt],
        }
        for src, tgt in SUPPORTED_PAIRS
    ]

