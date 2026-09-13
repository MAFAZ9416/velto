"""
ConversionJob model — the core database entity for VELTO Conversion.
"""

import uuid
from django.conf import settings
from django.db import models
from apps.conversions.formats import FORMAT_CHOICES


class JobStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    QUEUED = "queued", "Queued"
    STARTED = "started", "Started"
    PROCESSING = "processing", "Processing"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"
    RETRYING = "retrying", "Retrying"
    CANCEL_REQUESTED = "cancel_requested", "Cancel Requested"
    CANCELLED = "cancelled", "Cancelled"
    EXPIRED = "expired", "Expired"


class ConversionJob(models.Model):
    """
    Represents a single file conversion request.

    Design notes
    ------------
    - UUID primary key is used to avoid sequential ID enumeration.
    - `user` is nullable to support anonymous sessions; a non-null user FK
      will be used when authentication is added in a later phase.
    - `session_key` stores the Django session key for anonymous job ownership.
      When `user` is set, `session_key` may be blank.
    - Uploaded files are NOT stored in this model. The `original_filename`
      and `source_format` fields capture metadata only. Actual file bytes
      are handled by the temporary upload staging layer (see ConversionService).
    - `started_at` and `completed_at` are null until the job transitions to
      the corresponding state. This allows accurate duration tracking.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conversion_jobs",
        help_text="Null for anonymous users. Set when the user is logged in.",
    )
    # Session key for anonymous ownership filtering
    session_key = models.CharField(
        max_length=40,
        blank=True,
        db_index=True,
        help_text="Django session key for anonymous user job ownership.",
    )
    source_format = models.CharField(
        max_length=20,
        choices=FORMAT_CHOICES,
        help_text="Format of the uploaded file.",
    )
    target_format = models.CharField(
        max_length=20,
        choices=FORMAT_CHOICES,
        help_text="Desired output format.",
    )
    status = models.CharField(
        max_length=20,
        choices=JobStatus.choices,
        default=JobStatus.PENDING,
        db_index=True,
    )
    original_filename = models.CharField(
        max_length=255,
        help_text="Original filename as provided by the user. Metadata only.",
    )
    file_size_bytes = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        help_text="Size of the uploaded file in bytes. Stored for auditing.",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the conversion engine began processing.",
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the conversion finished (succeeded or failed).",
    )
    error_message = models.TextField(
        blank=True,
        help_text="Engine error details. Empty unless status is 'failed'.",
    )
    options = models.JSONField(
        default=dict,
        blank=True,
        help_text="Optional parameters for conversion engine (e.g. resize, quality).",
    )

    # ── Progress & stage fields ───────────────────────────────────────────────
    progress = models.IntegerField(
        default=0,
        help_text="Job progress percentage 0-100.",
    )
    current_stage = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="Human readable stage identifier.",
    )
    stage_message = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Detailed stage status message.",
    )
    error_code = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="Machine-readable error code.",
    )

    # ── Retry & Execution tracking ────────────────────────────────────────────
    retry_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of retry attempts executed.",
    )
    max_retries = models.PositiveIntegerField(
        default=3,
        help_text="Maximum allowed retries.",
    )
    failed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the job reached FAILED status.",
    )
    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the job was cancelled.",
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the output file or job metadata expires.",
    )

    # ── Celery & worker correlation ───────────────────────────────────────────
    celery_task_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Associated Celery task UUID.",
    )
    worker_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Name of worker that processed the task.",
    )
    last_heartbeat = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last active heartbeat timestamp from worker.",
    )

    # ── Object Storage metadata ───────────────────────────────────────────────
    storage_backend = models.CharField(
        max_length=32,
        default="local",
        help_text="Storage provider backend used ('local', 's3').",
    )
    input_storage_key = models.CharField(
        max_length=1024,
        blank=True,
        help_text="Object storage key for the staged input file.",
    )
    output_storage_key = models.CharField(
        max_length=1024,
        blank=True,
        help_text="Object storage key for the generated output file.",
    )
    is_finalized = models.BooleanField(
        default=True,
        help_text="False for pending direct presigned upload sessions until finalization.",
    )

    # ── File-path metadata (never store file bytes here) ──────────────────────
    input_path = models.CharField(
        max_length=1024,
        blank=True,
        help_text=(
            "Absolute path to the staged input file on disk. "
            "Internal use only — never exposed through the API."
        ),
    )
    output_path = models.CharField(
        max_length=1024,
        blank=True,
        help_text=(
            "Absolute path to the generated output file on disk. "
            "Internal use only — never exposed through the API."
        ),
    )
    output_filename = models.CharField(
        max_length=255,
        blank=True,
        help_text="Safe output filename presented to the user for download.",
    )
    output_size_bytes = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        help_text="Size of the generated output file in bytes.",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Conversion Job"
        verbose_name_plural = "Conversion Jobs"
        indexes = [
            models.Index(fields=["session_key", "status"]),
            models.Index(fields=["user", "status"]),
        ]

    def __str__(self) -> str:
        return (
            f"ConversionJob({self.id}) "
            f"{self.source_format}→{self.target_format} [{self.status}]"
        )

    @property
    def public_id(self) -> str:
        return str(self.id)

    @property
    def is_terminal(self) -> bool:
        """True if the job is in a final state (completed, failed, cancelled, expired)."""
        return self.status in (
            JobStatus.COMPLETED,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
            JobStatus.EXPIRED,
        )
