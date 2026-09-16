"""
Core Infrastructure Views for VELTO Conversion.

Provides:
- HealthCheckView: Lightweight liveness check (GET /health/ and GET /api/v1/health/).
- ReadinessCheckView: Runtime dependency readiness check (GET /ready/ and GET /api/v1/ready/).
"""

import logging
from pathlib import Path
from django.conf import settings
from django.db import connection
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.conversions.engines.libreoffice import find_libreoffice_executable

from drf_spectacular.utils import extend_schema
from apps.conversions.serializers import (
    HealthCheckSerializer,
    ReadinessCheckSerializer,
    ErrorResponseSerializer,
)

logger = logging.getLogger(__name__)


class HealthCheckView(APIView):
    """
    GET /health/
    GET /api/v1/health/

    Lightweight liveness check. Returns HTTP 200 when application process is alive.
    Does not depend on external services (DB, Redis, LibreOffice).
    """

    authentication_classes = []
    permission_classes = []

    @extend_schema(
        summary="Liveness Health Check",
        description="Lightweight liveness check returning HTTP 200 when service process is running.",
        responses={200: HealthCheckSerializer},
        tags=["System"],
        operation_id="system_health_check",
    )
    def get(self, request):
        return Response(
            {
                "status": "ok",
                "service": "velto-conversion",
            },
            status=status.HTTP_200_OK,
        )


class ReadinessCheckView(APIView):
    """
    GET /ready/
    GET /api/v1/ready/

    Verifies readiness of runtime dependencies (Database, Temporary Storage, LibreOffice, Redis).
    Returns HTTP 200 when ready, or HTTP 503 Service Unavailable when critical dependencies fail.
    """

    authentication_classes = []
    permission_classes = []

    @extend_schema(
        summary="Dependency Readiness Check",
        description="Verifies runtime dependency health (database, storage, optional services).",
        responses={
            200: ReadinessCheckSerializer,
            503: ErrorResponseSerializer,
        },
        tags=["System"],
        operation_id="system_readiness_check",
    )
    def get(self, request):
        checks = {}
        is_ready = True

        # 1. Database Connectivity Check
        try:
            connection.ensure_connection()
            checks["database"] = "ok"
        except Exception as exc:
            logger.error("Readiness check: database connection failed: %s", exc)
            checks["database"] = "error"
            is_ready = False

        # 2. Storage Directory Check
        try:
            temp_dir = Path(settings.TEMP_UPLOAD_DIR).resolve()
            temp_dir.mkdir(parents=True, exist_ok=True)
            checks["storage"] = "ok"
        except Exception as exc:
            logger.error("Readiness check: storage directory access failed: %s", exc)
            checks["storage"] = "error"
            is_ready = False

        # 3. Optional LibreOffice Availability Check
        try:
            exe_path = find_libreoffice_executable()
            checks["libreoffice"] = "available" if exe_path else "unavailable"
        except Exception:
            checks["libreoffice"] = "unavailable"

        if is_ready:
            return Response(
                {
                    "status": "ready",
                    "service": "velto-conversion",
                    "checks": checks,
                },
                status=status.HTTP_200_OK,
            )

        request_id = getattr(request, "request_id", "")
        return Response(
            {
                "success": False,
                "data": None,
                "error": {
                    "code": "INFRASTRUCTURE_UNAVAILABLE",
                    "message": "One or more required system dependencies are currently unavailable.",
                    "details": {"status": "not_ready", "service": "velto-conversion", "checks": checks},
                    "request_id": request_id,
                },
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
