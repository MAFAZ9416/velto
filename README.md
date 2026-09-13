# VELTO Conversion

> A production-ready, secure, and extensible file-conversion platform built with Django REST Framework.

<p align="center">
  <strong>Convert documents, spreadsheets, presentations, images, and text files through one reliable conversion backend.</strong>
</p>

<p align="center">
  <a href="#features">Features</a>
  •
  <a href="#supported-conversions">Conversions</a>
  •
  <a href="#architecture">Architecture</a>
  •
  <a href="#installation">Installation</a>
  •
  <a href="#api-usage">API Usage</a>
  •
  <a href="#testing">Testing</a>
  •
  <a href="#roadmap">Roadmap</a>
</p>

---

## Overview

**VELTO Conversion** is a backend-first file-conversion SaaS platform designed to provide reliable, secure, and scalable document processing.

The project is built around a modular conversion-engine architecture. Each conversion type is implemented as an independent engine and registered through a central engine registry. This makes the platform easier to maintain, test, extend, and eventually connect to a modern frontend.

VELTO is designed as a serious product rather than a demonstration project.

### Core principles

* Production-quality backend architecture
* Secure file handling
* Session-based isolation
* Modular conversion engines
* Strict input and output validation
* Reliable temporary-file cleanup
* Clear API behavior
* Comprehensive automated testing
* Extensible architecture for future conversion types

---

## Current Status

| Area                    | Status                         |
| ----------------------- | ------------------------------ |
| Backend framework       | Django + Django REST Framework |
| Conversion architecture | Modular engine registry        |
| Session isolation       | Implemented                    |
| Conversion history      | Implemented                    |
| Failed-job history      | Implemented                    |
| Temporary-file cleanup  | Implemented and tested         |
| Image conversions       | Completed                      |
| Document conversions    | In progress                    |
| Frontend                | Planned                        |
| Full backend regression | Passing                        |

### Verification status

* Image conversion tests: **28/28 passed**
* Full backend test suite: **297/297 passed**
* Django system check: **0 issues**
* Manual image verification: **Passed**
* Temporary-file cleanup regression: **Resolved**

---

## Features

### File Conversion

VELTO currently supports conversion between several major file formats.

#### PDF conversions

* PDF → DOCX
* PDF → JPG
* PDF → PNG
* PDF → XLSX

#### Microsoft Office conversions

* DOCX → PDF
* DOCX → JPG
* DOCX → PNG
* PPTX → PDF
* PPTX → JPG
* PPTX → PNG
* XLSX → PDF
* XLSX → JPG
* XLSX → PNG

#### Spreadsheet conversions

* CSV → XLSX
* CSV → PDF
* CSV → JPG
* CSV → PNG

#### Image conversions

* JPG → PNG
* PNG → JPG
* JPG → JPG
* PNG → PNG
* WEBP → JPG
* WEBP → PNG
* BMP → JPG
* BMP → PNG
* TIFF → JPG
* TIFF → PNG
* GIF → JPG
* GIF → PNG
* Image compression
* Image resizing
* Multiple images → ZIP

#### Document conversions

Planned and currently being implemented:

* TXT → PDF
* TXT → DOCX
* HTML → PDF
* HTML → DOCX
* Markdown → PDF
* Markdown → DOCX

---

## Image Processing Features

VELTO includes a dedicated image-processing layer built with safety and predictable output behavior in mind.

### Supported image operations

#### Format conversion

Convert between supported image formats while preserving image dimensions whenever possible.

#### Compression

Supported compression options include:

* JPEG quality
* Progressive JPEG output
* JPEG optimization
* PNG compression level
* WebP quality
* WebP lossless mode
* WebP encoding method

> Compression does not always guarantee a smaller file. The final size depends on the source image and selected encoding settings.

#### Resizing

Supported resizing behavior includes:

* Custom width
* Custom height
* Aspect-ratio preservation
* High-quality LANCZOS resampling
* Upscaling protection by default
* Pixel-count safety validation

#### Transparency handling

When converting transparent PNG images to JPEG, VELTO composites the image onto a white background to avoid black or corrupted transparency artifacts.

#### Multi-image ZIP

VELTO can package multiple image files into a ZIP archive.

The ZIP process includes:

* Independent validation of every image
* Deterministic file ordering
* Safe member filenames
* Path-traversal protection
* Session isolation
* Cleanup of temporary files

---

## Supported Input and Output Formats

| Format   | Extension       | MIME Type                                                                   |
| -------- | --------------- | --------------------------------------------------------------------------- |
| PDF      | `.pdf`          | `application/pdf`                                                           |
| DOCX     | `.docx`         | `application/vnd.openxmlformats-officedocument.wordprocessingml.document`   |
| XLSX     | `.xlsx`         | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`         |
| PPTX     | `.pptx`         | `application/vnd.openxmlformats-officedocument.presentationml.presentation` |
| CSV      | `.csv`          | `text/csv`                                                                  |
| TXT      | `.txt`          | `text/plain`                                                                |
| HTML     | `.html`, `.htm` | `text/html`                                                                 |
| Markdown | `.md`           | `text/markdown`                                                             |
| JPG      | `.jpg`, `.jpeg` | `image/jpeg`                                                                |
| PNG      | `.png`          | `image/png`                                                                 |
| WEBP     | `.webp`         | `image/webp`                                                                |
| BMP      | `.bmp`          | `image/bmp`                                                                 |
| TIFF     | `.tif`, `.tiff` | `image/tiff`                                                                |
| GIF      | `.gif`          | `image/gif`                                                                 |
| ZIP      | `.zip`          | `application/zip`                                                           |

---

## Architecture

VELTO follows a layered architecture.

```text
Client
  │
  ▼
Django REST API
  │
  ▼
Serializers
  │
  ▼
Conversion Service
  │
  ▼
Conversion Job
  │
  ▼
Engine Registry
  │
  ▼
Selected Conversion Engine
  │
  ├── Input Validation
  ├── Temporary Workspace
  ├── Conversion Processing
  ├── Output Validation
  └── Cleanup
  │
  ▼
Stored Output
  │
  ▼
Download / History API
```

### Main layers

#### API layer

Responsible for:

* Receiving uploads
* Validating request data
* Creating conversion jobs
* Returning job status
* Providing output downloads
* Returning useful API errors

#### Serializer layer

Responsible for:

* Request validation
* Format validation
* Options validation
* Multi-file upload validation
* Response serialization

#### Service layer

Responsible for:

* Staging uploaded files
* Creating conversion jobs
* Managing conversion lifecycle
* Passing options to engines
* Managing output files
* Cleaning temporary resources

#### Engine layer

Each conversion is handled by a dedicated engine implementing the common engine contract.

Examples:

* `CsvToPdfEngine`
* `CsvToJpgEngine`
* `JpgToPngEngine`
* `PngToJpgEngine`
* `GenericImageConversionEngine`
* `ImagesToZipEngine`

#### Validation layer

Responsible for:

* File signature validation
* Format verification
* Output validation
* Image safety checks
* PDF validation
* DOCX archive validation
* File-size and pixel-count limits

#### History layer

Stores completed and failed conversion jobs while keeping sessions isolated.

Pending and processing jobs do not appear in the history list.

---

## Project Structure

```text
Velto_Conversion/
│
├── backend/
│   ├── manage.py
│   ├── README.md
│   │
│   ├── config/
│   │   ├── settings.py
│   │   ├── urls.py
│   │   ├── asgi.py
│   │   └── wsgi.py
│   │
│   └── apps/
│       ├── core/
│       ├── conversions/
│       │   ├── migrations/
│       │   ├── engines/
│       │   │   ├── base.py
│       │   │   ├── validators.py
│       │   │   ├── image_engine.py
│       │   │   └── ...
│       │   ├── formats.py
│       │   ├── models.py
│       │   ├── serializers.py
│       │   ├── services.py
│       │   ├── views.py
│       │   ├── apps.py
│       │   └── tests_*.py
│       │
│       └── history/
│
├── .venv/
│
└── README.md
```

---

## Installation

### Requirements

Recommended environment:

* Windows, Linux, or macOS
* Python 3.11+
* Git
* Virtual environment support
* LibreOffice for Office/PDF conversions where required

### Clone the project

```powershell
git clone <your-repository-url>
cd Velto_Conversion
```

### Create a virtual environment

```powershell
py -m venv .venv
```

### Activate the virtual environment

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Windows Command Prompt:

```cmd
.venv\Scripts\activate
```

Linux/macOS:

```bash
source .venv/bin/activate
```

### Install dependencies

```powershell
pip install -r backend/requirements.txt
```

If the project uses a different dependency file, install the dependencies defined by the current backend setup.

### Apply migrations

```powershell
.venv\Scripts\python backend\manage.py migrate
```

### Run system checks

```powershell
.venv\Scripts\python backend\manage.py check
```

### Start the development server

```powershell
.venv\Scripts\python backend\manage.py runserver
```

The development server will normally be available at:

```text
http://127.0.0.1:8000/
```

---

## Environment Configuration

Use environment variables for deployment-specific configuration.

Recommended variables include:

```env
DEBUG=True
SECRET_KEY=change-this-in-production
ALLOWED_HOSTS=127.0.0.1,localhost
DATABASE_URL=
MEDIA_ROOT=
MAX_UPLOAD_SIZE=
```

Never commit production secrets to the repository.

For production:

* Set `DEBUG=False`
* Use a strong secret key
* Configure trusted hosts
* Use a production database
* Configure secure media storage
* Enable HTTPS
* Restrict allowed origins
* Configure logging
* Configure background processing if required

---

## API Usage

The API is designed around conversion jobs.

A typical workflow is:

```text
1. Upload a file
2. Select the target format
3. Create a conversion job
4. Process the job
5. Check job status
6. Download the output
7. View the job in history
```

### Create a conversion job

Example request:

```http
POST /api/conversions/
Content-Type: multipart/form-data
```

Example form fields:

```text
file: notes.csv
target_format: pdf
```

Example using cURL:

```bash
curl -X POST http://127.0.0.1:8000/api/conversions/ \
  -F "file=@notes.csv" \
  -F "target_format=pdf"
```

### Image conversion with options

Example:

```bash
curl -X POST http://127.0.0.1:8000/api/conversions/ \
  -F "file=@photo.png" \
  -F "target_format=jpg" \
  -F 'options={"quality":40}'
```

### Image resizing

Example:

```bash
curl -X POST http://127.0.0.1:8000/api/conversions/ \
  -F "file=@photo.jpg" \
  -F "target_format=png" \
  -F 'options={"width":800,"preserve_aspect_ratio":true}'
```

### Multi-image ZIP

Example:

```bash
curl -X POST http://127.0.0.1:8000/api/conversions/ \
  -F "files=@image-one.jpg" \
  -F "files=@image-two.png" \
  -F "target_format=zip"
```

The exact field names should follow the current serializer implementation.

### Check job status

```http
GET /api/conversions/<job-id>/
```

Example:

```bash
curl http://127.0.0.1:8000/api/conversions/<job-id>/
```

### Download output

```http
GET /api/conversions/<job-id>/download/
```

Example:

```bash
curl -L \
  http://127.0.0.1:8000/api/conversions/<job-id>/download/ \
  -o converted-file
```

### View conversion history

```http
GET /api/history/
```

### Filter completed jobs

```http
GET /api/history/?status=completed
```

### Filter failed jobs

```http
GET /api/history/?status=failed
```

---

## Job Lifecycle

A conversion job may move through the following states:

```text
PENDING
   │
   ▼
PROCESSING
   │
   ├──► COMPLETED
   │
   └──► FAILED
```

### History behavior

* `PENDING` jobs are not shown in history.
* `PROCESSING` jobs are not shown in history.
* `COMPLETED` jobs appear in history.
* `FAILED` jobs appear in history.
* History is isolated between sessions.
* Users cannot access another session’s conversion output.

---

## Security

Security is a core part of VELTO’s design.

### File validation

VELTO does not rely only on file extensions.

Validation may include:

* File signature checks
* MIME-type verification
* Actual file parsing
* Corruption detection
* Output structure validation
* File-size limits
* Image pixel-count limits

### Image safety

The image-processing layer enforces a maximum image size of:

```text
80,000,000 pixels
```

This helps reduce the risk of decompression-bomb attacks and excessive memory usage.

### Image restrictions

Animated GIF and animated WEBP inputs are restricted to single-frame processing unless animation support is explicitly implemented.

Multi-page TIFF behavior is also restricted where full multi-page support is not available.

### Path traversal protection

Uploaded filenames and ZIP member filenames are sanitized.

Unsafe paths such as the following are rejected or normalized:

```text
../../secret.txt
..\..\secret.txt
/absolute/path/file.txt
```

### HTML security

HTML is treated as untrusted input.

The conversion pipeline must:

* Remove or neutralize scripts
* Block dangerous URL schemes
* Remove event-handler attributes
* Prevent local file access
* Prevent external network requests
* Avoid JavaScript execution
* Avoid arbitrary resource loading

### Session isolation

Each client session can access only its own jobs, files, outputs, and history records.

Cross-session access attempts should return an appropriate `404` response rather than exposing whether another session’s job exists.

---

## Temporary Files and Cleanup

Conversion engines frequently require intermediate files.

For example:

```text
CSV
 │
 ▼
XLSX
 │
 ▼
PDF
 │
 ▼
JPG
```

VELTO uses temporary workspaces for intermediate files.

Every engine must:

* Track the temporary resources it creates
* Clean up on successful conversion
* Clean up on failed conversion
* Clean up nested intermediate files
* Preserve the final output
* Avoid deleting unrelated files
* Avoid leaving orphaned directories

Cleanup must happen through guaranteed cleanup logic such as `try/finally` or managed temporary-directory contexts.

---

## Output Validation

VELTO validates generated files before making them available for download.

### PDF validation

Checks may include:

* Valid PDF signature
* Non-empty output
* Parseable PDF structure
* Expected file extension
* Expected MIME type

### DOCX validation

A DOCX file must be a valid ZIP archive containing required document files such as:

```text
[Content_Types].xml
word/document.xml
```

### Image validation

Checks may include:

* Valid image signature
* Actual image format
* Image readability
* Dimensions
* Pixel count
* Frame count
* Corruption detection
* Expected MIME type

---

## Testing

The project uses Django’s test framework.

### Run image conversion tests

```powershell
.venv\Scripts\python backend\manage.py test apps.conversions.tests_phase3_images --verbosity=2
```

### Run all conversion tests

```powershell
.venv\Scripts\python backend\manage.py test apps.conversions --verbosity=1
```

### Run core, conversion, and history tests

```powershell
.venv\Scripts\python backend\manage.py test apps.core apps.conversions apps.history --verbosity=1
```

### Run the complete backend suite

```powershell
.venv\Scripts\python backend\manage.py test --verbosity=1
```

### Run Django checks

```powershell
.venv\Scripts\python backend\manage.py check
```

### Show migrations

```powershell
.venv\Scripts\python backend\manage.py showmigrations
```

### Manual image verification

```powershell
.venv\Scripts\python verify_manual_images.py
```

---

## Testing Philosophy

VELTO tests more than successful conversions.

Test coverage includes:

* Valid input files
* Invalid input files
* Corrupted files
* Unsupported formats
* Invalid conversion pairs
* Unicode content
* Tamil content
* Empty files
* Large files
* Long lines
* Transparency
* Image dimensions
* Compression options
* Resize options
* ZIP safety
* Session isolation
* History filtering
* Download behavior
* Failed jobs
* Temporary-file cleanup
* Output validation

A conversion feature is not considered complete until:

1. Focused tests pass.
2. Existing conversion tests pass.
3. Full backend regression passes.
4. Django system checks pass.
5. Manual verification succeeds where appropriate.
6. Temporary resources are confirmed to be cleaned up.

---

## Development Guidelines

When adding a new conversion engine:

1. Inspect the existing architecture.
2. Reuse `BaseConversionEngine`.
3. Add format constants.
4. Add the supported conversion pair.
5. Implement input validation.
6. Implement the conversion engine.
7. Register the engine.
8. Add output validation.
9. Add cleanup handling.
10. Add focused tests.
11. Run the complete regression suite.
12. Update documentation.

### Do not

* Duplicate the entire conversion service
* Bypass session isolation
* Trust file extensions alone
* Leave temporary files behind
* Expose internal paths in API responses
* Silently ignore invalid input
* Add unsupported conversion pairs
* Weaken tests to hide implementation failures
* Claim unsupported features in documentation

---

## Roadmap

### Completed

* Core Django project setup
* Conversion job model
* Conversion service
* Engine registry
* Session isolation
* History API
* PDF conversions
* Office document conversions
* CSV conversions
* Image conversions
* Image compression
* Image resizing
* Multi-image ZIP packaging
* Temporary-file cleanup
* Output validation
* Regression testing

### In progress

* TXT → PDF
* TXT → DOCX
* HTML → PDF
* HTML → DOCX
* Markdown → PDF
* Markdown → DOCX

### Planned

* Frontend application
* Drag-and-drop uploads
* Conversion progress indicators
* Batch conversion dashboard
* User accounts
* Persistent cloud storage
* Background task processing
* Conversion quotas
* Usage analytics
* Subscription plans
* API keys
* Webhooks
* Team workspaces
* Cloud deployment
* Observability and monitoring

---

## Product Direction

VELTO Conversion is being developed as a complete file-conversion SaaS platform.

The long-term goal is to provide:

* Fast and reliable conversion
* Simple user experience
* Secure file processing
* Clear conversion status
* Downloadable results
* Conversion history
* Batch workflows
* Developer-friendly APIs
* Scalable infrastructure

The backend is intentionally being developed and stabilized before the frontend is introduced.

---

## Contributing

Contributions are welcome when they preserve the project’s architecture and quality standards.

Before submitting changes:

* Run the focused tests.
* Run the complete test suite.
* Run `manage.py check`.
* Confirm migrations are valid.
* Confirm no temporary files remain.
* Update documentation.
* Include tests for new behavior.
* Avoid unrelated changes.

---

## License

Add the project’s selected license here before public release.

Example:

```text
MIT License
```

Do not publish a license declaration until the repository owner has selected the appropriate license.

---

## Maintainer

**VELTO Conversion**

Built with:

* Python
* Django
* Django REST Framework
* Pillow
* LibreOffice-based document processing
* Modular conversion engines
* Automated regression testing

---

<p align="center">
  <strong>VELTO Conversion — Convert Anything. Build Without Limits.</strong>
</p>
