"""
Core Infrastructure & Observability Views for VELTO Conversion.

Provides:
- HealthCheckView: Lightweight liveness check (GET /health/ and GET /api/v1/health/).
- ReadinessCheckView: Runtime dependency readiness check (GET /ready/ and GET /api/v1/ready/).
- MetricsView: Prometheus metric exposition endpoint (GET /internal/metrics/).
- OperationalMonitoringView: Staff-only operational statistics (GET /api/v1/internal/operations/).
"""

import logging
import os
import time
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection, models
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from apps.conversions.engines.libreoffice import find_libreoffice_executable
from apps.conversions.models import ConversionJob, JobStatus
from apps.conversions.serializers import (
    ErrorResponseSerializer,
    HealthCheckSerializer,
    ReadinessCheckSerializer,
)
from apps.users.models import UserProfile

User = get_user_model()
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

    Verifies readiness of runtime dependencies (Database, Temporary Storage, Redis, Celery).
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

        # 3. Redis Connectivity Check
        try:
            from django.core.cache import cache
            cache.set("velto_readiness_ping", "ok", timeout=5)
            if cache.get("velto_readiness_ping") == "ok":
                checks["redis"] = "ok"
            else:
                checks["redis"] = "degraded"
        except Exception as exc:
            logger.warning("Readiness check: Redis ping notice: %s", exc)
            checks["redis"] = "degraded"

        # 4. Celery Worker Check (short 0.5s timeout)
        try:
            from config.celery import app as celery_app
            i = celery_app.control.inspect(timeout=0.5)
            ping_res = i.ping()
            if ping_res:
                checks["celery"] = "ok"
            else:
                checks["celery"] = "degraded"
        except Exception as exc:
            logger.warning("Readiness check: Celery inspect notice: %s", exc)
            checks["celery"] = "degraded"

        # 5. Optional LibreOffice Check
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


class MetricsView(APIView):
    """
    GET /internal/metrics/

    Exposes Prometheus format metrics.
    Authorized via METRICS_TOKEN header/bearer or IsAdminUser staff credentials.
    """

    authentication_classes = []
    permission_classes = []

    @extend_schema(exclude=True)
    def get(self, request):
        configured_token = (getattr(settings, "METRICS_TOKEN", None) or os.environ.get("METRICS_TOKEN", "") or "").strip()
        header_token = request.headers.get("X-Metrics-Token", "").strip()
        auth_header = request.headers.get("Authorization", "").strip()

        authorized = False

        if configured_token:
            if header_token == configured_token:
                authorized = True
            elif auth_header.startswith("Bearer ") and auth_header.split(" ", 1)[1].strip() == configured_token:
                authorized = True

        if not authorized and getattr(request, "user", None) and request.user.is_authenticated and request.user.is_staff:
            authorized = True

        if not authorized:
            return Response(
                {"error": True, "message": "Unauthorized access to metrics endpoint."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        output = generate_latest()
        return HttpResponse(output, content_type=CONTENT_TYPE_LATEST)


class OperationalMonitoringView(APIView):
    """
    GET /api/v1/internal/operations/

    Staff-only endpoint returning system operational statistics and aggregate metrics.
    """

    permission_classes = [IsAdminUser]

    @extend_schema(
        summary="Operational Monitoring Metrics",
        description="Returns aggregated system metrics, user counts, queue status, and conversion statistics (Staff only).",
        tags=["System"],
        operation_id="v1_internal_operations",
    )
    def get(self, request):
        total_users = User.objects.count()
        verified_users = UserProfile.objects.filter(is_email_verified=True).count()
        active_users = User.objects.filter(is_active=True).count()

        total_conversions = ConversionJob.objects.count()
        successful_conversions = ConversionJob.objects.filter(status=JobStatus.COMPLETED).count()
        failed_conversions = ConversionJob.objects.filter(status=JobStatus.FAILED).count()
        cancelled_conversions = ConversionJob.objects.filter(status=JobStatus.CANCELLED).count()

        queued_jobs = ConversionJob.objects.filter(status__in=[JobStatus.QUEUED, JobStatus.PENDING]).count()
        active_jobs = ConversionJob.objects.filter(status__in=[JobStatus.PROCESSING, JobStatus.STARTED, JobStatus.RETRYING]).count()

        avg_duration = ConversionJob.objects.filter(
            status=JobStatus.COMPLETED, duration_ms__isnull=False
        ).aggregate(avg_ms=models.Avg("duration_ms"))["avg_ms"] or 0

        recent_failures = list(
            ConversionJob.objects.filter(status=JobStatus.FAILED)
            .values("error_category")
            .annotate(count=models.Count("id"))
            .order_by("-count")[:5]
        )

        total_storage_bytes = UserProfile.objects.aggregate(total=models.Sum("storage_used_bytes"))["total"] or 0

        return Response(
            {
                "users": {
                    "total": total_users,
                    "verified": verified_users,
                    "active": active_users,
                },
                "conversions": {
                    "total": total_conversions,
                    "successful": successful_conversions,
                    "failed": failed_conversions,
                    "cancelled": cancelled_conversions,
                    "queued": queued_jobs,
                    "active": active_jobs,
                    "average_duration_ms": round(avg_duration, 2),
                },
                "failure_breakdown": recent_failures,
                "storage": {
                    "total_used_bytes": total_storage_bytes,
                },
            },
            status=status.HTTP_200_OK,
        )
