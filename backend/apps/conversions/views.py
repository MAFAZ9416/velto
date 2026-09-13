"""
Views for the conversions app — Security Hardened.

Integrated with:
  - DRF rate throttles (JobCreateRateThrottle, PdfUtilityRateThrottle, OcrRateThrottle, DownloadRateThrottle).
  - Session and User ownership enforcement (check_job_ownership, filter_jobs_for_request).
  - Resource abuse controls (check_concurrent_jobs).
  - Security diagnostics endpoint (GET /api/v1/security/diagnostics/).
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
from apps.conversions.security import (
    DownloadRateThrottle,
    JobCreateRateThrottle,
    OcrRateThrottle,
    PdfUtilityRateThrottle,
    UploadRateThrottle,
    check_concurrent_jobs,
    check_job_ownership,
    filter_jobs_for_request,
    get_security_diagnostics,
)

logger = logging.getLogger(__name__)

DOCX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)

FORMAT_CONTENT_TYPES = {
    "docx": DOCX_CONTENT_TYPE,
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "pdf": "application/pdf",
    "jpg": "image/jpeg",
    "png": "image/png",
}


def _ensure_session_key(request) -> str:
    """Ensure the request has an active Django session and return the session key."""
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


# ── Views ──────────────────────────────────────────────────────────────────────

class SupportedFormatsView(APIView):
    """
    GET /api/conversions/supported-formats/
    Returns the full list of supported source→target format pairs.
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


class SecurityDiagnosticsView(APIView):
    """
    GET /api/v1/security/diagnostics/
    Returns non-sensitive status information on active security controls.
    """
    def get(self, request):
        return Response(get_security_diagnostics(), status=status.HTTP_200_OK)


class ConversionJobListCreateView(APIView):
    """
    GET  /api/conversions/   — list jobs owned by the current session or user.
    POST /api/conversions/   — upload a file, run conversion, return real status.
    """
    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [JobCreateRateThrottle, UploadRateThrottle]

    def get(self, request):
        jobs = filter_jobs_for_request(request)
        serializer = ConversionJobSerializer(jobs, many=True)
        return Response(
            {
                "count": jobs.count(),
                "results": serializer.data,
            }
        )

    def post(self, request):
        check_concurrent_jobs(request)

        data = request.data.copy() if hasattr(request.data, "copy") else dict(request.data)
        file_list = request.FILES.getlist("files") or request.FILES.getlist("file")
        if len(file_list) > 1 and "files" not in data:
            data.setlist("files", file_list) if hasattr(data, "setlist") else data.update({"files": file_list})

        serializer = ConversionJobCreateSerializer(data=data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated = serializer.validated_data
        session_key = _ensure_session_key(request)

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

        job = ConversionService.process_job(job)
        output = ConversionJobSerializer(job)
        http_status = (
            status.HTTP_201_CREATED
            if job.status == JobStatus.COMPLETED
            else status.HTTP_202_ACCEPTED
        )
        return Response(output.data, status=http_status)


class ConversionJobDetailView(APIView):
    """
    GET /api/conversions/{id}/
    Returns a single job after validating ownership.
    """
    def get(self, request, job_id):
        jobs = filter_jobs_for_request(request)
        try:
            job = jobs.get(pk=job_id)
            check_job_ownership(request, job)
        except (ConversionJob.DoesNotExist, ValueError):
            return Response(
                {"error": True, "message": "Conversion job not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as exc:
            return Response(
                {"error": True, "message": str(exc)},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = ConversionJobSerializer(job)
        return Response(serializer.data)


class ConversionJobDownloadView(APIView):
    """
    GET /api/conversions/{id}/download/
    Stream the converted output file to the client.
    """
    throttle_classes = [DownloadRateThrottle]

    def get(self, request, job_id):
        jobs = filter_jobs_for_request(request)
        try:
            job = jobs.get(pk=job_id)
            check_job_ownership(request, job)
        except (ConversionJob.DoesNotExist, ValueError):
            return Response(
                {"error": True, "message": "Conversion job not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if job.status in (JobStatus.PENDING, JobStatus.PROCESSING):
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

        download_name = job.output_filename or f"converted_{job.id}.{job.target_format}"
        if download_name.lower().endswith(".zip") or (output_path and output_path.lower().endswith(".zip")):
            content_type = "application/zip"
        else:
            content_type = FORMAT_CONTENT_TYPES.get(job.target_format, "application/octet-stream")

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
    throttle_classes = [PdfUtilityRateThrottle, UploadRateThrottle]

    def post(self, request):
        check_concurrent_jobs(request)
        from apps.conversions.formats import ALL_PDF_OPERATIONS
        operation = request.data.get("operation")
        if operation not in ALL_PDF_OPERATIONS:
            return Response(
                {"error": True, "message": f"unsupported_operation: Invalid or missing PDF utility operation. Supported: {', '.join(ALL_PDF_OPERATIONS)}."},
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

        for key in ("split_mode", "pages", "scope", "profile", "position", "color", "text", "password", "user_password", "owner_password", "mode", "title", "author", "subject", "keywords", "creator", "producer", "prefix", "suffix", "format_style"):
            if key in request.data:
                options[key] = request.data.get(key)

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
            except (ValueError, TypeError):
                pass

        if "rotation" in request.data:
            rot_val = request.data.get("rotation")
            try:
                options["rotation"] = int(rot_val)
            except (ValueError, TypeError):
                options["rotation"] = rot_val

        if "opacity" in request.data:
            try:
                options["opacity"] = float(request.data.get("opacity"))
            except (ValueError, TypeError):
                pass

        if "font_size" in request.data:
            try:
                options["font_size"] = float(request.data.get("font_size"))
            except (ValueError, TypeError):
                pass

        if "start_number" in request.data:
            try:
                options["start_number"] = int(request.data.get("start_number"))
            except (ValueError, TypeError):
                pass

        if "permissions" in request.data:
            try:
                options["permissions"] = int(request.data.get("permissions"))
            except (ValueError, TypeError):
                pass

        if operation == "pdf_compress" and "profile" not in options:
            options["profile"] = "lossless"

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


class OcrUtilitiesView(APIView):
    """
    POST /api/v1/ocr/ — Dedicated API endpoint for OCR Utility operations.
    """
    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [OcrRateThrottle, UploadRateThrottle]

    def post(self, request):
        check_concurrent_jobs(request)
        from apps.conversions.formats import ALL_OCR_OPERATIONS
        operation = request.data.get("operation")
        if operation not in ALL_OCR_OPERATIONS:
            return Response(
                {
                    "error": True,
                    "message": f"unsupported_operation: Invalid or missing OCR operation. Supported: {', '.join(ALL_OCR_OPERATIONS)}.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response(
                {"error": True, "message": "invalid_file: An uploaded input file ('file') is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        filename = file_obj.name.lower()
        if operation == "ocr_image_to_searchable_pdf":
            ext = Path(filename).suffix.lstrip(".")
            source_format = ext if ext in ("jpg", "jpeg", "png", "webp", "bmp", "tiff", "tif") else "jpg"
            if source_format in ("jpeg", "tif"):
                source_format = "jpg" if source_format == "jpeg" else "tiff"
            target_format = "pdf"
        elif operation == "ocr_image_to_txt":
            ext = Path(filename).suffix.lstrip(".")
            source_format = ext if ext in ("jpg", "jpeg", "png", "webp", "bmp", "tiff", "tif") else "jpg"
            if source_format in ("jpeg", "tif"):
                source_format = "jpg" if source_format == "jpeg" else "tiff"
            target_format = "txt"
        elif operation == "ocr_pdf_to_txt":
            source_format = "pdf"
            target_format = "txt"
        elif operation == "ocr_scanned_pdf_to_searchable_pdf":
            source_format = "pdf"
            target_format = "pdf"
        else:
            return Response(
                {"error": True, "message": "unsupported_operation: Invalid OCR operation."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        options = {"operation": operation}

        for key in ("language", "preserve_layout"):
            if key in request.data:
                options[key] = request.data.get(key)

        if "dpi" in request.data:
            try:
                options["dpi"] = int(request.data.get("dpi"))
            except (ValueError, TypeError):
                pass

        if "page_segmentation_mode" in request.data or "psm" in request.data:
            psm_val = request.data.get("page_segmentation_mode", request.data.get("psm"))
            try:
                options["page_segmentation_mode"] = int(psm_val)
                options["psm"] = int(psm_val)
            except (ValueError, TypeError):
                pass

        session_key = _ensure_session_key(request)

        try:
            job = ConversionService.create_job(
                source_format=source_format,
                target_format=target_format,
                uploaded_file=file_obj,
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
