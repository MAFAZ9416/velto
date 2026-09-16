"""
Django settings for VELTO Conversion backend.

Environment variables are loaded from backend/.env (copy from .env.example).
Secrets are never hard-coded here.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env from the backend directory
load_dotenv(BASE_DIR / ".env")

# ── Security ───────────────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    # Fallback only for initial `migrate` before .env is created; replace immediately.
    "django-insecure-placeholder-replace-before-production",
)

DEBUG = os.environ.get("DEBUG", "True") == "True"

_raw_hosts = os.environ.get("ALLOWED_HOSTS", "127.0.0.1,localhost")
ALLOWED_HOSTS = [h.strip() for h in _raw_hosts.split(",") if h.strip()]

# ── Application definition ─────────────────────────────────────────────────────
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "corsheaders",
    "drf_spectacular",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
]

LOCAL_APPS = [
    "apps.core",
    "apps.users",
    "apps.conversions",
    "apps.history",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ── Middleware ─────────────────────────────────────────────────────────────────
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",          # must be first
    "django.middleware.security.SecurityMiddleware",
    "apps.core.middleware.RequestIdMiddleware",        # attaches X-Request-ID
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ── Database ───────────────────────────────────────────────────────────────────
import dj_database_url
from django.core.exceptions import ImproperlyConfigured

DJANGO_ENV = os.environ.get("DJANGO_ENV", "development").lower()
ALLOW_SQLITE_FALLBACK = os.environ.get("ALLOW_SQLITE_FALLBACK", "true").lower() in ("true", "1", "t")
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()

if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
            ssl_require=True if "sslmode=require" in DATABASE_URL or DJANGO_ENV == "production" else False,
        )
    }
else:
    if DJANGO_ENV == "production" and not ALLOW_SQLITE_FALLBACK:
        raise ImproperlyConfigured(
            "DATABASE_URL environment variable is required in production environment."
        )
    # Default SQLite3 fallback for local development and testing
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# ── Password validation ────────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ── Internationalisation ───────────────────────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ── Static files ───────────────────────────────────────────────────────────────
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# ── Default primary key ────────────────────────────────────────────────────────
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── Sessions ───────────────────────────────────────────────────────────────────
# Cookie-based sessions are used to identify anonymous users.
# Session data is stored server-side in the database (default backend).
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_NAME = "velto_session"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
# In production set SESSION_COOKIE_SECURE = True (requires HTTPS)
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_AGE = 60 * 60 * 24 * 90  # 90 days

# ── Django REST Framework ──────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "apps.core.renderers.VeltoResponseRenderer",
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",  # required for file uploads
        "rest_framework.parsers.FormParser",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        # Allow anonymous access globally; individual views can tighten this.
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {},
    "EXCEPTION_HANDLER": "apps.core.exceptions.custom_exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

from datetime import timedelta

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "VELTO Conversion API",
    "DESCRIPTION": (
        "Production-grade file conversion SaaS API providing secure document, "
        "image, and spreadsheet transformations."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "TAGS": [
        {"name": "System", "description": "Liveness and readiness health checks"},
        {"name": "Discovery", "description": "Conversion pair and format specifications discovery"},
        {"name": "Upload", "description": "Presigned upload URL generation and upload finalization"},
        {"name": "Jobs", "description": "Conversion job lifecycle management, status, retry, cancel, delete"},
        {"name": "Download", "description": "Secure file stream and presigned download URL endpoints"},
        {"name": "History", "description": "User and anonymous session conversion history with filtering and pagination"},
    ],
}

# ── CORS ───────────────────────────────────────────────────────────────────────
_raw_cors = os.environ.get("CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
CORS_ALLOWED_ORIGINS = [o.strip() for o in _raw_cors.split(",") if o.strip()]
CORS_ALLOW_CREDENTIALS = True  # needed so the browser sends the session cookie

# ── File uploads ───────────────────────────────────────────────────────────────
# Maximum upload size read from env; default 50 MB.
MAX_UPLOAD_SIZE = int(os.environ.get("MAX_UPLOAD_SIZE", 52_428_800))
DATA_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_SIZE
FILE_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_SIZE

# Temporary staging directory for conversion processing (not persisted in DB).
TEMP_UPLOAD_DIR = Path(os.environ.get("TEMP_UPLOAD_DIR", BASE_DIR.parent / "tmp_uploads"))

# ── Celery & Redis Configuration ───────────────────────────────────────────────
REDIS_URL = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", REDIS_URL)

CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

# Timeouts: 5 min hard limit, 4 min soft limit
CELERY_TASK_TIME_LIMIT = int(os.environ.get("CELERY_TASK_TIME_LIMIT", 300))
CELERY_TASK_SOFT_TIME_LIMIT = int(os.environ.get("CELERY_TASK_SOFT_TIME_LIMIT", 240))

# Worker reliability
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True

import sys
TESTING = "test" in sys.argv or os.environ.get("TESTING", "False").lower() in ("true", "1", "t")

# Celery Eager Mode (Synchronous execution for testing or fallback)
CELERY_TASK_ALWAYS_EAGER = TESTING or (os.environ.get("CELERY_TASK_ALWAYS_EAGER", "False").lower() in ("true", "1", "t"))
CELERY_TASK_EAGER_PROPAGATES = True

# ── Object Storage & Quota Settings ───────────────────────────────────────────
STORAGE_BACKEND = os.environ.get("STORAGE_BACKEND", "local").lower()
S3_ENDPOINT_URL = os.environ.get("S3_ENDPOINT_URL", None)
S3_REGION = os.environ.get("S3_REGION", "us-east-1")
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "velto-storage")
S3_ACCESS_KEY_ID = os.environ.get("S3_ACCESS_KEY_ID", "")
S3_SECRET_ACCESS_KEY = os.environ.get("S3_SECRET_ACCESS_KEY", "")

S3_PRESIGNED_UPLOAD_EXPIRY = int(os.environ.get("S3_PRESIGNED_UPLOAD_EXPIRY", 900))
S3_PRESIGNED_DOWNLOAD_EXPIRY = int(os.environ.get("S3_PRESIGNED_DOWNLOAD_EXPIRY", 900))
S3_MULTIPART_THRESHOLD = int(os.environ.get("S3_MULTIPART_THRESHOLD", 52_428_800))  # 50 MB

# Per-owner storage quota (500 MB default)
STORAGE_QUOTA_BYTES = int(os.environ.get("STORAGE_QUOTA_BYTES", 524_288_000))
# Retention period for completed output files and staging workspace (24 hours default)
STORAGE_RETENTION_HOURS = int(os.environ.get("STORAGE_RETENTION_HOURS", 24))



