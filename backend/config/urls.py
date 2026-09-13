"""
VELTO Conversion — Root URL configuration.
"""

from django.contrib import admin
from django.urls import path, include
from apps.conversions.views import PdfUtilitiesView, QueueStatusView

urlpatterns = [
    # Django admin (internal use)
    path("admin/", admin.site.urls),

    # Core: health check
    path("api/", include("apps.core.urls")),

    # PDF V1 Utilities: POST /api/v1/pdf/utilities/
    path("api/v1/pdf/utilities/", PdfUtilitiesView.as_view(), name="pdf-v1-utilities"),

    # Conversions API: formats, job creation, job list, job detail, download, cancel
    path("api/conversions/", include("apps.conversions.urls")),

    # Jobs API alias: /api/jobs/ maps to conversions endpoints
    path("api/jobs/", include(("apps.conversions.urls", "jobs"), namespace="jobs")),

    # Internal queue status route
    path("api/internal/queue-status/", QueueStatusView.as_view(), name="internal-queue-status"),

    # History: user/session conversion history
    path("api/history/", include("apps.history.urls")),
]
