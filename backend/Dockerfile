# =============================================================================
# VELTO Conversion — Production Dockerfile
# =============================================================================
#
# Build target: backend/Dockerfile
# Context root: ./backend  (set Docker build context to ./backend on Render)
#
# System binaries installed:
#   - LibreOffice headless (writer, calc, impress) — for DOCX/PPTX/XLSX → PDF
#   - Tesseract OCR + eng data                     — for OCR engines
#   - Font packages                                — required by LibreOffice
#     for correct rendering of documents with non-ASCII glyphs
#
# Python application:
#   - Django 4.2 + DRF backend
#   - Gunicorn WSGI server
#   - All dependencies from requirements.txt
#
# Security:
#   - Runs as non-root 'app' user at runtime
#   - No shell-injection risk: LibreOffice invoked via subprocess list form
#   - LIBREOFFICE_PATH env var can override executable discovery
# =============================================================================

# ── Base image ─────────────────────────────────────────────────────────────────
# python:3.11-slim-bookworm is Debian Bookworm (12) — same apt pool as Ubuntu 22.04.
FROM python:3.11-slim-bookworm

# ── Build-time env ─────────────────────────────────────────────────────────────
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    DISPLAY="" \
    TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata

# ── System dependencies ────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-core \
    libreoffice-writer \
    libreoffice-calc \
    libreoffice-impress \
    fonts-liberation \
    fonts-liberation2 \
    fonts-noto \
    fonts-noto-cjk \
    fonts-freefont-ttf \
    fonts-dejavu-core \
    tesseract-ocr \
    tesseract-ocr-eng \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ── Verify LibreOffice headless works at build time ────────────────────────────
RUN libreoffice --headless --version

# ── Non-root user ─────────────────────────────────────────────────────────────
RUN groupadd --gid 1001 app && \
    useradd --uid 1001 --gid app --shell /bin/bash --create-home app

# ── Application directory ──────────────────────────────────────────────────────
WORKDIR /app

# ── Python dependencies ────────────────────────────────────────────────────────
COPY requirements.txt ./
RUN pip install --upgrade pip --no-cache-dir && \
    pip install --no-cache-dir -r requirements.txt

# ── Application source ─────────────────────────────────────────────────────────
COPY . .

# ── Writable runtime directories ──────────────────────────────────────────────
RUN mkdir -p /app/tmp_uploads /app/staticfiles && \
    chown -R app:app /app/tmp_uploads /app/staticfiles

# ── Ownership ─────────────────────────────────────────────────────────────────
RUN chown -R app:app /app

# ── Switch to non-root user ────────────────────────────────────────────────────
USER app

# ── Collect static files ──────────────────────────────────────────────────────
RUN SECRET_KEY=docker-build-collectstatic-dummy \
    DJANGO_ENV=production \
    DATABASE_URL="" \
    ALLOW_SQLITE_FALLBACK=true \
    python manage.py collectstatic --noinput

# ── Runtime port ──────────────────────────────────────────────────────────────
EXPOSE 8000

# ── Healthcheck ───────────────────────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/api/health/ || exit 1

# ── Start command ─────────────────────────────────────────────────────────────
CMD ["sh", "-c", "python manage.py migrate --noinput && \
    gunicorn config.wsgi:application \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers ${GUNICORN_WORKERS:-2} \
    --timeout ${GUNICORN_TIMEOUT:-120} \
    --log-level info \
    --access-logfile - \
    --error-logfile -"]
