# VELTO Conversion Backend

Production-oriented Django + DRF backend for the VELTO file conversion SaaS platform.

---

## Phase 4 — Document Conversion Phase (TXT, HTML, Markdown → PDF / DOCX)

Phase 4 introduces production-ready document conversion engines for plain text, HTML, and Markdown inputs to PDF and Word (DOCX) documents using a unified block tree representation pipeline:

* **TXT → PDF / DOCX**: Full UTF-8 and UTF-8 BOM decoding, CRLF/LF line ending normalization, blank line preservation, long-line automatic wrapping, multi-page layout, and Tamil/Unicode rendering.
* **HTML → PDF / DOCX**: Strict security-first HTML sanitization (stripping scripts, styles, iframes, embeds, event handlers, unsafe URL schemes, local file references, and remote network calls) with structured conversion of headings, paragraphs, lists, blockquotes, code blocks, and tables.
* **Markdown → PDF / DOCX**: Parsing GFM Markdown (headings, emphasis, ordered/unordered lists, blockquotes, code blocks, tables, horizontal rules, safe links) into sanitized document blocks.

### Supported Conversions & Status

| Feature | Status |
|---|---|
| Upload TXT, HTML, MD, PDF, DOCX, PPTX, XLSX, CSV, Images | ✅ |
| Convert TXT → PDF | ✅ Real ReportLab rendering |
| Convert TXT → DOCX | ✅ Real python-docx builder |
| Convert HTML → PDF | ✅ Sanitized block pipeline |
| Convert HTML → DOCX | ✅ Sanitized block pipeline |
| Convert Markdown → PDF | ✅ GFM Markdown parsing |
| Convert Markdown → DOCX | ✅ GFM Markdown parsing |
| Strict HTML/Markdown XSS & SSRF Security | ✅ Strips scripts, event handlers & dangerous URL schemes |
| Tamil & Unicode Font Registration | ✅ Automatic TTF font detection (Latha, Nirmala, Noto, Segoe UI) |
| Safety & Resource Limits | ✅ Enforces max upload (50MB), text length (5M chars), HTML elements (50k), PDF pages (500) |
| Convert PDF → Word (.docx), Excel (.xlsx), JPG, PNG | ✅ Real rendering |
| Convert Word (.docx) → PDF, JPG, PNG | ✅ Real LibreOffice / PyMuPDF |
| Convert PowerPoint (.pptx) → PDF, JPG, PNG | ✅ Real LibreOffice / PyMuPDF |
| Convert Excel (.xlsx) → PDF, JPG, PNG | ✅ Real LibreOffice / PyMuPDF |
| Convert CSV → XLSX, PDF, JPG, PNG | ✅ Real conversion |
| Convert Image formats (JPG, PNG, WEBP, BMP, TIFF, GIF, ZIP) | ✅ Real Pillow / ZIP engine |
| Download converted output via protected endpoint | ✅ |
| Session-based anonymous ownership & cross-session isolation | ✅ |
| Honest error responses & resource teardown | ✅ |
| 339+ automated tests | ✅ All passing |

---

## Document Engine Security & Safety Policy

1. **Input Encoding & Normalization**:
   - Tries `utf-8-sig` (stripping BOM cleanly) then `utf-8`.
   - Normalizes `\r\n` and `\r` line endings to standard `\n`.
2. **HTML Security Restrictions**:
   - Automatically strips disallowed tags: `<script>`, `<style>`, `<iframe>`, `<object>`, `<embed>`, `<meta>`, `<head>`, `<link>`, `<applet>`, `<base>`, `<form>`, `<input>`, `<button>`, `<textarea>`, `<select>`.
   - Strips all `on*` inline event handlers (e.g. `onclick`, `onerror`, `onload`).
   - Blocks unsafe link schemes (`javascript:`, `file:`, `data:`, `vbscript:`).
   - Blocks local filesystem paths (`C:\`, `/etc/`, `\\`).
   - Never executes JavaScript or fetches external remote network resources.
3. **Markdown Security**:
   - Passes rendered Markdown HTML through the security sanitization parser.
   - Raw HTML inside Markdown is sanitized against XSS/SSRF attacks.
4. **Tamil & Unicode Font Support**:
   - Detects system TrueType Unicode fonts (e.g., `Latha`, `Nirmala UI`, `Noto Sans Tamil`, `Segoe UI`) and registers them with ReportLab to prevent encoding crashes.
5. **Safety Limits**:
   - Maximum input file size: 50 MB
   - Maximum decoded text length: 5,000,000 characters (~5 MB)
   - Maximum HTML elements: 50,000
   - Maximum PDF pages: 500
   - Maximum table rows: 1,000

---

## Installation

### Requirements

- Python 3.10+
- Windows, macOS, or Linux

### Dependencies Added in Phase 4

```text
markdown>=3.4.0
```

### Setup

```bash
# Clone or enter the project directory
cd Velto_Conversion

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS/Linux

# Install dependencies
pip install -r backend/requirements.txt

# Apply migrations
python backend/manage.py migrate

# Run the development server
python backend/manage.py runserver 8000
```

---

## Verification Commands

```bash
# Run the Phase 4 Document Conversion test suite (42 tests)
python backend/manage.py test apps.conversions.tests_phase4_documents --verbosity=2

# Run Django system check
python backend/manage.py check

# Run full backend regression test suite
python backend/manage.py test apps.core apps.conversions apps.history --verbosity=2
```
