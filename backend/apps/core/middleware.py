"""
Request ID & HTTP Observability Middleware for VELTO Conversion.

Generates or preserves a unique X-Request-ID correlation header for every request.
Attaches request_id to the request object and HTTP response headers.
Tracks HTTP request duration and records Prometheus API metrics.
"""

import logging
import re
import time
import uuid
from typing import Callable
from django.http import HttpRequest, HttpResponse

from apps.core.logging import log_event
from apps.core.metrics import API_REQUEST_DURATION_SECONDS

logger = logging.getLogger(__name__)

# Permitted characters for client-supplied request IDs (UUIDs, hex, hyphens, alphanumeric)
SAFE_REQUEST_ID_REGEX = re.compile(r"^[a-zA-Z0-9\-_]{1,64}$")
UUID_PATH_REGEX = re.compile(r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}", re.IGNORECASE)


def normalize_route_path(path: str) -> str:
    """Replace UUIDs or dynamic parameters with fixed placeholder for low-cardinality metric labels."""
    return UUID_PATH_REGEX.sub("{id}", path)


class RequestIdMiddleware:
    """
    Middleware enforcing request correlation, HTTP duration measurement, and metrics emission.
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
        start_time = time.monotonic()

        response = self.get_response(request)
        response["X-Request-ID"] = request_id

        duration_sec = time.monotonic() - start_time
        duration_ms = int(duration_sec * 1000)

        # Normalize route for metrics to prevent label cardinality explosion
        normalized_route = normalize_route_path(request.path)
        method = request.method or "GET"
        status_code = str(response.status_code)

        API_REQUEST_DURATION_SECONDS.labels(
            method=method,
            route=normalized_route,
            status_code=status_code,
        ).observe(duration_sec)

        user_id = ""
        if hasattr(request, "user") and request.user.is_authenticated:
            user_id = str(request.user.id)

        event_name = "http.request.completed" if response.status_code < 400 else "http.request.failed"
        log_level = logging.INFO if response.status_code < 400 else (logging.WARNING if response.status_code < 500 else logging.ERROR)

        # Suppress excessive health check polling log volume
        if not (request.path in ("/health/", "/ready/", "/api/v1/health/", "/api/v1/ready/", "/internal/metrics/") and response.status_code == 200):
            log_event(
                logger,
                log_level,
                event_name,
                f"HTTP {method} {request.path} -> {response.status_code} ({duration_ms}ms)",
                request_id=request_id,
                user_id=user_id,
                status=status_code,
                duration_ms=duration_ms,
            )

        return response
