"""
VELTO Conversion — Root URL configuration.
"""

from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from apps.core.views import HealthCheckView, ReadinessCheckView, MetricsView, OperationalMonitoringView
from apps.conversions.views import PdfUtilitiesView, QueueStatusView

urlpatterns = [
    # Django admin (internal operational use)
    path("admin/", admin.site.urls),

    # Top-level Health, Readiness, and Prometheus Metrics endpoints
    path("health/", HealthCheckView.as_view(), name="health"),
    path("ready/", ReadinessCheckView.as_view(), name="readiness"),
    path("internal/metrics/", MetricsView.as_view(), name="internal-metrics"),

    # Versioned API V1 endpoints (/api/v1/)
    path("api/v1/health/", HealthCheckView.as_view(), name="v1-health"),
    path("api/v1/ready/", ReadinessCheckView.as_view(), name="v1-readiness"),
    path("api/v1/internal/operations/", OperationalMonitoringView.as_view(), name="v1-internal-operations"),
    path("api/v1/auth/", include(("apps.users.urls", "v1-auth"), namespace="v1-auth")),
    path("api/v1/conversions/", include(("apps.conversions.urls", "v1-conversions"), namespace="v1-conversions")),
    path("api/v1/pdf/utilities/", PdfUtilitiesView.as_view(), name="v1-pdf-utilities"),

    # Legacy & Backward-Compatible API Routes
    path("api/", include("apps.core.urls")),
    path("api/conversions/", include("apps.conversions.urls")),
    path("api/jobs/", include(("apps.conversions.urls", "jobs"), namespace="jobs")),
    path("api/history/", include("apps.history.urls")),
    path("api/internal/queue-status/", QueueStatusView.as_view(), name="internal-queue-status"),

    # OpenAPI 3 Schema & Interactive Documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]
