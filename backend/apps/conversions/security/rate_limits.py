"""
DRF rate limiting throttles for VELTO Conversion API endpoints.

Applies configurable rate throttling per IP/session/user using Django's cache backend.
Supports deterministic test mode override to prevent test suite flakiness.
"""

from django.conf import settings
from rest_framework.throttling import SimpleRateThrottle
from apps.conversions.security.ownership import get_request_owner_identity


class BaseVeltoThrottle(SimpleRateThrottle):
    """Base throttle class for VELTO Conversion endpoints."""

    def allow_request(self, request, view):
        # Allow disabling throttling during automated unit tests
        if getattr(settings, "REST_FRAMEWORK_THROTTLE_ENABLE", True) is False:
            return True
        if getattr(settings, "TESTING", False) is True:
            return True
        return super().allow_request(request, view)

    def get_cache_key(self, request, view):
        user, session_key = get_request_owner_identity(request)
        if user:
            ident = f"user_{user.id}"
        elif session_key:
            ident = f"session_{session_key}"
        else:
            ident = self.get_ident(request)

        return self.cache_format % {
            "scope": self.scope,
            "ident": ident,
        }


class UploadRateThrottle(BaseVeltoThrottle):
    """Rate limit for file upload endpoints."""
    scope = "upload"
    rate = "30/minute"


class JobCreateRateThrottle(BaseVeltoThrottle):
    """Rate limit for conversion job creation."""
    scope = "job_create"
    rate = "30/minute"


class OcrRateThrottle(BaseVeltoThrottle):
    """Rate limit for expensive OCR operations."""
    scope = "ocr"
    rate = "10/minute"


class PdfUtilityRateThrottle(BaseVeltoThrottle):
    """Rate limit for PDF Utility operations."""
    scope = "pdf_utility"
    rate = "20/minute"


class DownloadRateThrottle(BaseVeltoThrottle):
    """Rate limit for output download endpoints."""
    scope = "download"
    rate = "60/minute"
