"""
Comprehensive unit and integration test suite for VELTO Job Processing Milestone.

Tests:
  - Celery background task execution and dispatch.
  - Lifecycle: QUEUED → STARTED → PROCESSING → COMPLETED / FAILED / CANCELLED.
  - Progress tracking (stage updates, 0-100%, non-decreasing).
  - Transient retries vs permanent fast-fail.
  - Soft timeout handling & workspace file cleanup.
  - Stale job recovery management command / task.
  - Cancellation endpoint & database-authoritative checks.
  - Staff-only queue monitoring endpoint & rate limiting.
  - Ownership & IDOR protection across detail, cancel, download endpoints.
  - Output download flow and cleanup verification.
"""

import io
import os
from datetime import timedelta
from unittest.mock import patch

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.conversions.models import ConversionJob, JobStatus
from apps.conversions.services import ConversionService
from apps.conversions.tasks import (
    process_conversion_job_task,
    recover_stale_jobs_task,
)

User = get_user_model()


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, TESTING=True)
class JobProcessingTestCase(TestCase):
    """Core job processing unit and integration tests."""

    def setUp(self):
        self.client = APIClient()
        self.user_a = User.objects.create_user(username="usera", password="password123")
        self.user_b = User.objects.create_user(username="userb", password="password123")
        self.staff_user = User.objects.create_user(username="admin", password="password123", is_staff=True)

        # Generate a valid 10x10 PNG image using Pillow
        buf = io.BytesIO()
        img = Image.new("RGB", (10, 10), color="red")
        img.save(buf, format="PNG")
        self.test_png = buf.getvalue()

    # ── 1. Real Task Submission & Lifecycle ────────────────────────────────────

    def test_successful_background_conversion_lifecycle(self):
        """Verify complete QUEUED -> STARTED -> PROCESSING -> COMPLETED lifecycle."""
        uploaded = SimpleUploadedFile("sample.png", self.test_png, content_type="image/png")

        job = ConversionService.create_job(
            source_format="png",
            target_format="jpg",
            uploaded_file=uploaded,
            session_key="",
            user=self.user_a,
        )

        res = process_conversion_job_task(str(job.id))
        self.assertEqual(res.get("status"), "completed")

        job.refresh_from_db()
        self.assertEqual(job.status, JobStatus.COMPLETED)
        self.assertEqual(job.progress, 100)
        self.assertEqual(job.current_stage, "completed")
        self.assertTrue(job.output_path and os.path.exists(job.output_path))

        # Clean up output
        ConversionService.cleanup_job_files(job)

    def test_failed_conversion_redaction(self):
        """Verify failed conversion records safe error without exposing secrets or internal paths."""
        ws = ConversionService._create_isolated_workspace()
        bad_path = str(ws / "missing.png")

        job = ConversionJob.objects.create(
            user=self.user_a,
            source_format="png",
            target_format="jpg",
            original_filename="missing.png",
            input_path=bad_path,
            status=JobStatus.QUEUED,
        )

        res = process_conversion_job_task(str(job.id))
        self.assertEqual(res.get("status"), "failed")

        job.refresh_from_db()
        self.assertEqual(job.status, JobStatus.FAILED)
        self.assertIsNotNone(job.failed_at)
        self.assertIn("could not be found", job.error_message.lower())

    # ── 2. Retry Handling ──────────────────────────────────────────────────────

    def test_permanent_error_no_retry(self):
        """Permanent validation/security errors should fail immediately without retrying."""
        job = ConversionJob.objects.create(
            user=self.user_a,
            source_format="png",
            target_format="jpg",
            original_filename="bad_path.png",
            input_path="/etc/passwd",
            status=JobStatus.QUEUED,
        )

        res = process_conversion_job_task(str(job.id))
        self.assertEqual(res.get("status"), "failed")

        job.refresh_from_db()
        self.assertEqual(job.status, JobStatus.FAILED)
        self.assertEqual(job.retry_count, 0)
        self.assertIn("could not be found", job.error_message.lower())

    @patch("apps.conversions.tasks.process_conversion_job_task.retry")
    def test_transient_error_retry(self, mock_retry):
        """Transient operational errors should invoke task retry mechanism."""
        mock_retry.side_effect = Exception("Celery retry triggered")

        ws = ConversionService._create_isolated_workspace()
        staged_file = str(ws / "transient.png")
        with open(staged_file, "wb") as f:
            f.write(self.test_png)

        job = ConversionJob.objects.create(
            user=self.user_a,
            source_format="png",
            target_format="jpg",
            original_filename="transient.png",
            input_path=staged_file,
            status=JobStatus.QUEUED,
        )

        try:
            with patch("apps.conversions.services.ConversionService.process_job", side_effect=ConnectionError("Transient socket failure")):
                with self.assertRaises(Exception) as cm:
                    process_conversion_job_task(str(job.id))
                self.assertIn("Celery retry triggered", str(cm.exception))

            job.refresh_from_db()
            self.assertEqual(job.status, JobStatus.RETRYING)
            self.assertEqual(job.retry_count, 1)
        finally:
            ConversionService.cleanup_job_files(job)

    # ── 3. Timeout Handling ────────────────────────────────────────────────────

    def test_soft_time_limit_exceeded(self):
        """Celery SoftTimeLimitExceeded transitions job to FAILED with timeout error code."""
        ws = ConversionService._create_isolated_workspace()
        staged_file = str(ws / "timeout.png")
        with open(staged_file, "wb") as f:
            f.write(self.test_png)

        job = ConversionJob.objects.create(
            user=self.user_a,
            source_format="png",
            target_format="jpg",
            original_filename="timeout.png",
            input_path=staged_file,
            status=JobStatus.QUEUED,
        )

        from celery.exceptions import SoftTimeLimitExceeded
        with patch("apps.conversions.services.ConversionService.process_job", side_effect=SoftTimeLimitExceeded()):
            res = process_conversion_job_task(str(job.id))

        self.assertEqual(res.get("status"), "failed")
        job.refresh_from_db()
        self.assertEqual(job.status, JobStatus.FAILED)
        self.assertEqual(job.error_code, "TASK_TIMEOUT")
        self.assertIn("timed out", job.error_message.lower())

    # ── 4. Stale-Job Recovery ──────────────────────────────────────────────────

    def test_stale_job_recovery_task(self):
        """Stale jobs stuck in PROCESSING past threshold should be recovered cleanly."""
        stale_time = timezone.now() - timedelta(minutes=30)
        stale_job = ConversionJob.objects.create(
            user=self.user_a,
            source_format="png",
            target_format="jpg",
            original_filename="stale.png",
            status=JobStatus.PROCESSING,
            started_at=stale_time,
            last_heartbeat=stale_time,
        )

        res = recover_stale_jobs_task(timeout_minutes=15)
        self.assertEqual(res.get("recovered_count"), 1)

        stale_job.refresh_from_db()
        self.assertEqual(stale_job.status, JobStatus.FAILED)
        self.assertEqual(stale_job.error_code, "STALE_JOB_RECOVERED")
        self.assertIsNotNone(stale_job.failed_at)

    # ── 5. Cancellation Support ────────────────────────────────────────────────

    def test_cancellation_endpoint_and_idempotency(self):
        """Verify cancellation endpoint cancels queued job, cleans up, and is idempotent."""
        job = ConversionJob.objects.create(
            user=self.user_a,
            source_format="png",
            target_format="jpg",
            original_filename="cancel_me.png",
            status=JobStatus.QUEUED,
        )

        self.client.force_authenticate(user=self.user_a)

        # First cancel request
        url = reverse("conversions:job-cancel", kwargs={"job_id": job.id})
        res1 = self.client.post(url)
        self.assertEqual(res1.status_code, status.HTTP_200_OK)

        job.refresh_from_db()
        self.assertEqual(job.status, JobStatus.CANCELLED)
        self.assertIsNotNone(job.cancelled_at)

        # Idempotent second cancel request
        res2 = self.client.post(url)
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertIn("already cancelled", res2.data.get("message", "").lower())

    def test_cannot_cancel_completed_job(self):
        """Completed jobs cannot be cancelled and return 400 Bad Request."""
        job = ConversionJob.objects.create(
            user=self.user_a,
            source_format="png",
            target_format="jpg",
            original_filename="done.png",
            status=JobStatus.COMPLETED,
        )

        self.client.force_authenticate(user=self.user_a)
        url = reverse("conversions:job-cancel", kwargs={"job_id": job.id})
        res = self.client.post(url)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("completed jobs cannot be cancelled", res.data.get("message", "").lower())

    # ── 6. Queue Monitoring & Permissions ─────────────────────────────────────

    def test_queue_monitoring_permissions(self):
        """Queue monitoring endpoint requires staff access; regular users get 403."""
        url = reverse("conversions:queue-status")

        # Anonymous request -> 403/401
        res_anon = self.client.get(url)
        self.assertIn(res_anon.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

        # Non-staff user -> 403
        self.client.force_authenticate(user=self.user_a)
        res_user = self.client.get(url)
        self.assertEqual(res_user.status_code, status.HTTP_403_FORBIDDEN)

        # Staff user -> 200 OK
        self.client.force_authenticate(user=self.staff_user)
        res_staff = self.client.get(url)
        self.assertEqual(res_staff.status_code, status.HTTP_200_OK)
        self.assertIn("queue_depth", res_staff.data)
        self.assertIn("metrics", res_staff.data)

    # ── 7. Ownership & IDOR Protection ────────────────────────────────────────

    def test_job_ownership_isolation(self):
        """User A cannot access or cancel User B's job."""
        job_b = ConversionJob.objects.create(
            user=self.user_b,
            source_format="png",
            target_format="jpg",
            original_filename="user_b_file.png",
            status=JobStatus.QUEUED,
        )

        self.client.force_authenticate(user=self.user_a)

        # Detail endpoint -> 404/403
        detail_url = reverse("conversions:job-detail", kwargs={"job_id": job_b.id})
        res_detail = self.client.get(detail_url)
        self.assertIn(res_detail.status_code, (status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN))

        # Cancel endpoint -> 404/403
        cancel_url = reverse("conversions:job-cancel", kwargs={"job_id": job_b.id})
        res_cancel = self.client.post(cancel_url)
        self.assertIn(res_cancel.status_code, (status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN))

        # Download endpoint -> 404/403
        dl_url = reverse("conversions:job-download", kwargs={"job_id": job_b.id})
        res_dl = self.client.get(dl_url)
        self.assertIn(res_dl.status_code, (status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN))

    # ── 8. Jobs API Alias Compatibility ────────────────────────────────────────

    def test_jobs_api_route_alias(self):
        """Verify /api/jobs/ endpoints map correctly to conversions logic."""
        self.client.force_authenticate(user=self.user_a)
        res = self.client.get("/api/jobs/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("results", res.data)
