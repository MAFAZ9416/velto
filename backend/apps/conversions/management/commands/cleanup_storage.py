"""
Django management command for object storage and database file lifecycle cleanup.

Usage:
    python backend/manage.py cleanup_storage [--hours 24] [--dry-run]
"""

from datetime import timedelta
import logging

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.conversions.models import ConversionJob, JobStatus, CleanupStatus
from apps.conversions.services import ConversionService
from apps.conversions.storage import get_storage_service

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Cleans up expired outputs, abandoned uploads, failed/cancelled job files, and orphan storage objects."

    def add_arguments(self, parser):
        parser.add_argument(
            "--hours",
            type=int,
            default=getattr(settings, "STORAGE_RETENTION_HOURS", 24),
            help="Retention threshold in hours (default: 24). Files older than this will be cleaned.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Scan and report target files without performing actual deletions.",
        )

    def _execute_job_cleanup(self, job: ConversionJob, dry_run: bool, new_status: str = None):
        """Performs cleanup for a single job and records lifecycle metadata safely."""
        if dry_run:
            return

        job.cleanup_started_at = timezone.now()
        job.cleanup_status = CleanupStatus.IN_PROGRESS
        job.cleanup_attempts += 1

        try:
            ConversionService.cleanup_job_files(job)
            job.cleanup_completed_at = timezone.now()
            job.cleanup_status = CleanupStatus.COMPLETED
            job.cleanup_error = ""
            if new_status:
                job.status = new_status

            update_fields = [
                "cleanup_started_at",
                "cleanup_completed_at",
                "cleanup_status",
                "cleanup_attempts",
                "cleanup_error",
            ]
            if new_status:
                update_fields.append("status")

            job.save(update_fields=update_fields)
        except Exception as exc:
            logger.error("Error executing cleanup for job %s: %s", job.id, exc)
            job.cleanup_status = CleanupStatus.FAILED
            job.cleanup_error = str(exc)[:500]
            job.save(update_fields=["cleanup_started_at", "cleanup_status", "cleanup_attempts", "cleanup_error"])

    def handle(self, *args, **options):
        retention_hours = options["hours"]
        dry_run = options["dry_run"]
        cutoff = timezone.now() - timedelta(hours=retention_hours)

        self.stdout.write(
            self.style.NOTICE(
                f"Starting storage lifecycle cleanup (cutoff: {cutoff.isoformat()}, dry_run={dry_run})..."
            )
        )

        storage = get_storage_service()
        deleted_count = 0

        # 1. Clean abandoned unfinalized presigned uploads older than 1 hour
        abandoned_cutoff = timezone.now() - timedelta(hours=1)
        abandoned_jobs = ConversionJob.objects.filter(
            is_finalized=False,
            created_at__lt=abandoned_cutoff,
        ).exclude(cleanup_status=CleanupStatus.COMPLETED)

        for job in abandoned_jobs:
            self.stdout.write(f"Found abandoned unfinalized upload session: job {job.id}")
            self._execute_job_cleanup(job, dry_run, new_status=JobStatus.EXPIRED)
            deleted_count += 1

        # 2. Clean files for FAILED and CANCELLED jobs older than cutoff
        terminal_cleanup_jobs = ConversionJob.objects.filter(
            status__in=[JobStatus.FAILED, JobStatus.CANCELLED],
            created_at__lt=cutoff,
        ).exclude(cleanup_status=CleanupStatus.COMPLETED)

        for job in terminal_cleanup_jobs:
            self.stdout.write(f"Cleaning files for {job.status} job {job.id}")
            self._execute_job_cleanup(job, dry_run)
            deleted_count += 1

        # 3. Clean expired output files for COMPLETED jobs older than retention cutoff
        expired_completed_jobs = ConversionJob.objects.filter(
            status=JobStatus.COMPLETED,
            completed_at__lt=cutoff,
        ).exclude(cleanup_status=CleanupStatus.COMPLETED)

        for job in expired_completed_jobs:
            self.stdout.write(f"Expired output retention limit reached for job {job.id}")
            self._execute_job_cleanup(job, dry_run, new_status=JobStatus.EXPIRED)
            deleted_count += 1

        msg = (
            f"[DRY-RUN] Would clean {deleted_count} job storage files/sessions."
            if dry_run
            else f"Successfully cleaned {deleted_count} job storage files/sessions."
        )
        self.stdout.write(self.style.SUCCESS(msg))

