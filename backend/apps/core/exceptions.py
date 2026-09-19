"""
Centralized Error Handling & Exception Management for VELTO Conversion.

Provides a unified DRF exception handler converting all API errors into the standard envelope:
{
  "success": false,
  "data": null,
  "error": {
    "code": "ERROR_CODE",
    "message": "Safe human-readable message",
    "details": { ... },
    "request_id": "8f3a..."
  }
}
"""

import logging
import uuid
from typing import Any

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    MethodNotAllowed,
    NotAuthenticated,
    NotFound,
    PermissionDenied,
    Throttled,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler

from apps.conversions.engines.base import ConversionError
from apps.conversions.security.exceptions import (
    AbuseLimitExceeded,
    AntivirusUnavailable,
    ArchiveLimitExceeded,
    DocumentLimitExceeded,
    FileTooLarge,
    InvalidFileSignature,
    InvalidMimeType,
    MalwareDetected,
    OutputTooLarge,
    OwnershipDenied,
    PathTraversalAttempt,
    ProcessingTimeout,
    RateLimitExceeded,
    SecurityValidationError,
    UnsafeFilename,
)

logger = logging.getLogger(__name__)


def _sanitize_message(message: str) -> str:
    """Strip internal file paths, credentials, or stack trace artifacts if present."""
    msg = str(message)
    msg_lower = msg.lower()

    # 1. Sanitize sensitive connection strings, credentials, or secrets
    if any(k in msg_lower for k in ("postgres://", "redis://", "password=", "secret_key", "access_key", "sslmode=")):
        return "A system service configuration error occurred."

    # 2. Sanitize internal stack traces or module paths
    if "traceback (" in msg_lower or 'file "' in msg_lower or "line " in msg_lower:
        return "An internal server error occurred during request processing."

    # 3. Sanitize filesystem paths or storage location leaks
    if any(k in msg for k in ("C:\\", "C:/", "/Users/", "/home/", "/tmp/", "\\AppData\\", "file:///")):
        if "does not exist" in msg_lower or "not found" in msg_lower:
            return "The requested file or resource could not be found."
        elif "permission" in msg_lower or "access" in msg_lower:
            return "Storage permission error occurred."
        elif "full" in msg_lower or "space" in msg_lower:
            return "Storage capacity exceeded. Please try again later."
        return "A file processing error occurred."

    return msg


def _derive_error_code(exc: Exception, http_status: int) -> str:
    """Map exception instances or HTTP status codes to standardized uppercase error codes."""
    if hasattr(exc, "error_code") and getattr(exc, "error_code"):
        return str(getattr(exc, "error_code")).upper()

    if isinstance(exc, (InvalidMimeType, InvalidFileSignature)):
        return "INVALID_FILE_TYPE"
    if isinstance(exc, FileTooLarge):
        return "FILE_TOO_LARGE"
    if isinstance(exc, OutputTooLarge):
        return "OUTPUT_TOO_LARGE"
    if isinstance(exc, (PathTraversalAttempt, UnsafeFilename)):
        return "PATH_TRAVERSAL_DETECTED"
    if isinstance(exc, OwnershipDenied):
        return "PERMISSION_DENIED"
    if isinstance(exc, ProcessingTimeout):
        return "PROCESSING_TIMEOUT"
    if isinstance(exc, (RateLimitExceeded, AbuseLimitExceeded, Throttled)):
        return "RATE_LIMIT_EXCEEDED"
    if isinstance(exc, (MalwareDetected, AntivirusUnavailable)):
        return "SECURITY_VALIDATION_FAILED"
    if isinstance(exc, (ArchiveLimitExceeded, DocumentLimitExceeded)):
        return "RESOURCE_LIMIT_EXCEEDED"

    if isinstance(exc, ValidationError):
        return "VALIDATION_ERROR"
    if isinstance(exc, (NotAuthenticated, AuthenticationFailed)):
        return "UNAUTHENTICATED"
    if isinstance(exc, (PermissionDenied, DjangoPermissionDenied)):
        return "PERMISSION_DENIED"
    if isinstance(exc, (NotFound, Http404)):
        return "NOT_FOUND"
    if isinstance(exc, MethodNotAllowed):
        return "METHOD_NOT_ALLOWED"
    if isinstance(exc, ConversionError):
        return "CONVERSION_FAILURE"

    status_code_map = {
        400: "VALIDATION_ERROR",
        401: "UNAUTHENTICATED",
        403: "PERMISSION_DENIED",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "INVALID_JOB_STATE",
        410: "EXPIRED_JOB",
        413: "FILE_TOO_LARGE",
        415: "INVALID_FILE_TYPE",
        422: "CONVERSION_FAILURE",
        429: "RATE_LIMIT_EXCEEDED",
        500: "INTERNAL_ERROR",
        503: "INFRASTRUCTURE_UNAVAILABLE",
    }
    return status_code_map.get(http_status, "INTERNAL_ERROR")


def derive_error_category(exc: Exception, http_status: int = 500) -> str:
    """Map exception instances or HTTP status codes to standardized error categories."""
    if hasattr(exc, "error_category") and getattr(exc, "error_category"):
        return str(getattr(exc, "error_category")).lower()

    if isinstance(exc, (NotAuthenticated, AuthenticationFailed)):
        return "authentication_error"
    if isinstance(exc, (PermissionDenied, DjangoPermissionDenied, OwnershipDenied)):
        return "authorization_error"
    if isinstance(exc, (RateLimitExceeded, AbuseLimitExceeded, Throttled, ArchiveLimitExceeded, DocumentLimitExceeded)):
        return "quota_error"
    if isinstance(exc, (InvalidMimeType, InvalidFileSignature, FileTooLarge, OutputTooLarge, PathTraversalAttempt, UnsafeFilename)):
        return "file_error"
    if isinstance(exc, (ValidationError, SecurityValidationError)):
        return "validation_error"
    if isinstance(exc, ProcessingTimeout):
        return "timeout_error"
    if isinstance(exc, ConversionError):
        msg_str = str(exc).lower()
        if "ocr" in msg_str or "tesseract" in msg_str:
            return "ocr_error"
        if "format" in msg_str or "unsupported" in msg_str:
            return "unsupported_format"
        return "conversion_engine_error"

    if http_status == 401:
        return "authentication_error"
    if http_status == 403:
        return "authorization_error"
    if http_status in (400, 422):
        return "validation_error"
    if http_status == 429:
        return "quota_error"
    if http_status == 503:
        return "external_service_error"

    return "internal_error"


def custom_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    """
    Global DRF exception handler formatting all API error responses into standard envelope.
    """
    request = context.get("request")
    request_id = getattr(request, "request_id", "") if request else ""
    if not request_id:
        request_id = uuid.uuid4().hex

    response = exception_handler(exc, context)

    # If DRF handled it
    if response is not None:
        http_status = response.status_code
        error_code = _derive_error_code(exc, http_status)
        details = {}
        message = "An error occurred during request processing."

        if isinstance(response.data, dict):
            if "detail" in response.data:
                message = _sanitize_message(response.data["detail"])
            else:
                message = "Validation error."
                details = {
                    field: [str(e) for e in errors] if isinstance(errors, list) else [str(errors)]
                    for field, errors in response.data.items()
                }
        elif isinstance(response.data, list):
            message = "; ".join(str(e) for e in response.data)

        # Build standard error envelope
        response.data = {
            "success": False,
            "data": None,
            "error": {
                "code": error_code,
                "message": message,
                "details": details,
                "request_id": request_id,
            },
        }
        return response

    # Handle ConversionError and domain security exceptions directly
    if isinstance(exc, ConversionError):
        error_code = _derive_error_code(exc, 400)
        message = _sanitize_message(str(exc))
        http_status = status.HTTP_400_BAD_REQUEST

        if isinstance(exc, OwnershipDenied):
            http_status = status.HTTP_403_FORBIDDEN
        elif isinstance(exc, PathTraversalAttempt):
            http_status = status.HTTP_400_BAD_REQUEST

        return Response(
            {
                "success": False,
                "data": None,
                "error": {
                    "code": error_code,
                    "message": message,
                    "details": {},
                    "request_id": request_id,
                },
            },
            status=http_status,
        )

    # Unhandled server exceptions (500)
    logger.exception("Unhandled server exception for request %s: %s", request_id, exc)
    return Response(
        {
            "success": False,
            "data": None,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred. Please try again later.",
                "details": {},
                "request_id": request_id,
            },
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
