"""
Standardized API Success Envelope Renderer for VELTO Conversion.

Formats successful REST API responses into the unified JSON envelope:
{
  "success": true,
  "data": { ... },
  "error": null
}

Rules:
- Bypasses binary/file stream responses (FileResponse, StreamingHttpResponse).
- Bypasses OpenAPI schema endpoints, Swagger/Redoc UI views, and non-JSON media types.
- Bypasses error responses (>= 400 status codes) or responses already wrapped in an envelope.
- Preserves pagination metadata inside data.
"""

from typing import Any
from django.http import FileResponse, StreamingHttpResponse
from rest_framework.renderers import JSONRenderer


class VeltoResponseRenderer(JSONRenderer):
    """
    Custom JSON renderer enforcing standard envelope responses for success payloads.
    """

    def render(
        self,
        data: Any,
        accepted_media_type: str | None = None,
        renderer_context: dict[str, Any] | None = None,
    ) -> bytes:
        renderer_context = renderer_context or {}
        response = renderer_context.get("response")
        request = renderer_context.get("request")

        # 1. Skip non-dict/file streams or responses without context
        if response is None:
            return super().render(data, accepted_media_type, renderer_context)

        # 2. Skip binary files, redirects, error status codes (>= 400)
        if isinstance(response, (FileResponse, StreamingHttpResponse)):
            return data

        if 300 <= response.status_code < 400 or response.status_code >= 400:
            return super().render(data, accepted_media_type, renderer_context)

        # 3. Skip OpenAPI schema, docs views, or HTML/non-JSON media types
        path = getattr(request, "path", "") if request else ""
        if (
            "/api/schema" in path
            or "/api/docs" in path
            or "/api/redoc" in path
            or "schema" in (accepted_media_type or "")
            or "text/html" in (accepted_media_type or "")
        ):
            return super().render(data, accepted_media_type, renderer_context)

        # 4. Only wrap versioned routes (/api/v1/) and system health/readiness endpoints
        is_versioned_or_system = (
            path.startswith("/api/v1/")
            or path in ("/health/", "/ready/", "/health", "/ready")
        )
        if not is_versioned_or_system:
            return super().render(data, accepted_media_type, renderer_context)

        # 5. Avoid double wrapping if response is already enveloped
        if isinstance(data, dict) and "success" in data and ("data" in data or "error" in data):
            return super().render(data, accepted_media_type, renderer_context)

        # 6. Envelope standard success payload for versioned/system endpoints
        enveloped = {
            "success": True,
            "data": data if data is not None else {},
            "error": None,
        }

        return super().render(enveloped, accepted_media_type, renderer_context)
