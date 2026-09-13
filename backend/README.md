# VELTO Conversion Backend

Production-oriented Django + DRF backend for the VELTO file conversion SaaS platform.

---

# VELTO Conversion Backend

Production-oriented Django + DRF backend for the VELTO file conversion SaaS platform.

---

## Phase 3 — Image Conversion Phase (JPG, PNG, WEBP, BMP, TIFF, GIF, ZIP)

Phase 3 provides production-quality image conversion engines, compression, resizing, and archive packaging:
* **JPG ↔ PNG**: High-fidelity conversion preserving visual orientation and dimensions.
* **PNG → JPG**: Compositing alpha channel onto solid white background `(255, 255, 255)` to prevent legibility issues.
* **General Format Conversions**: Full matrix support between **JPG**, **PNG**, **WEBP**, **BMP**, **TIFF**, **GIF**.
* **Image Compression**: Customizable quality (JPEG/WEBP), progressive encoding, optimize flags, and PNG compression levels.
* **Image Resizing**: High-quality `LANCZOS` resampling, aspect-ratio preservation, no-upscale defaults, and max pixel bounds.
* **Multiple Images → ZIP**: Packaging single or multiple uploaded images into clean ZIP archives with zero-padded deterministic ordering.

### Supported Conversions & Status

| Feature | Status |
|---|---|
| Upload PDF, DOCX, PPTX, XLSX, CSV, JPG, PNG, WEBP, BMP, TIFF, GIF | ✅ |
| Validate image signatures, dimensions, decomp bomb bounds & format | ✅ Pillow validation |
| Convert JPG ↔ PNG | ✅ Real conversion |
| Convert PNG → JPG (RGBA transparent composited on white) | ✅ Real rendering |
| Convert Image formats (JPG, PNG, WEBP, BMP, TIFF, GIF) | ✅ Real conversion |
| Image Compression (`quality`, `compress_level`, `optimize`, `progressive`) | ✅ Real optimization |
| Image Resizing (`width`, `height`, `preserve_aspect_ratio`, `allow_upscale`) | ✅ Real LANCZOS resampling |
| Package Multiple Images → ZIP archive | ✅ Real ZIP packaging |
| Convert PDF → Word (.docx), Excel (.xlsx), JPG, PNG | ✅ Real rendering |
| Convert Word (.docx) → PDF, JPG, PNG | ✅ Real LibreOffice / PyMuPDF |
| Convert PowerPoint (.pptx) → PDF, JPG, PNG | ✅ Real LibreOffice / PyMuPDF |
| Convert Excel (.xlsx) → PDF, JPG, PNG | ✅ Real LibreOffice / PyMuPDF |
| Convert CSV → XLSX, PDF, JPG, PNG | ✅ Real conversion |
| Return completed job with accurate output metadata | ✅ |
| Download converted output via protected endpoint | ✅ |
| Session-based anonymous ownership & cross-session isolation | ✅ |
| Honest error responses & resource teardown | ✅ |
| 297 automated tests | ✅ All 297 passing |

---

## Image Conversion Parameters

API requests to `POST /api/conversions/` can pass optional parameters inside `options`:

```json
{
  "source_format": "jpg",
  "target_format": "png",
  "options": {
    "width": 800,
    "height": 600,
    "preserve_aspect_ratio": true,
    "allow_upscale": false,
    "quality": 85,
    "compress_level": 6,
    "optimize": true,
    "progressive": true
  }
}
```

### Safety & Processing Rules

- **Decompression Bomb Protection**: Enforces an `80,000,000` pixel limit (80 Megapixels) per image to protect server resources.
- **EXIF Orientation**: Applies `PIL.ImageOps.exif_transpose()` automatically before resizing or saving.
- **Transparency Compositing**: Converts transparent RGBA / Palette PNGs to solid white RGB background when output format is JPEG or BMP.
- **Animation Safety**: Restricts multi-frame animated GIF/WEBP inputs to single-frame processing or returns explicit validation errors.
- **ZIP Security**: Enforces zero-padded deterministic file ordering (`image_001_...`, `image_002_...`) and sanitizes archive member paths against directory traversal.

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

## Running Tests

```bash
# Run the Phase 3 Image Conversion test suite
python backend/manage.py test apps.conversions.tests_phase3_images --verbosity=2

# Run the full backend test suite
python backend/manage.py test apps.core apps.conversions apps.history --verbosity=2
```

