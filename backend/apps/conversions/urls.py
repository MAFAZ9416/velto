"""
URL patterns for the conversions app — Phase 2.
"""

from django.urls import path
from apps.conversions.views import (
    SupportedFormatsView,
    ConversionJobListCreateView,
    ConversionJobDetailView,
    ConversionJobDownloadView,
)

app_name = "conversions"

urlpatterns = [
    # GET /api/conversions/supported-formats/
    path("supported-formats/", SupportedFormatsView.as_view(), name="supported-formats"),

    # GET  /api/conversions/
    # POST /api/conversions/
    path("", ConversionJobListCreateView.as_view(), name="job-list-create"),

    # GET /api/conversions/{job_id}/
    path("<uuid:job_id>/", ConversionJobDetailView.as_view(), name="job-detail"),

    # GET /api/conversions/{job_id}/download/
    path("<uuid:job_id>/download/", ConversionJobDownloadView.as_view(), name="job-download"),
]
