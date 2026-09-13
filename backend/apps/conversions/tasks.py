"""
Celery background tasks for VELTO Conversion.

Handles:
  - Background conversion job execution with stage updates and progress tracking.
  - Ownership & database-authoritative cancellation checks.
  - Safe error redaction and transient retry handling.
  - Stale job recovery for interrupted workers.
"""

import logging
import socket
from datetime import timedelta
from typing import Optional

from celery import shared_task
from celery.exceptions import Retry, SoftTimeLimitExceeded
from django.db import models, transaction
from django.utils import timezone

from apps.conversions.models import ConversionJob, JobStatus
from apps.conversions.services import ConversionService, ConversionServiceError
from apps.conversions.security import SecurityValidationError

logger = logging.getLogger(__name__)

PERMANENT_EXCEPTIONS = (
    SecurityValidationError,
    ConversionServiceError,
    ValueError,
    TypeError,
    KeyError,
    FileNotFoundError,
)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def process_conversion_job_task(self, job_id: str) -> dict:
    """
    Celery task that executes a queued ConversionJob in the background.

    Lifecycle:
      QUEUED → STARTED → PROCESSING → COMPLETED (or FAILED / CANCELLED)
    """
    worker_identity = getattr(self.request, "hostname", None) or socket.gethostname()
    task_id = self.request.id or ""

    try:
        job = ConversionJob.objects.get(pk=job_id)
    except ConversionJob.DoesNotExist:
        logger.error("Task received for non-existent job ID %s", job_id)
        return {"status": "not_found", "job_id": job_id}

    # Database-authoritative cancellation check before execution
    if job.status in (JobStatus.CANCELLED, JobStatus.CANCEL_REQUESTED):
        logger.info("Job %s was cancelled before execution started.", job.id)
        _mark_job_cancelled(job)
        return {"status": "cancelled", "job_id": str(job.id)}

    if job.is_terminal:
        logger.info("Job %s is already in terminal state (%s) — skipping.", job.id, job.status)
        return {"status": job.status, "job_id": str(job.id)}

    # Mark STARTED and associate Celery task metadata
    with transaction.atomic():
        job.status = JobStatus.STARTED
        job.celery_task_id = task_id
        job.worker_name = worker_identity
        job.last_heartbeat = timezone.now()
        job.current_stage = "starting"
        job.stage_message = "Job assigned to worker node"
        job.progress = max(job.progress, 5)
        job.save(update_fields=[
            "status", "celery_task_id", "worker_name", "last_heartbeat",
            "current_stage", "stage_message", "progress",
        ])

    def _update_stage(progress_val: int, stage_name: str, message: str) -> bool:
        """
        Helper to update job progress monotonically and check for cancellation request.
        Returns False if cancellation was requested.
        """
        job.refresh_from_db()
        if job.status in (JobStatus.CANCELLED, JobStatus.CANCEL_REQUESTED):
            return False

        with transaction.atomic():
            new_progress = max(job.progress, min(100, progress_val))
            job.progress = new_progress
            job.current_stage = stage_name
            job.stage_message = message
            job.last_heartbeat = timezone.now()
            job.save(update_fields=["progress", "current_stage", "stage_message", "last_heartbeat"])
        return True

    try:
        # Stage 1: Validation
        if not _update_stage(15, "validating", "Validating file integrity and security rules"):
            _mark_job_cancelled(job)
            return {"status": "cancelled", "job_id": str(job.id)}

        # Stage 2: Workspace Preparation
        if not _update_stage(35, "preparing", "Preparing isolated execution environment"):
            _mark_job_cancelled(job)
            return {"status": "cancelled", "job_id": str(job.id)}

        # Stage 3: Conversion Execution
        if not _update_stage(60, "converting", "Executing file conversion engine"):
            _mark_job_cancelled(job)
            return {"status": "cancelled", "job_id": str(job.id)}

        # Delegate execution to ConversionService
        job = ConversionService.process_job(job)

        # Check final state after service execution
        job.refresh_from_db()
        if job.status == JobStatus.COMPLETED:
            _update_stage(100, "completed", "Conversion completed successfully")
            return {"status": "completed", "job_id": str(job.id), "progress": 100}

        elif job.status == JobStatus.FAILED:
            with transaction.atomic():
                job.failed_at = timezone.now()
                if not job.error_code:
                    job.error_code = "CONVERSION_FAILED"
                job.save(update_fields=["failed_at", "error_code"])
            return {"status": "failed", "job_id": str(job.id), "error": job.error_message}

        elif job.status in (JobStatus.CANCELLED, JobStatus.CANCEL_REQUESTED):
            _mark_job_cancelled(job)
            return {"status": "cancelled", "job_id": str(job.id)}

    except SoftTimeLimitExceeded:
        logger.error("Celery task soft time limit exceeded for job %s", job.id)
        with transaction.atomic():
            job.status = JobStatus.FAILED
            job.error_message = "Conversion processing timed out. The operation took longer than allowed."
            job.error_code = "TASK_TIMEOUT"
            job.failed_at = timezone.now()
            job.save(update_fields=["status", "error_message", "error_code", "failed_at"])
        ConversionService.cleanup_job_files(job)
        return {"status": "failed", "job_id": str(job.id), "error": "timeout"}

    except Retry:
        raise

    except Exception as exc:
        err_str = str(exc)
        logger.exception("Unexpected error in process_conversion_job_task for job %s: %s", job.id, exc)

        is_permanent = isinstance(exc, PERMANENT_EXCEPTIONS)

        if not is_permanent and self.request.retries < self.max_retries:
            retry_num = self.request.retries + 1
            with transaction.atomic():
                job.status = JobStatus.RETRYING
                job.retry_count = retry_num
                job.stage_message = f"Retrying conversion after unexpected error (attempt {retry_num}/{self.max_retries})"
                job.save(update_fields=["status", "retry_count", "stage_message"])

            countdown = 5 * (2 ** self.request.retries)
            raise self.retry(exc=exc, countdown=countdown)

        safe_user_msg = "An unexpected background error occurred during processing."
        with transaction.atomic():
            job.status = JobStatus.FAILED
            job.error_message = safe_user_msg
            job.error_code = "TASK_UNHANDLED_ERROR"
            job.failed_at = timezone.now()
            job.save(update_fields=["status", "error_message", "error_code", "failed_at"])
        ConversionService.cleanup_job_files(job)
        return {"status": "failed", "job_id": str(job.id), "error": safe_user_msg}

    return {"status": job.status, "job_id": str(job.id)}


@shared_task(bind=True)
def recover_stale_jobs_task(self, timeout_minutes: int = 15) -> dict:
    """
    Periodic task or management job to detect and recover stale processing jobs.

    Finds jobs in STARTED/PROCESSING state whose last_heartbeat or started_at
    is older than timeout_minutes, and marks them FAILED cleanly without orphan files.
    """
    cutoff = timezone.now() - timedelta(minutes=timeout_minutes)
    stale_jobs = ConversionJob.objects.filter(
        status__in=[JobStatus.STARTED, JobStatus.PROCESSING, JobStatus.RETRYING],
    ).filter(
        models.Q(last_heartbeat__lt=cutoff) |
        models.Q(last_heartbeat__isnull=True, started_at__lt=cutoff)
    )

    recovered_count = 0
    for job in stale_jobs:
        logger.warning("Recovering stale job %s (last heartbeat/start < %s)", job.id, cutoff)
        with transaction.atomic():
            job.status = JobStatus.FAILED
            job.error_message = "Job processing was interrupted due to worker timeout or failure."
            job.error_code = "STALE_JOB_RECOVERED"
            job.failed_at = timezone.now()
            job.save(update_fields=["status", "error_message", "error_code", "failed_at"])

        ConversionService.cleanup_job_files(job)
        recovered_count += 1

    return {"recovered_count": recovered_count, "timestamp": timezone.now().isoformat()}


def _mark_job_cancelled(job: ConversionJob) -> None:
    """Helper to finalize job status as CANCELLED and clean up workspace."""
    with transaction.atomic():
        job.status = JobStatus.CANCELLED
        job.cancelled_at = timezone.now()
        job.stage_message = "Conversion job was cancelled."
        job.save(update_fields=["status", "cancelled_at", "stage_message"])
    ConversionService.cleanup_job_files(job)
