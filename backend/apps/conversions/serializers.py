"""
Serializers for the conversions app.
"""

from pathlib import Path

from django.conf import settings
from django.urls import reverse
from rest_framework import serializers

from apps.conversions.formats import (
    ALLOWED_EXTENSIONS,
    ALLOWED_MIME_TYPES,
    FORMAT_CHOICES,
    is_valid_conversion,
)
from apps.conversions.models import ConversionJob


# ── Output serializer ──────────────────────────────────────────────────────────

import json

class ConversionJobSerializer(serializers.ModelSerializer):
    """
    Read serializer for ConversionJob — used in list, detail, and POST responses.

    Includes:
      - Human-readable format/status labels.
      - Output metadata (filename, size) when the job is completed.
      - A download_url when the job is completed and the output file exists.
      - Conversion options parameters.

    Intentionally excludes:
      - session_key (internal ownership field).
      - input_path / output_path (absolute filesystem paths — never exposed).
    """

    source_format_label = serializers.CharField(
        source="get_source_format_display", read_only=True
    )
    target_format_label = serializers.CharField(
        source="get_target_format_display", read_only=True
    )
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    # Computed serializer method fields
    download_url = serializers.SerializerMethodField()
    download_available = serializers.SerializerMethodField()
    cancellation_available = serializers.SerializerMethodField()
    retry_available = serializers.SerializerMethodField()

    class Meta:
        model = ConversionJob
        fields = [
            "id",
            "source_format",
            "source_format_label",
            "target_format",
            "target_format_label",
            "status",
            "status_label",
            "original_filename",
            "file_size_bytes",
            "options",
            "progress",
            "current_stage",
            "stage_message",
            "error_code",
            "retry_count",
            "max_retries",
            "celery_task_id",
            "worker_name",
            "storage_backend",
            "is_finalized",
            "output_filename",
            "output_size_bytes",
            "download_url",
            "download_available",
            "cancellation_available",
            "retry_available",
            "created_at",
            "updated_at",
            "started_at",
            "completed_at",
            "failed_at",
            "cancelled_at",
            "expires_at",
            "error_message",
        ]
        read_only_fields = fields

    def get_download_url(self, obj: ConversionJob) -> str | None:
        """
        Return the download URL when the job is completed and the output file exists.
        """
        from apps.conversions.models import JobStatus
        from pathlib import Path

        if obj.status != JobStatus.COMPLETED:
            return None
        if obj.output_storage_key:
            try:
                return reverse("conversions:job-download-url", kwargs={"job_id": obj.id})
            except Exception:
                pass
        if obj.output_path and Path(obj.output_path).exists():
            try:
                return reverse("conversions:job-download", kwargs={"job_id": obj.id})
            except Exception:
                pass
        return None

    def get_download_available(self, obj: ConversionJob) -> bool:
        from apps.conversions.models import JobStatus
        from pathlib import Path
        if obj.status != JobStatus.COMPLETED:
            return False
        if obj.output_storage_key:
            return True
        if obj.output_path and Path(obj.output_path).exists():
            return True
        return False

    def get_cancellation_available(self, obj: ConversionJob) -> bool:
        from apps.conversions.models import JobStatus
        return obj.status in (JobStatus.PENDING, JobStatus.QUEUED, JobStatus.STARTED, JobStatus.PROCESSING)

    def get_retry_available(self, obj: ConversionJob) -> bool:
        from apps.conversions.models import JobStatus
        from pathlib import Path
        if obj.status not in (JobStatus.FAILED, JobStatus.CANCELLED):
            return False
        if obj.retry_count >= obj.max_retries:
            return False
        if obj.input_storage_key:
            return True
        if obj.input_path and Path(obj.input_path).exists():
            return True
        return False


# ── Input serializer ───────────────────────────────────────────────────────────

class ConversionJobCreateSerializer(serializers.Serializer):
    """
    Write serializer for POST /api/conversions/.

    Accepts a multipart/form-data request containing:
      - file:          the uploaded file (required for single-file conversions)
      - files:         list of uploaded files (optional, used for target_format="zip")
      - source_format: format key, e.g. "jpg" (required)
      - target_format: format key, e.g. "png" or "zip" (required)
      - options:       optional conversion options dict or JSON string
    """

    file = serializers.FileField(
        required=False,
        help_text="The file to convert.",
    )
    files = serializers.ListField(
        child=serializers.FileField(),
        required=False,
        help_text="Multiple files to package into a ZIP archive.",
    )
    source_format = serializers.ChoiceField(
        choices=FORMAT_CHOICES,
        required=True,
        help_text="Format of the uploaded file.",
    )
    target_format = serializers.ChoiceField(
        choices=FORMAT_CHOICES,
        required=True,
        help_text="Desired output format.",
    )
    options = serializers.JSONField(
        required=False,
        default=dict,
        help_text="Optional conversion parameters dict or JSON string.",
    )

    def validate_file(self, uploaded_file):
        """Validate single file size."""
        if uploaded_file:
            max_size = getattr(settings, "MAX_UPLOAD_SIZE", 52_428_800)
            if uploaded_file.size > max_size:
                max_mb = max_size / (1024 * 1024)
                raise serializers.ValidationError(
                    f"File is too large. Maximum allowed size is {max_mb:.0f} MB."
                )
        return uploaded_file

    def validate_files(self, uploaded_files):
        """Validate multi-file sizes."""
        if uploaded_files:
            max_size = getattr(settings, "MAX_UPLOAD_SIZE", 52_428_800)
            for f in uploaded_files:
                if f.size > max_size:
                    max_mb = max_size / (1024 * 1024)
                    raise serializers.ValidationError(
                        f"File '{f.name}' is too large. Maximum allowed size is {max_mb:.0f} MB."
                    )
        return uploaded_files

    def validate_options(self, value):
        """Parse options if provided as a JSON string."""
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except Exception as exc:
                raise serializers.ValidationError("Invalid JSON string in options field.") from exc
        if not isinstance(value, dict):
            raise serializers.ValidationError("Options must be a valid JSON dictionary.")
        return value

    def validate(self, attrs):
        """Cross-field validation: format pair + file extension + MIME type."""
        source_format = attrs.get("source_format")
        target_format = attrs.get("target_format")
        uploaded_file = attrs.get("file")
        uploaded_files = attrs.get("files")

        if not uploaded_file and not uploaded_files:
            raise serializers.ValidationError(
                {"file": "At least one uploaded file ('file' or 'files') is required."}
            )

        # 1. Validate the conversion pair.
        if source_format and target_format:
            if not is_valid_conversion(source_format, target_format):
                raise serializers.ValidationError(
                    {
                        "target_format": (
                            f"Converting from '{source_format}' to '{target_format}' "
                            "is not supported. See /api/conversions/supported-formats/ "
                            "for the full list."
                        )
                    }
                )

        # 2. Validate file extensions and MIME types for single file upload
        files_to_check = [uploaded_file] if uploaded_file else (uploaded_files or [])
        allowed_exts = ALLOWED_EXTENSIONS.get(source_format, [])
        allowed_mimes = ALLOWED_MIME_TYPES.get(source_format, [])

        # For generic image sources or ZIP target, skip single-extension lock
        if allowed_exts and source_format not in ("images", "zip") and target_format != "zip":
            for f in files_to_check:
                file_ext = Path(f.name).suffix.lower()
                if file_ext not in allowed_exts:
                    raise serializers.ValidationError(
                        {
                            "file": (
                                f"File extension '{file_ext}' does not match "
                                f"the declared source format '{source_format}'. "
                                f"Expected one of: {', '.join(allowed_exts)}."
                            )
                        }
                    )

                content_type = getattr(f, "content_type", None)
                if content_type and allowed_mimes and content_type not in allowed_mimes:
                    raise serializers.ValidationError(
                        {
                            "file": (
                                f"MIME type '{content_type}' does not match "
                                f"the declared source format '{source_format}'. "
                                f"Expected one of: {', '.join(allowed_mimes)}."
                            )
                        }
                    )

        return attrs


class PresignedUploadRequestSerializer(serializers.Serializer):
    """
    Write serializer for POST /api/conversions/upload-url/.
    """
    source_format = serializers.ChoiceField(choices=FORMAT_CHOICES, required=True)
    target_format = serializers.ChoiceField(choices=FORMAT_CHOICES, required=True)
    filename = serializers.CharField(max_length=255, required=True)
    file_size_bytes = serializers.IntegerField(min_value=1, required=True)
    options = serializers.JSONField(required=False, default=dict)

    def validate_options(self, value):
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except Exception as exc:
                raise serializers.ValidationError("Invalid JSON string in options field.") from exc
        if not isinstance(value, dict):
            raise serializers.ValidationError("Options must be a valid JSON dictionary.")
        return value

    def validate(self, attrs):
        source_format = attrs.get("source_format")
        target_format = attrs.get("target_format")
        options = attrs.get("options", {})
        if not is_valid_conversion(source_format, target_format, options):
            raise serializers.ValidationError(
                {"target_format": f"Converting from '{source_format}' to '{target_format}' is not supported."}
            )
        return attrs


class FormatDiscoverySerializer(serializers.Serializer):
    """
    Read serializer for format pair discovery endpoint (GET /api/v1/conversions/formats/).
    """
    source = serializers.CharField()
    target = serializers.CharField()
    source_label = serializers.CharField()
    target_label = serializers.CharField()
    category = serializers.CharField()
    enabled = serializers.BooleanField(default=True)
    mime_types = serializers.ListField(child=serializers.CharField(), required=False)
    max_file_size = serializers.IntegerField(required=False)
    restrictions = serializers.DictField(required=False)


class RetryJobResponseSerializer(serializers.Serializer):
    """
    Response serializer for POST /api/v1/conversions/{job_id}/retry/.
    """
    original_job_id = serializers.CharField()
    new_job_id = serializers.CharField()
    status = serializers.CharField()
    message = serializers.CharField()


class ConversionHistoryQuerySerializer(serializers.Serializer):
    """
    Query parameter serializer for GET /api/v1/conversions/history/.
    """
    status = serializers.CharField(required=False)
    source = serializers.CharField(required=False)
    source_format = serializers.CharField(required=False)
    target = serializers.CharField(required=False)
    target_format = serializers.CharField(required=False)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    search = serializers.CharField(required=False)
    ordering = serializers.CharField(required=False, default="-created_at")
    page = serializers.IntegerField(required=False, default=1, min_value=1)
    page_size = serializers.IntegerField(required=False, default=20, min_value=1, max_value=100)


class HealthCheckSerializer(serializers.Serializer):
    status = serializers.CharField(default="ok")
    service = serializers.CharField(default="velto-conversion")


class ReadinessCheckSerializer(serializers.Serializer):
    status = serializers.CharField(default="ready")
    service = serializers.CharField(default="velto-conversion")
    checks = serializers.DictField()


class CancelJobResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    job = ConversionJobSerializer()


class DeleteJobResponseSerializer(serializers.Serializer):
    message = serializers.CharField()


class PresignedUploadResponseSerializer(serializers.Serializer):
    job_id = serializers.CharField()
    upload_url = serializers.CharField()
    fields = serializers.DictField()
    storage_key = serializers.CharField()
    expires_in = serializers.IntegerField()
    max_file_size = serializers.IntegerField()
    backend = serializers.CharField()


class PresignedDownloadResponseSerializer(serializers.Serializer):
    job_id = serializers.CharField()
    download_url = serializers.CharField()
    expires_in = serializers.IntegerField()
    filename = serializers.CharField()


class ErrorDetailSerializer(serializers.Serializer):
    code = serializers.CharField()
    message = serializers.CharField()
    details = serializers.DictField(default=dict)
    request_id = serializers.CharField()


class ErrorResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(default=False)
    data = serializers.SerializerMethodField(default=None)
    error = ErrorDetailSerializer()


class SuccessEnvelopeSerializer(serializers.Serializer):
    success = serializers.BooleanField(default=True)
    data = serializers.DictField()
    error = serializers.SerializerMethodField(default=None)



