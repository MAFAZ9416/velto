# VELTO Conversion Backend

Production-oriented Django + DRF backend for the VELTO file conversion SaaS platform.

---

## Phase 2 — Conversion Engines (PDF, DOCX, PPTX, XLSX, CSV, JPG, PNG)

Phase 2 provides real, working conversion engines for:
* **PDF → DOCX** using **pdf2docx** and **PyMuPDF**.
* **PDF → JPG** using **PyMuPDF** (`pymupdf`).
* **PDF → PNG** using **PyMuPDF** (`pymupdf`).
* **PDF → XLSX** using **PyMuPDF**, **pdfplumber**, and **openpyxl**.
* **DOCX → PDF** using **LibreOffice** headless mode.
* **DOCX → JPG** using **LibreOffice** + **PyMuPDF**.
* **DOCX → PNG** using **LibreOffice** + **PyMuPDF**.
* **PPTX → PDF** using **LibreOffice** headless mode.
* **PPTX → JPG** using **LibreOffice** + **PyMuPDF**.
* **PPTX → PNG** using **LibreOffice** + **PyMuPDF**.
* **XLSX → PDF** using **LibreOffice** headless mode.
* **XLSX → JPG** using **LibreOffice** + **PyMuPDF**.
* **XLSX → PNG** using **LibreOffice** + **PyMuPDF**.
* **CSV → XLSX** using native **csv** module + **openpyxl**.
* **CSV → PDF** using **CsvToXlsxEngine** + **XlsxToPdfEngine** (**LibreOffice**).
* **CSV → JPG** using **CsvToPdfEngine** + **PdfToJpgEngine** (**PyMuPDF**).
* **CSV → PNG** using **CsvToPdfEngine** + **PdfToPngEngine** (**PyMuPDF**).

### What works now

| Feature | Status |
|---|---|
| Upload a PDF, DOCX, PPTX, XLSX, or CSV file via REST API | ✅ |
| Validate PDF, DOCX, PPTX, XLSX & CSV (signatures, extension, MIME, size, structure) | ✅ |
| Convert PDF → Word (.docx) | ✅ Real conversion |
| Convert PDF → JPG (1-page .jpg, multi-page .zip) | ✅ Real rendering |
| Convert PDF → PNG (1-page .png, multi-page .zip) | ✅ Real rendering |
| Convert PDF → Excel (.xlsx) | ✅ Real table extraction |
| Convert Word (.docx) → PDF | ✅ Real LibreOffice conversion |
| Convert Word (.docx) → JPG (1-page .jpg, multi-page .zip) | ✅ Real conversion |
| Convert Word (.docx) → PNG (1-page .png, multi-page .zip) | ✅ Real conversion |
| Convert PowerPoint (.pptx) → PDF | ✅ Real LibreOffice conversion |
| Convert PowerPoint (.pptx) → JPG (1-slide .jpg, multi-slide .zip) | ✅ Real conversion |
| Convert PowerPoint (.pptx) → PNG (1-slide .png, multi-slide .zip) | ✅ Real conversion |
| Convert Excel (.xlsx) → PDF | ✅ Real LibreOffice conversion |
| Convert Excel (.xlsx) → JPG (1-page .jpg, multi-page .zip) | ✅ Real conversion |
| Convert Excel (.xlsx) → PNG (1-page .png, multi-page .zip) | ✅ Real conversion |
| Convert CSV → Excel (.xlsx) | ✅ Real openpyxl generation |
| Convert CSV → PDF | ✅ Real CsvToXlsx + LibreOffice conversion |
| Convert CSV → JPG (1-page .jpg, multi-page .zip) | ✅ Real rendering |
| Convert CSV → PNG (1-page .png, multi-page .zip) | ✅ Real rendering |
| Return completed job with accurate output metadata | ✅ |
| Download converted output via protected endpoint | ✅ |
| Session-based anonymous ownership | ✅ |
| Honest error responses & output validation via PyMuPDF & Pillow | ✅ |
| Invalid/corrupt file returns honest error | ✅ |
| Cross-session access blocked | ✅ |
| 269 automated tests | ✅ All 269 passing |

---

## Installation

### Requirements

- Python 3.10+
- Windows, macOS, or Linux

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

# (Optional) Create a superuser for Django admin
python backend/manage.py createsuperuser

# Run the development server
python backend/manage.py runserver 8000
```

---

## Output Behavior for XLSX → JPG / PNG Conversions

- **Composition**: Converts XLSX to intermediate PDF via `XlsxToPdfEngine` (LibreOffice headless) and renders pages via `PdfToJpgEngine` / `PdfToPngEngine` (PyMuPDF).
- **Single-Page Workbook**: Produces a single image file (`financial_report.jpg` or `financial_report.png`).
- **Multi-Sheet/Multi-Page Workbook**: Produces a `.zip` archive (`financial_report.zip`) containing ordered sheet images (`page-001.jpg`, `page-002.jpg`, etc.).
- **Resource Safety**: Intermediate PDFs, profile directories, and work files are generated inside isolated temporary directories and automatically purged on success and failure.

---

## Running Tests

```bash
# Run the focused XLSX image test suite
python backend/manage.py test apps.conversions.tests_phase2_xlsx_images --verbosity=2

# Run the full backend test suite
python backend/manage.py test apps.core apps.conversions apps.history --verbosity=2
```
