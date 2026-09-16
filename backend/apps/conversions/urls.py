"""
URL patterns for the conversions app — Public API Contract, OpenAPI & Versioned Endpoints.
"""

from django.urls import path
from apps.conversions.views import (
    SupportedFormatsView,
    ConversionJobListCreateView,
    ConversionJobDetailView,
    ConversionJobCancelView,
    ConversionJobRetryView,
    ConversionHistoryListView,
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
    # Format pair discovery
    path("formats/", SupportedFormatsView.as_view(), name="formats"),
    path("supported-formats/", SupportedFormatsView.as_view(), name="supported-formats"),

    # History & pagination
    path("history/", ConversionHistoryListView.as_view(), name="history"),

    # Diagnostics & Queue
    path("security/diagnostics/", SecurityDiagnosticsView.as_view(), name="security-diagnostics"),
    path("queue-status/", QueueStatusView.as_view(), name="queue-status"),

    # Upload workflow
    path("upload-url/", PresignedUploadUrlView.as_view(), name="upload-url"),
    path("<uuid:job_id>/finalize-upload/", FinalizeUploadView.as_view(), name="job-finalize-upload"),

    # Document & OCR utilities
    path("pdf/utilities/", PdfUtilitiesView.as_view(), name="pdf-utilities"),
    path("ocr/", OcrUtilitiesView.as_view(), name="ocr-utilities"),

    # Jobs collection (GET list, POST upload & create job)
    path("", ConversionJobListCreateView.as_view(), name="job-list-create"),

    # Job lifecycle & actions
    path("<uuid:job_id>/", ConversionJobDetailView.as_view(), name="job-detail"),
    path("<uuid:job_id>/cancel/", ConversionJobCancelView.as_view(), name="job-cancel"),
    path("<uuid:job_id>/retry/", ConversionJobRetryView.as_view(), name="job-retry"),
    path("<uuid:job_id>/download-url/", PresignedDownloadUrlView.as_view(), name="job-download-url"),
    path("<uuid:job_id>/download/", ConversionJobDownloadView.as_view(), name="job-download"),
]
