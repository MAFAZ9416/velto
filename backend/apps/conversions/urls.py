"""
URL patterns for the conversions app — Security Hardened.
"""

from django.urls import path
from apps.conversions.views import (
    SupportedFormatsView,
    ConversionJobListCreateView,
    ConversionJobDetailView,
    ConversionJobDownloadView,
    PdfUtilitiesView,
    OcrUtilitiesView,
    SecurityDiagnosticsView,
)

app_name = "conversions"

urlpatterns = [
    # GET /api/conversions/supported-formats/
    path("supported-formats/", SupportedFormatsView.as_view(), name="supported-formats"),

    # GET /api/conversions/security/diagnostics/
    path("security/diagnostics/", SecurityDiagnosticsView.as_view(), name="security-diagnostics"),

    # POST /api/conversions/pdf/utilities/
    path("pdf/utilities/", PdfUtilitiesView.as_view(), name="pdf-utilities"),

    # POST /api/conversions/ocr/
    path("ocr/", OcrUtilitiesView.as_view(), name="ocr-utilities"),

    # GET  /api/conversions/
    # POST /api/conversions/
    path("", ConversionJobListCreateView.as_view(), name="job-list-create"),

    # GET /api/conversions/{job_id}/
    path("<uuid:job_id>/", ConversionJobDetailView.as_view(), name="job-detail"),

    # GET /api/conversions/{job_id}/download/
    path("<uuid:job_id>/download/", ConversionJobDownloadView.as_view(), name="job-download"),
]
