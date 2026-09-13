"""
Custom DRF exception handler for VELTO Conversion.

Wraps all errors in a consistent envelope:
{
    "error": true,
    "code": "HTTP status code",
    "message": "Human-readable summary",
    "details": { ... }   # field-level validation errors, when available
}
"""

import logging

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)


def velto_exception_handler(exc, context):
    """
    Call the default DRF handler first, then reformat the response envelope.
    Unhandled exceptions (500s) are left to Django's standard error handling.
    """
    response = exception_handler(exc, context)

    if response is None:
        # Django will handle 500s; log and re-raise.
        logger.exception("Unhandled exception in view %s", context.get("view"))
        return None

    # Normalise validation errors (field → list of strings)
    details = {}
    message = "An error occurred."

    if isinstance(response.data, dict):
        # DRF validation errors come as {field: [errors]} or {detail: "..."}
        if "detail" in response.data:
            message = str(response.data["detail"])
        else:
            message = "Validation failed."
            details = {
                field: [str(e) for e in errors] if isinstance(errors, list) else [str(errors)]
                for field, errors in response.data.items()
            }
    elif isinstance(response.data, list):
        message = "; ".join(str(e) for e in response.data)

    response.data = {
        "error": True,
        "code": response.status_code,
        "message": message,
        "details": details,
    }
    return response
