"""
URL patterns for the conversions app — Security Hardened, Job Processing & Object Storage Enabled.
"""

from django.urls import path
from apps.conversions.views import (
    SupportedFormatsView,
    ConversionJobListCreateView,
    ConversionJobDetailView,
    ConversionJobCancelView,
    ConversionJobDownloadView,
    QueueStatusView,
    PdfUtilitiesView,
    OcrUtilitiesView,
    SecurityDiagnosticsView,
    PresignedUploadUrlView,
    FinalizeUploadView,
    PresignedDownloadUrlView,
)

app_name = "conversions"

urlpatterns = [
    # GET /api/conversions/supported-formats/
    path("supported-formats/", SupportedFormatsView.as_view(), name="supported-formats"),

    # GET /api/conversions/security/diagnostics/
    path("security/diagnostics/", SecurityDiagnosticsView.as_view(), name="security-diagnostics"),

    # GET /api/conversions/queue-status/
    path("queue-status/", QueueStatusView.as_view(), name="queue-status"),

    # POST /api/conversions/upload-url/
    path("upload-url/", PresignedUploadUrlView.as_view(), name="upload-url"),

    # POST /api/conversions/pdf/utilities/
    path("pdf/utilities/", PdfUtilitiesView.as_view(), name="pdf-utilities"),

    # POST /api/conversions/ocr/
    path("ocr/", OcrUtilitiesView.as_view(), name="ocr-utilities"),

    # GET  /api/conversions/
    # POST /api/conversions/
    path("", ConversionJobListCreateView.as_view(), name="job-list-create"),

    # GET /api/conversions/{job_id}/
    path("<uuid:job_id>/", ConversionJobDetailView.as_view(), name="job-detail"),

    # POST /api/conversions/{job_id}/cancel/
    path("<uuid:job_id>/cancel/", ConversionJobCancelView.as_view(), name="job-cancel"),

    # POST /api/conversions/{job_id}/finalize-upload/
    path("<uuid:job_id>/finalize-upload/", FinalizeUploadView.as_view(), name="job-finalize-upload"),

    # GET /api/conversions/{job_id}/download-url/
    path("<uuid:job_id>/download-url/", PresignedDownloadUrlView.as_view(), name="job-download-url"),

    # GET /api/conversions/{job_id}/download/
    path("<uuid:job_id>/download/", ConversionJobDownloadView.as_view(), name="job-download"),
]
