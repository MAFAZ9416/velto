"""
Views for the conversions app — Security Hardened & Background Job Processing Enabled.

Integrated with:
  - Celery background job processing via ConversionService.dispatch_job.
  - DRF rate throttles (JobCreateRateThrottle, PdfUtilityRateThrottle, OcrRateThrottle, DownloadRateThrottle, QueueMonitorRateThrottle).
  - Session and User ownership enforcement (check_job_ownership, filter_jobs_for_request).
  - Resource abuse controls (check_concurrent_jobs).
  - Database-authoritative job cancellation endpoint.
  - Staff-only queue monitoring endpoint.
  - Security diagnostics endpoint (GET /api/v1/security/diagnostics/).
"""

import logging
import os
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.http import FileResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema, OpenApiParameter
from apps.conversions.formats import get_supported_formats_response
from apps.conversions.models import ConversionJob, JobStatus
from apps.conversions.serializers import (
    ConversionJobCreateSerializer,
    ConversionJobSerializer,
    FormatDiscoverySerializer,
    RetryJobResponseSerializer,
    CancelJobResponseSerializer,
    DeleteJobResponseSerializer,
    PresignedUploadRequestSerializer,
    PresignedUploadResponseSerializer,
    PresignedDownloadResponseSerializer,
    ConversionHistoryQuerySerializer,
    ErrorResponseSerializer,
)
from apps.conversions.engines.base import ConversionError
from apps.conversions.services import ConversionService, ConversionServiceError
from apps.conversions.security import (
    DownloadRateThrottle,
    JobCreateRateThrottle,
    OcrRateThrottle,
    PdfUtilityRateThrottle,
    QueueMonitorRateThrottle,
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
    GET /api/v1/conversions/formats/
    GET /api/conversions/supported-formats/
    Returns the full list of supported source→target format pairs with metadata.
    """
    authentication_classes = []
    permission_classes = []

    @extend_schema(
        summary="Discover Supported Formats",
        description="Returns list of supported source to target format pairs with MIME types and restrictions.",
        responses={200: FormatDiscoverySerializer(many=True)},
        tags=["Discovery"],
        operation_id="v1_conversions_formats_list",
    )
    def get(self, request):
        from apps.conversions.engines.registry import engine_registry
        from apps.conversions.security.specs import get_format_spec
        from apps.conversions.security.limits import MAX_SINGLE_FILE_SIZE, MAX_PDF_PAGES

        FORMAT_LABELS = {
            "pdf": "PDF",
            "docx": "Word (DOCX)",
            "xlsx": "Excel (XLSX)",
            "pptx": "PowerPoint (PPTX)",
            "jpg": "JPEG Image",
            "png": "PNG Image",
            "txt": "Text",
            "html": "HTML Document",
            "epub": "ePub eBook",
            "md": "Markdown",
            "zip": "ZIP Archive",
            "images": "Multiple Images",
        }

        seen = set()
        formats_list = []
        for key in engine_registry._registry.keys():
            src, tgt = key[0], key[1]
            if (src, tgt) in seen:
                continue
            seen.add((src, tgt))
            try:
                spec_src = get_format_spec(src)
            except KeyError:
                spec_src = None

            try:
                spec_tgt = get_format_spec(tgt)
            except KeyError:
                spec_tgt = None

            src_label = FORMAT_LABELS.get(src, spec_src.format_name.upper() if spec_src else src.upper())
            tgt_label = FORMAT_LABELS.get(tgt, spec_tgt.format_name.upper() if spec_tgt else tgt.upper())

            formats_list.append({
                "source": src,
                "target": tgt,
                "source_label": src_label,
                "target_label": tgt_label,
                "category": "image" if src in ("images", "jpg", "png", "webp", "gif") else "document",
                "enabled": True,
                "mime_types": list(spec_src.allowed_mime_types) if spec_src else [],
                "max_file_size": spec_src.max_file_size if spec_src else MAX_SINGLE_FILE_SIZE,
                "restrictions": {
                    "max_pdf_pages": MAX_PDF_PAGES if src == "pdf" else None,
                },
            })

        return Response(
            {
                "count": len(formats_list),
                "formats": formats_list,
            }
        )


class SecurityDiagnosticsView(APIView):
    """
    GET /api/v1/security/diagnostics/
    Returns non-sensitive status information on active security controls.
    """
    @extend_schema(
        summary="Security Control Diagnostics",
        description="Returns active security control configuration status.",
        tags=["System"],
        operation_id="v1_security_diagnostics",
    )
    def get(self, request):
        return Response(get_security_diagnostics(), status=status.HTTP_200_OK)


class ConversionJobListCreateView(APIView):
    """
    GET  /api/conversions/   — list jobs owned by the current session or user.
    POST /api/conversions/   — upload a file, queue background conversion job, return status.
    """
    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [JobCreateRateThrottle, UploadRateThrottle]

    @extend_schema(
        summary="List Active Conversion Jobs",
        description="Lists conversion jobs created by the current session or authenticated user.",
        responses={200: ConversionJobSerializer(many=True)},
        tags=["Jobs"],
        operation_id="v1_conversions_list",
    )
    def get(self, request):
        jobs = filter_jobs_for_request(request)
        serializer = ConversionJobSerializer(jobs, many=True)
        return Response(
            {
                "count": jobs.count(),
                "results": serializer.data,
            }
        )

    @extend_schema(
        summary="Create and Dispatch Conversion Job",
        description="Uploads input file, validates security controls, and queues background conversion task.",
        request=ConversionJobCreateSerializer,
        responses={
            201: ConversionJobSerializer,
            202: ConversionJobSerializer,
            400: ErrorResponseSerializer,
        },
        tags=["Jobs"],
        operation_id="v1_conversions_create",
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
        except ConversionError as exc:
            logger.warning("ConversionService.create_job error: %s", exc)
            return Response(
                {"error": True, "message": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        job = ConversionService.dispatch_job(job)
        output = ConversionJobSerializer(job)
        http_status = (
            status.HTTP_201_CREATED
            if job.status == JobStatus.COMPLETED
            else status.HTTP_202_ACCEPTED
        )
        return Response(output.data, status=http_status)


class ConversionJobDetailView(APIView):
    """
    GET /api/v1/conversions/{id}/ — Returns job status.
    DELETE /api/v1/conversions/{id}/ — Deletes job and cleans up storage objects.
    """
    @extend_schema(
        summary="Get Job Status and Details",
        description="Returns detailed job status, progress, timestamps, and action availability flags.",
        responses={200: ConversionJobSerializer, 404: ErrorResponseSerializer},
        tags=["Jobs"],
        operation_id="v1_conversions_detail",
    )
    def get(self, request, job_id):
        jobs = filter_jobs_for_request(request)
        try:
            job = jobs.get(pk=job_id)
            check_job_ownership(request, job)
        except (ConversionJob.DoesNotExist, ValueError):
            raise NotFound("Conversion job not found.")
        except OwnershipDenied as exc:
            raise PermissionDenied(str(exc))
        except Exception as exc:
            raise PermissionDenied(str(exc))
        serializer = ConversionJobSerializer(job)
        return Response(serializer.data)

    @extend_schema(
        summary="Delete Conversion Job",
        description="Deletes conversion job and cleans up associated input/output storage files.",
        responses={200: DeleteJobResponseSerializer, 403: ErrorResponseSerializer},
        tags=["Jobs"],
        operation_id="v1_conversions_delete",
    )
    def delete(self, request, job_id):
        jobs = filter_jobs_for_request(request)
        try:
            job = jobs.get(pk=job_id)
            check_job_ownership(request, job)
        except (ConversionJob.DoesNotExist, ValueError):
            return Response(
                {"message": "Job deleted or non-existent."},
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            return Response(
                {"error": True, "message": str(exc)},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            ConversionService.cleanup_job_files(job)
        except Exception as exc:
            logger.warning("Error cleaning up job files for job %s: %s", job_id, exc)

        job.delete()
        return Response(
            {"message": "Conversion job and associated storage objects deleted successfully."},
            status=status.HTTP_200_OK,
        )


class ConversionJobRetryView(APIView):
    """
    POST /api/v1/conversions/{id}/retry/
    Retry a failed or cancelled conversion job.
    """
    @extend_schema(
        summary="Retry Failed or Cancelled Job",
        description="Re-queues a failed or cancelled conversion job if input file is available and retry limit is not exceeded.",
        responses={200: RetryJobResponseSerializer, 400: ErrorResponseSerializer},
        tags=["Jobs"],
        operation_id="v1_conversions_retry",
    )
    def post(self, request, job_id):
        jobs = filter_jobs_for_request(request)
        try:
            job = jobs.get(pk=job_id)
            check_job_ownership(request, job)
        except (ConversionJob.DoesNotExist, ValueError):
            raise NotFound("Conversion job not found.")
        except OwnershipDenied as exc:
            raise PermissionDenied(str(exc))
        except Exception as exc:
            raise PermissionDenied(str(exc))

        if job.status not in (JobStatus.FAILED, JobStatus.CANCELLED):
            raise ValidationError(f"Job in status '{job.status}' cannot be retried. Only failed or cancelled jobs can be retried.")

        if job.retry_count >= job.max_retries:
            raise ValidationError(f"Maximum retry limit ({job.max_retries}) reached for this job.")

        # Confirm input file availability
        input_available = False
        if job.input_storage_key:
            from apps.conversions.storage import get_storage_service
            storage = get_storage_service(job.storage_backend)
            if storage.object_exists(job.input_storage_key):
                input_available = True
        if not input_available and job.input_path and Path(job.input_path).exists():
            input_available = True

        if not input_available:
            raise ValidationError("Input file is no longer available in storage for retry.")

        # Reset job state for retry
        with transaction.atomic():
            job.status = JobStatus.QUEUED
            job.progress = 0
            job.current_stage = "retrying"
            job.stage_message = f"Retrying job (attempt {job.retry_count + 1})."
            job.error_message = ""
            job.error_code = ""
            job.retry_count += 1
            job.started_at = None
            job.completed_at = None
            job.failed_at = None
            job.cancelled_at = None
            job.save()

        job = ConversionService.dispatch_job(job)
        serializer = ConversionJobSerializer(job)
        return Response(
            {
                "original_job_id": str(job.id),
                "new_job_id": str(job.id),
                "status": job.status,
                "message": "Job retry queued successfully.",
                "job": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class ConversionHistoryListView(APIView):
    """
    GET /api/v1/conversions/history/
    GET /api/history/
    Returns user/session conversion history with filtering, pagination, and safe ordering.
    """
    @extend_schema(
        summary="Conversion History List",
        description="Returns user/session conversion history with pagination, date filtering, and safe ordering.",
        parameters=[ConversionHistoryQuerySerializer],
        responses={200: ConversionJobSerializer(many=True)},
        tags=["History"],
        operation_id="v1_conversions_history_list",
    )
    def get(self, request):
        jobs = filter_jobs_for_request(request)

        status_param = request.query_params.get("status")
        if status_param and status_param in [s.value for s in JobStatus]:
            jobs = jobs.filter(status=status_param)

        src_param = request.query_params.get("source_format") or request.query_params.get("source")
        if src_param:
            jobs = jobs.filter(source_format=src_param)

        tgt_param = request.query_params.get("target_format") or request.query_params.get("target")
        if tgt_param:
            jobs = jobs.filter(target_format=tgt_param)

        search_param = request.query_params.get("search")
        if search_param:
            jobs = jobs.filter(original_filename__icontains=search_param.strip())

        date_from = request.query_params.get("date_from")
        if date_from:
            try:
                jobs = jobs.filter(created_at__gte=date_from)
            except Exception:
                pass

        date_to = request.query_params.get("date_to")
        if date_to:
            try:
                jobs = jobs.filter(created_at__lte=date_to)
            except Exception:
                pass

        ordering = request.query_params.get("ordering", "-created_at")
        allowed_ordering = ("created_at", "-created_at", "updated_at", "-updated_at")
        if ordering in allowed_ordering:
            jobs = jobs.order_by(ordering)
        else:
            jobs = jobs.order_by("-created_at")

        try:
            page_size = int(request.query_params.get("page_size", 20))
            page_size = max(1, min(page_size, 100))
        except (ValueError, TypeError):
            page_size = 20

        try:
            page_num = int(request.query_params.get("page", 1))
            page_num = max(1, page_num)
        except (ValueError, TypeError):
            page_num = 1

        total_count = jobs.count()
        start_idx = (page_num - 1) * page_size
        end_idx = start_idx + page_size
        page_jobs = jobs[start_idx:end_idx]

        serializer = ConversionJobSerializer(page_jobs, many=True)
        return Response(
            {
                "count": total_count,
                "page": page_num,
                "page_size": page_size,
                "results": serializer.data,
            }
        )


class ConversionJobCancelView(APIView):
    """
    POST /api/conversions/{id}/cancel/ or POST /api/jobs/{id}/cancel/
    Request cancellation of an active or queued conversion job.
    """
    @extend_schema(
        summary="Cancel Conversion Job",
        description="Cancels an active or queued conversion job and revokes background Celery tasks.",
        responses={200: CancelJobResponseSerializer, 400: ErrorResponseSerializer},
        tags=["Jobs"],
        operation_id="v1_conversions_cancel",
    )
    def post(self, request, job_id):
        jobs = filter_jobs_for_request(request)
        try:
            job = jobs.get(pk=job_id)
            check_job_ownership(request, job)
        except (ConversionJob.DoesNotExist, ValueError):
            raise NotFound("Conversion job not found.")
        except OwnershipDenied as exc:
            raise PermissionDenied(str(exc))
        except Exception as exc:
            raise PermissionDenied(str(exc))

        if job.status == JobStatus.COMPLETED:
            raise ValidationError("Completed jobs cannot be cancelled.")

        if job.status in (JobStatus.CANCELLED, JobStatus.CANCEL_REQUESTED):
            serializer = ConversionJobSerializer(job)
            return Response(
                {"message": "Conversion job is already cancelled.", "job": serializer.data},
                status=status.HTTP_200_OK,
            )

        # Database-authoritative cancellation
        with transaction.atomic():
            job.status = JobStatus.CANCEL_REQUESTED
            job.cancelled_at = timezone.now()
            job.stage_message = "Cancellation requested by user."
            job.save(update_fields=["status", "cancelled_at", "stage_message"])

        # Attempt Celery task revocation if task_id is recorded
        if job.celery_task_id:
            try:
                from config.celery import app as celery_app
                celery_app.control.revoke(job.celery_task_id, terminate=True)
            except Exception as exc:
                logger.warning("Could not revoke Celery task %s: %s", job.celery_task_id, exc)

        # Clean up workspace files
        ConversionService.cleanup_job_files(job)

        with transaction.atomic():
            job.status = JobStatus.CANCELLED
            job.save(update_fields=["status"])

        serializer = ConversionJobSerializer(job)
        return Response(
            {"message": "Conversion job cancelled successfully.", "job": serializer.data},
            status=status.HTTP_200_OK,
        )


class ConversionJobDownloadView(APIView):
    """
    GET /api/conversions/{id}/download/
    Stream the converted output file to the client.
    """
    throttle_classes = [DownloadRateThrottle]

    @extend_schema(
        summary="Stream Converted Output File",
        description="Streams the converted output file directly to the client as an attachment.",
        responses={200: bytes, 404: ErrorResponseSerializer},
        tags=["Download"],
        operation_id="v1_conversions_download",
    )
    def get(self, request, job_id):
        jobs = filter_jobs_for_request(request)
        try:
            job = jobs.get(pk=job_id)
            check_job_ownership(request, job)
        except (ConversionJob.DoesNotExist, ValueError):
            raise NotFound("Conversion job not found.")
        except OwnershipDenied as exc:
            raise PermissionDenied(str(exc))
        except Exception as exc:
            raise PermissionDenied(str(exc))

        if job.status in (JobStatus.PENDING, JobStatus.QUEUED, JobStatus.STARTED, JobStatus.PROCESSING, JobStatus.RETRYING):
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


class QueueStatusView(APIView):
    """
    GET /api/conversions/queue-status/ or GET /api/internal/queue-status/
    Admin/staff-only endpoint returning non-sensitive Celery/Redis queue metrics.
    """
    permission_classes = [IsAdminUser]
    throttle_classes = [QueueMonitorRateThrottle]

    @extend_schema(
        summary="Internal Queue Metrics",
        description="Returns Celery and Redis task queue metrics (Staff only).",
        tags=["System"],
        operation_id="v1_internal_queue_status",
    )
    def get(self, request):
        active_count = 0
        reserved_count = 0
        redis_online = False

        try:
            from config.celery import app as celery_app
            i = celery_app.control.inspect(timeout=1.0)
            active_dict = i.active() or {}
            reserved_dict = i.reserved() or {}
            active_count = sum(len(tasks) for tasks in active_dict.values())
            reserved_count = sum(len(tasks) for tasks in reserved_dict.values())
            redis_online = True
        except Exception as exc:
            logger.warning("Queue status inspect notice: Celery/Redis worker check failed or offline: %s", exc)

        queued_jobs = ConversionJob.objects.filter(status__in=[JobStatus.QUEUED, JobStatus.PENDING]).count()
        processing_jobs = ConversionJob.objects.filter(
            status__in=[JobStatus.PROCESSING, JobStatus.STARTED, JobStatus.RETRYING]
        ).count()
        failed_jobs = ConversionJob.objects.filter(status=JobStatus.FAILED).count()
        completed_jobs = ConversionJob.objects.filter(status=JobStatus.COMPLETED).count()
        cancelled_jobs = ConversionJob.objects.filter(status=JobStatus.CANCELLED).count()

        return Response(
            {
                "status": "healthy" if redis_online else "degraded",
                "redis_online": redis_online,
                "queue_depth": queued_jobs,
                "active_tasks": active_count or processing_jobs,
                "reserved_tasks": reserved_count,
                "metrics": {
                    "queued": queued_jobs,
                    "processing": processing_jobs,
                    "failed": failed_jobs,
                    "completed": completed_jobs,
                    "cancelled": cancelled_jobs,
                },
            },
            status=status.HTTP_200_OK,
        )


class PdfUtilitiesView(APIView):
    """
    POST /api/v1/pdf/utilities/ — Dedicated API endpoint for PDF Utility operations.
    """
    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [PdfUtilityRateThrottle, UploadRateThrottle]

    @extend_schema(
        summary="Execute PDF Utilities",
        description="Executes PDF utility operations (compress, merge, split, encrypt, rotate, watermark, page numbers, metadata).",
        responses={201: ConversionJobSerializer, 202: ConversionJobSerializer, 400: ErrorResponseSerializer},
        tags=["Jobs"],
        operation_id="v1_pdf_utilities",
    )
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

        job = ConversionService.dispatch_job(job)
        output = ConversionJobSerializer(job)
        http_status = status.HTTP_201_CREATED if job.status == JobStatus.COMPLETED else status.HTTP_202_ACCEPTED
        return Response(output.data, status=http_status)


class OcrUtilitiesView(APIView):
    """
    POST /api/v1/ocr/ — Dedicated API endpoint for OCR Utility operations.
    """
    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [OcrRateThrottle, UploadRateThrottle]

    @extend_schema(
        summary="Execute OCR Utilities",
        description="Executes OCR operations (image to searchable PDF/text, scanned PDF to searchable PDF/text).",
        responses={201: ConversionJobSerializer, 202: ConversionJobSerializer, 400: ErrorResponseSerializer},
        tags=["Jobs"],
        operation_id="v1_ocr_utilities",
    )
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

        job = ConversionService.dispatch_job(job)
        output = ConversionJobSerializer(job)
        http_status = status.HTTP_201_CREATED if job.status == JobStatus.COMPLETED else status.HTTP_202_ACCEPTED
        return Response(output.data, status=http_status)


class PresignedUploadUrlView(APIView):
    """
    POST /api/conversions/upload-url/ or POST /api/jobs/upload-url/
    Creates a pending upload session and generates a short-lived presigned upload URL.
    """
    throttle_classes = [UploadRateThrottle]

    @extend_schema(
        summary="Generate Presigned Upload URL",
        description="Generates presigned upload URL for direct cloud/local staging upload.",
        request=PresignedUploadRequestSerializer,
        responses={201: PresignedUploadResponseSerializer, 400: ErrorResponseSerializer},
        tags=["Upload"],
        operation_id="v1_conversions_upload_url",
    )
    def post(self, request):
        serializer = PresignedUploadRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated = serializer.validated_data
        _ensure_session_key(request)

        try:
            session_data = ConversionService.create_presigned_upload_session(
                request,
                source_format=validated["source_format"],
                target_format=validated["target_format"],
                filename=validated["filename"],
                file_size_bytes=validated["file_size_bytes"],
                options=validated.get("options", {}),
            )
            return Response(
                {
                    "job_id": session_data["job_id"],
                    "upload_url": session_data["upload_url"],
                    "fields": session_data["fields"],
                    "storage_key": session_data["storage_key"],
                    "expires_in": session_data["expires_in"],
                    "max_file_size": session_data["max_file_size"],
                    "backend": session_data["backend"],
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception as exc:
            logger.warning("Error creating presigned upload session: %s", exc)
            return Response(
                {"error": True, "message": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class FinalizeUploadView(APIView):
    """
    POST /api/conversions/{id}/finalize-upload/ or POST /api/jobs/{id}/finalize-upload/
    Verifies object existence in storage, performs security checks, marks finalized, and dispatches task.
    """
    @extend_schema(
        summary="Finalize Upload Session",
        description="Verifies file upload completion in storage, performs security validation, and dispatches conversion task.",
        responses={201: ConversionJobSerializer, 202: ConversionJobSerializer, 400: ErrorResponseSerializer},
        tags=["Upload"],
        operation_id="v1_conversions_finalize_upload",
    )
    def post(self, request, job_id):
        jobs = filter_jobs_for_request(request)
        try:
            job = jobs.get(pk=job_id)
            check_job_ownership(request, job)
        except (ConversionJob.DoesNotExist, ValueError):
            raise NotFound("Conversion job not found.")
        except OwnershipDenied as exc:
            raise PermissionDenied(str(exc))
        except Exception as exc:
            raise PermissionDenied(str(exc))

        try:
            job = ConversionService.finalize_uploaded_job(job)
            serializer = ConversionJobSerializer(job)
            http_status = status.HTTP_201_CREATED if job.status == JobStatus.COMPLETED else status.HTTP_202_ACCEPTED
            return Response(serializer.data, status=http_status)
        except Exception as exc:
            logger.warning("Error finalizing upload for job %s: %s", job_id, exc)
            return Response(
                {"error": True, "message": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class PresignedDownloadUrlView(APIView):
    """
    GET /api/conversions/{id}/download-url/ or GET /api/jobs/{id}/download-url/
    Returns a short-lived presigned download URL for a completed conversion job.
    """
    throttle_classes = [DownloadRateThrottle]

    @extend_schema(
        summary="Generate Presigned Download URL",
        description="Returns a short-lived presigned download URL for a completed conversion job.",
        responses={200: PresignedDownloadResponseSerializer, 404: ErrorResponseSerializer},
        tags=["Download"],
        operation_id="v1_conversions_download_url",
    )
    def get(self, request, job_id):
        jobs = filter_jobs_for_request(request)
        try:
            job = jobs.get(pk=job_id)
            check_job_ownership(request, job)
        except (ConversionJob.DoesNotExist, ValueError):
            raise NotFound("Conversion job not found.")
        except OwnershipDenied as exc:
            raise PermissionDenied(str(exc))
        except Exception as exc:
            raise PermissionDenied(str(exc))

        if job.status in (JobStatus.PENDING, JobStatus.QUEUED, JobStatus.STARTED, JobStatus.PROCESSING, JobStatus.RETRYING):
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
                    "status": job.status,
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        if job.status == JobStatus.CANCELLED:
            return Response(
                {"error": True, "message": "This conversion job was cancelled."},
                status=status.HTTP_410_GONE,
            )

        download_url = ConversionService.get_job_download_url(job)
        if not download_url:
            return Response(
                {"error": True, "message": "The converted file is no longer available."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                "job_id": str(job.id),
                "download_url": download_url,
                "expires_in": getattr(settings, "S3_PRESIGNED_DOWNLOAD_EXPIRY", 900),
                "filename": job.output_filename or f"converted_{job.id}.{job.target_format}",
            },
            status=status.HTTP_200_OK,
        )

