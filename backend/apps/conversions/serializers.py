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

class ConversionJobSerializer(serializers.ModelSerializer):
    """
    Read serializer for ConversionJob — used in list, detail, and POST responses.

    Includes:
      - Human-readable format/status labels.
      - Output metadata (filename, size) when the job is completed.
      - A download_url when the job is completed and the output file exists.

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

    # Dynamically computed — only present when status=completed and file exists
    download_url = serializers.SerializerMethodField()

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
            "output_filename",
            "output_size_bytes",
            "download_url",
            "created_at",
            "started_at",
            "completed_at",
            "error_message",
        ]
        read_only_fields = fields

    def get_download_url(self, obj: ConversionJob) -> str | None:
        """
        Return the download URL when the job is completed and the output file exists.

        The URL is a relative path (e.g. /api/conversions/<id>/download/) so it
        works behind any domain or reverse proxy.
        """
        from apps.conversions.models import JobStatus
        from pathlib import Path

        if obj.status != JobStatus.COMPLETED:
            return None
        if not obj.output_path:
            return None
        # Only return URL if the file physically exists
        if not Path(obj.output_path).exists():
            return None

        try:
            return reverse("conversions:job-download", kwargs={"job_id": obj.id})
        except Exception:
            return None


# ── Input serializer ───────────────────────────────────────────────────────────

class ConversionJobCreateSerializer(serializers.Serializer):
    """
    Write serializer for POST /api/conversions/.

    Accepts a multipart/form-data request containing:
      - file:          the uploaded file (required)
      - source_format: format key, e.g. "pdf"  (required)
      - target_format: format key, e.g. "docx" (required)

    Validates:
      1. source_format and target_format are known values.
      2. The (source, target) pair is a supported conversion.
      3. The uploaded file's extension matches the declared source_format.
      4. The uploaded file's MIME type matches the declared source_format.
      5. The uploaded file does not exceed MAX_UPLOAD_SIZE.

    NOTE: PDF magic-byte validation happens in ConversionService (after staging)
    because the serializer only has access to an in-memory UploadedFile object.
    """

    file = serializers.FileField(
        required=True,
        help_text="The file to convert.",
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

    def validate_file(self, uploaded_file):
        """Validate file size."""
        max_size = getattr(settings, "MAX_UPLOAD_SIZE", 52_428_800)
        if uploaded_file.size > max_size:
            max_mb = max_size / (1024 * 1024)
            raise serializers.ValidationError(
                f"File is too large. Maximum allowed size is {max_mb:.0f} MB."
            )
        return uploaded_file

    def validate(self, attrs):
        """Cross-field validation: format pair + file extension + MIME type."""
        source_format = attrs.get("source_format")
        target_format = attrs.get("target_format")
        uploaded_file = attrs.get("file")

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

        # 2. Validate file extension against declared source_format.
        if source_format and uploaded_file:
            allowed_exts = ALLOWED_EXTENSIONS.get(source_format, [])
            file_ext = Path(uploaded_file.name).suffix.lower()
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

            # 3. Validate MIME type against declared source_format.
            allowed_mimes = ALLOWED_MIME_TYPES.get(source_format, [])
            content_type = getattr(uploaded_file, "content_type", None)
            if content_type and content_type not in allowed_mimes:
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
