"""
Request ID Middleware for VELTO Conversion.

Generates or preserves a unique X-Request-ID correlation header for every request.
Attaches request_id to the request object and HTTP response headers.
"""

import re
import uuid
from typing import Callable
from django.http import HttpRequest, HttpResponse

# Permitted characters for client-supplied request IDs (UUIDs, hex, hyphens, alphanumeric)
SAFE_REQUEST_ID_REGEX = re.compile(r"^[a-zA-Z0-9\-_]{1,64}$")


class RequestIdMiddleware:
    """
    Middleware that ensures every incoming HTTP request has an associated request_id.

    - Reads X-Request-ID header if supplied by client or load balancer.
    - Validates length (max 64 chars) and safe character set.
    - Generates a new UUID hex string if missing or invalid.
    - Sets request.request_id attribute.
    - Adds X-Request-ID header to the HTTP response.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        raw_header = request.headers.get("X-Request-ID") or request.META.get("HTTP_X_REQUEST_ID", "")
        clean_header = str(raw_header).strip()

        if clean_header and SAFE_REQUEST_ID_REGEX.match(clean_header):
            request_id = clean_header
        else:
            request_id = uuid.uuid4().hex

        request.request_id = request_id

        response = self.get_response(request)
        response["X-Request-ID"] = request_id
        return response
