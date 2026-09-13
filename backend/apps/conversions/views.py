"""
Views for the conversions app — Phase 2.

Changes from Phase 1:
  - POST /api/conversions/ now calls ConversionService.process_job() synchronously
    after creating the job, so the response reflects the real conversion status.
  - GET /api/conversions/{id}/download/ added — protected download endpoint.
"""

import logging
import os
from pathlib import Path

from django.http import FileResponse
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.conversions.formats import get_supported_formats_response
from apps.conversions.models import ConversionJob, JobStatus
from apps.conversions.serializers import (
    ConversionJobCreateSerializer,
    ConversionJobSerializer,
)
from apps.conversions.services import ConversionService, ConversionServiceError

logger = logging.getLogger(__name__)

# MIME type for .docx files
DOCX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)

# Map target format → MIME type for the download response
FORMAT_CONTENT_TYPES = {
    "docx": DOCX_CONTENT_TYPE,
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "pdf": "application/pdf",
    "jpg": "image/jpeg",
    "png": "image/png",
}


# ── Helper: session key management ────────────────────────────────────────────

def _ensure_session_key(request) -> str:
    """
    Ensure the request has an active Django session and return the session key.

    Creates a new session if none exists — this is what issues the velto_session
    cookie to the browser on first contact.
    """
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


def _filter_jobs_for_request(request):
    """
    Return a QuerySet of ConversionJobs the current request is authorised to see.

    Authenticated users see their own jobs (by user FK).
    Anonymous users see jobs tied to their session key.
    """
    if request.user and request.user.is_authenticated:
        return ConversionJob.objects.filter(user=request.user)
    session_key = request.session.session_key
    if not session_key:
        return ConversionJob.objects.none()
    return ConversionJob.objects.filter(session_key=session_key, user__isnull=True)


# ── Views ──────────────────────────────────────────────────────────────────────

class SupportedFormatsView(APIView):
    """
    GET /api/conversions/supported-formats/

    Returns the full list of supported source→target format pairs.
    No authentication required.
    """

    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response(
            {
                "count": len(get_supported_formats_response()),
                "formats": get_supported_formats_response(),
            }
        )


class ConversionJobListCreateView(APIView):
    """
    GET  /api/conversions/   — list jobs owned by the current session or user.
    POST /api/conversions/   — upload a file, run conversion, return real status.
    """

    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        jobs = _filter_jobs_for_request(request)
        serializer = ConversionJobSerializer(jobs, many=True)
        return Response(
            {
                "count": jobs.count(),
                "results": serializer.data,
            }
        )

    def post(self, request):
        # Support multi-file upload lists passed under 'file' or 'files'
        data = request.data.copy() if hasattr(request.data, "copy") else dict(request.data)
        file_list = request.FILES.getlist("files") or request.FILES.getlist("file")
        if len(file_list) > 1 and "files" not in data:
            data.setlist("files", file_list) if hasattr(data, "setlist") else data.update({"files": file_list})

        serializer = ConversionJobCreateSerializer(data=data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated = serializer.validated_data
        session_key = _ensure_session_key(request)

        # ── Create pending job and stage input file ───────────────────────────
        try:
            job = ConversionService.create_job(
                source_format=validated["source_format"],
                target_format=validated["target_format"],
                uploaded_file=validated.get("file"),
                uploaded_files=validated.get("files") or (file_list if len(file_list) > 1 else None),
                options=validated.get("options", {}),
                session_key=session_key,
                user=request.user if request.user.is_authenticated else None,
            )
        except ConversionServiceError as exc:
            logger.warning("ConversionService.create_job error: %s", exc)
            return Response(
                {"error": True, "message": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Run the conversion synchronously (Phase 2) ────────────────────────
        # In Phase 3 this will be dispatched to a Celery worker instead.
        job = ConversionService.process_job(job)

        # ── Return the real status — never fake success ───────────────────────
        output = ConversionJobSerializer(job)
        http_status = (
            status.HTTP_201_CREATED
            if job.status == JobStatus.COMPLETED
            else status.HTTP_202_ACCEPTED   # pending or failed
        )
        return Response(output.data, status=http_status)


class ConversionJobDetailView(APIView):
    """
    GET /api/conversions/{id}/

    Returns a single job. Anonymous users may only retrieve their own jobs.
    """

    def get(self, request, job_id):
        jobs = _filter_jobs_for_request(request)
        try:
            job = jobs.get(pk=job_id)
        except (ConversionJob.DoesNotExist, ValueError):
            return Response(
                {"error": True, "message": "Conversion job not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = ConversionJobSerializer(job)
        return Response(serializer.data)


class ConversionJobDownloadView(APIView):
    """
    GET /api/conversions/{id}/download/

    Stream the converted output file to the client.

    Security:
      - Ownership is enforced via _filter_jobs_for_request (session/user).
      - Only completed jobs with a valid output file on disk are served.
      - Internal filesystem paths are never exposed in the response.
      - Content-Disposition uses a sanitised output_filename, not the raw path.
    """

    def get(self, request, job_id):
        # ── Ownership check ───────────────────────────────────────────────────
        jobs = _filter_jobs_for_request(request)
        try:
            job = jobs.get(pk=job_id)
        except (ConversionJob.DoesNotExist, ValueError):
            return Response(
                {"error": True, "message": "Conversion job not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # ── Status checks ─────────────────────────────────────────────────────
        if job.status == JobStatus.PENDING or job.status == JobStatus.PROCESSING:
            return Response(
                {
                    "error": True,
                    "message": "Conversion is still in progress. Please try again shortly.",
                    "status": job.status,
                },
                status=status.HTTP_202_ACCEPTED,
            )

        if job.status == JobStatus.FAILED:
            return Response(
                {
                    "error": True,
                    "message": "Conversion failed. No output file is available.",
                    "detail": job.error_message or "See job details for more information.",
                    "status": job.status,
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        if job.status == JobStatus.CANCELLED:
            return Response(
                {"error": True, "message": "This conversion job was cancelled."},
                status=status.HTTP_410_GONE,
            )

        # ── Locate output file ────────────────────────────────────────────────
        output_path = ConversionService.get_job_output(job)
        if output_path is None:
            return Response(
                {
                    "error": True,
                    "message": (
                        "The converted file is no longer available. "
                        "Temporary files are cleaned up periodically. "
                        "Please submit a new conversion request."
                    ),
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # ── Build Content-Disposition filename ────────────────────────────────
        # Use the stored output_filename (already sanitised), fall back to stem of job id.
        download_name = job.output_filename or f"converted_{job.id}.{job.target_format}"
        if download_name.lower().endswith(".zip") or (output_path and output_path.lower().endswith(".zip")):
            content_type = "application/zip"
        else:
            content_type = FORMAT_CONTENT_TYPES.get(job.target_format, "application/octet-stream")

        # ── Stream file ───────────────────────────────────────────────────────
        try:
            response = FileResponse(
                open(output_path, "rb"),
                content_type=content_type,
                as_attachment=True,
                filename=download_name,
            )
            return response
        except OSError as exc:
            logger.error("Download failed for job %s: %s", job.id, exc)
            return Response(
                {"error": True, "message": "File could not be read. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PdfUtilitiesView(APIView):
    """
    POST /api/v1/pdf/utilities/ — Dedicated API endpoint for PDF Utility operations.
    """
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        operation = request.data.get("operation")
        if operation not in ("pdf_merge", "pdf_split", "pdf_extract_pages"):
            return Response(
                {"error": True, "message": "unsupported_operation: Invalid or missing PDF utility operation. Supported: pdf_merge, pdf_split, pdf_extract_pages."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        target_format = "zip" if operation == "pdf_split" else "pdf"
        file_single = request.FILES.get("file")
        file_list = request.FILES.getlist("files") or request.FILES.getlist("file[]") or request.FILES.getlist("files[]")

        if not file_single and not file_list:
            return Response(
                {"error": True, "message": "invalid_pdf: At least one uploaded PDF file ('file' or 'files') is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        options = {"operation": operation}
        if "split_mode" in request.data:
            options["split_mode"] = request.data.get("split_mode")
        if "ranges" in request.data:
            ranges_val = request.data.get("ranges")
            if isinstance(ranges_val, str) and (ranges_val.startswith("[") or "," in ranges_val):
                try:
                    import json
                    options["ranges"] = json.loads(ranges_val)
                except Exception:
                    options["ranges"] = [r.strip() for r in ranges_val.split(",") if r.strip()]
            else:
                options["ranges"] = ranges_val if isinstance(ranges_val, list) else [ranges_val]
        if "pages_per_file" in request.data:
            try:
                options["pages_per_file"] = int(request.data.get("pages_per_file"))
            except ValueError:
                pass
        if "pages" in request.data:
            options["pages"] = request.data.get("pages")

        session_key = _ensure_session_key(request)

        try:
            job = ConversionService.create_job(
                source_format="pdf",
                target_format=target_format,
                uploaded_file=file_single if not file_list else None,
                uploaded_files=file_list if file_list else None,
                options=options,
                session_key=session_key,
                user=request.user if request.user.is_authenticated else None,
            )
        except ConversionServiceError as exc:
            return Response(
                {"error": True, "message": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        job = ConversionService.process_job(job)
        output = ConversionJobSerializer(job)
        http_status = status.HTTP_201_CREATED if job.status == JobStatus.COMPLETED else status.HTTP_202_ACCEPTED
        return Response(output.data, status=http_status)

