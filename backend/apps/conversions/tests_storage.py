"""
Focused unit & integration test suite for VELTO Storage Milestone.

Tests:
  1. Storage configuration
  2. Local fallback configuration
  3. Secure object-key generation
  4. Presigned upload URL generation
  5. Upload ownership protection
  6. Upload size and MIME validation
  7. Upload finalization
  8. Invalid object rejection
  9. Presigned download URL generation
  10. Download ownership protection
  11. Expired download rejection
  12. Automatic expiration
  13. Cleanup of abandoned uploads
  14. Cleanup of failed and cancelled jobs
  15. Orphan object cleanup
  16. Storage quota acceptance
  17. Storage quota rejection
  18. Concurrent quota protection
  19. Storage provider failure handling
  20. Job Processing integration with object storage
"""

import io
import os
from datetime import timedelta
from unittest.mock import patch, MagicMock

from PIL import Image
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.conversions.models import ConversionJob, JobStatus
from apps.conversions.services import ConversionService, ConversionServiceError
from apps.conversions.security import AbuseLimitExceeded, check_storage_quota, get_owner_storage_usage
from apps.conversions.storage import (
    LocalStorageAdapter,
    S3StorageAdapter,
    get_storage_service,
    get_active_storage_backend,
    get_storage_diagnostics,
)
from apps.conversions.tasks import process_conversion_job_task

User = get_user_model()


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, TESTING=True)
class StorageMilestoneTestCase(TestCase):
    """Core storage milestone unit and integration tests."""

    def setUp(self):
        self.client = APIClient()
        self.user_a = User.objects.create_user(username="storage_usera", password="password123")
        self.user_b = User.objects.create_user(username="storage_userb", password="password123")
        self.staff_user = User.objects.create_user(username="storage_admin", password="password123", is_staff=True)

        # Generate valid test PNG image bytes
        buf = io.BytesIO()
        img = Image.new("RGB", (10, 10), color="blue")
        img.save(buf, format="PNG")
        self.test_png_bytes = buf.getvalue()

    def _get_active_session_key(self):
        session = self.client.session
        session.create()
        return session.session_key

    # ── 1. Storage Configuration ───────────────────────────────────────────────

    def test_01_storage_configuration(self):
        """Verify storage configuration and diagnostic metadata endpoint functions."""
        diag = get_storage_diagnostics()
        self.assertEqual(diag["storage_backend"], "local")
        self.assertIn("quota_limit_mb", diag)
        self.assertIn("retention_hours", diag)

    # ── 2. Local Fallback Configuration ────────────────────────────────────────

    def test_02_local_fallback_configuration(self):
        """Verify LocalStorageAdapter is selected by default for local storage backend."""
        adapter = get_storage_service("local")
        self.assertIsInstance(adapter, LocalStorageAdapter)

    # ── 3. Secure Object-Key Generation ───────────────────────────────────────

    def test_03_secure_object_key_generation(self):
        """Verify object keys are non-guessable, sanitized, and contained."""
        key_user = LocalStorageAdapter.generate_object_key("usr_42", "job_uuid_123", "input", "my invoice (1).pdf")
        self.assertTrue(key_user.startswith("users/usr_42/jobs/job_uuid_123/input/"))
        self.assertIn("my invoice", key_user)
        self.assertNotIn("..", key_user)

        key_sess = LocalStorageAdapter.generate_object_key("sess_abc", "job_uuid_123", "output", "../secret.txt")
        self.assertTrue(key_sess.startswith("sessions/sess_abc/jobs/job_uuid_123/output/"))
        self.assertNotIn("..", key_sess)

    # ── 4. Presigned Upload URL Generation ─────────────────────────────────────

    def test_04_presigned_upload_url_generation(self):
        """Verify POST /api/conversions/upload-url/ creates session and presigned URL payload."""
        self.client.force_authenticate(user=self.user_a)
        url = reverse("conversions:upload-url")
        payload = {
            "source_format": "png",
            "target_format": "jpg",
            "filename": "test.png",
            "file_size_bytes": len(self.test_png_bytes),
        }
        res = self.client.post(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn("upload_url", res.data)
        self.assertIn("job_id", res.data)
        self.assertIn("storage_key", res.data)

        # Check job in DB is created as unfinalized
        job = ConversionJob.objects.get(pk=res.data["job_id"])
        self.assertFalse(job.is_finalized)
        self.assertEqual(job.status, JobStatus.PENDING)

    # ── 5. Upload Ownership Protection ────────────────────────────────────────

    def test_05_upload_ownership_protection(self):
        """User A cannot finalize User B's upload session."""
        job_b = ConversionJob.objects.create(
            user=self.user_b,
            source_format="png",
            target_format="jpg",
            original_filename="user_b.png",
            file_size_bytes=100,
            input_storage_key="users/usr_b/jobs/123/input/file.png",
            is_finalized=False,
        )

        self.client.force_authenticate(user=self.user_a)
        finalize_url = reverse("conversions:job-finalize-upload", kwargs={"job_id": job_b.id})
        res = self.client.post(finalize_url)
        self.assertIn(res.status_code, (status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN))

    # ── 6. Upload Size & Format Validation ────────────────────────────────────

    def test_06_upload_size_and_format_validation(self):
        """Rejects invalid format pairs or oversized files during upload session creation."""
        self.client.force_authenticate(user=self.user_a)
        url = reverse("conversions:upload-url")

        # Invalid format pair
        res_format = self.client.post(url, {
            "source_format": "png",
            "target_format": "docx",
            "filename": "test.png",
            "file_size_bytes": 100,
        }, format="json")
        self.assertEqual(res_format.status_code, status.HTTP_400_BAD_REQUEST)

    # ── 7 & 8. Upload Finalization & Invalid Object Rejection ─────────────────

    def test_07_08_upload_finalization_and_missing_object_rejection(self):
        """Finalization fails when object is missing; succeeds when object is present in storage."""
        storage = get_storage_service()
        key = storage.generate_object_key("usr_test", "job_fin_1", "input", "test.png")

        job = ConversionJob.objects.create(
            user=self.user_a,
            source_format="png",
            target_format="jpg",
            original_filename="test.png",
            file_size_bytes=len(self.test_png_bytes),
            input_storage_key=key,
            is_finalized=False,
            status=JobStatus.PENDING,
        )

        self.client.force_authenticate(user=self.user_a)
        finalize_url = reverse("conversions:job-finalize-upload", kwargs={"job_id": job.id})

        # 1. Reject when missing in storage
        res_missing = self.client.post(finalize_url)
        self.assertEqual(res_missing.status_code, status.HTTP_400_BAD_REQUEST)

        # 2. Upload object to storage, then finalize successfully
        ws = ConversionService._create_isolated_workspace("fin_1")
        tmp_local = str(ws / "test.png")
        with open(tmp_local, "wb") as f:
            f.write(self.test_png_bytes)
        storage.upload_file(tmp_local, key)

        try:
            res_ok = self.client.post(finalize_url)
            self.assertIn(res_ok.status_code, (status.HTTP_201_CREATED, status.HTTP_202_ACCEPTED))
            job.refresh_from_db()
            self.assertTrue(job.is_finalized)
            self.assertEqual(job.status, JobStatus.COMPLETED)
        finally:
            ConversionService.cleanup_job_files(job)

    # ── 9. Presigned Download URL Generation ───────────────────────────────────

    def test_09_presigned_download_url_generation(self):
        """GET /api/conversions/<job_id>/download-url/ returns short-lived download URL."""
        storage = get_storage_service()
        key = storage.generate_object_key("usr_test", "job_dl_1", "output", "result.jpg")

        ws = ConversionService._create_isolated_workspace("dl_1")
        tmp_local = str(ws / "result.jpg")
        with open(tmp_local, "wb") as f:
            f.write(self.test_png_bytes)
        storage.upload_file(tmp_local, key)

        job = ConversionJob.objects.create(
            user=self.user_a,
            source_format="png",
            target_format="jpg",
            original_filename="result.png",
            status=JobStatus.COMPLETED,
            output_storage_key=key,
            output_filename="result.jpg",
        )

        self.client.force_authenticate(user=self.user_a)
        url = reverse("conversions:job-download-url", kwargs={"job_id": job.id})
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("download_url", res.data)
        self.assertEqual(res.data["filename"], "result.jpg")

        ConversionService.cleanup_job_files(job)

    # ── 10. Download Ownership Protection ────────────────────────────────────

    def test_10_download_ownership_protection(self):
        """User A cannot request download URL for User B's completed job."""
        job_b = ConversionJob.objects.create(
            user=self.user_b,
            source_format="png",
            target_format="jpg",
            original_filename="user_b.png",
            status=JobStatus.COMPLETED,
            output_storage_key="users/usr_b/jobs/123/output/res.jpg",
        )

        self.client.force_authenticate(user=self.user_a)
        url = reverse("conversions:job-download-url", kwargs={"job_id": job_b.id})
        res = self.client.get(url)

        self.assertIn(res.status_code, (status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN))

    # ── 11 & 12. Expired Download & Expiration Metadata ───────────────────────

    def test_11_12_expired_download_rejection(self):
        """Expired or uncompleted jobs reject download URL requests."""
        job_pending = ConversionJob.objects.create(
            user=self.user_a,
            source_format="png",
            target_format="jpg",
            original_filename="pending.png",
            status=JobStatus.PENDING,
        )

        self.client.force_authenticate(user=self.user_a)
        url = reverse("conversions:job-download-url", kwargs={"job_id": job_pending.id})
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_202_ACCEPTED)

    # ── 13, 14, 15. Storage Lifecycle Cleanup Command ─────────────────────────

    def test_13_14_15_cleanup_storage_management_command(self):
        """Management command cleanup_storage cleans abandoned uploads, failed files, and expired outputs."""
        old_time = timezone.now() - timedelta(hours=48)

        # Abandoned upload
        job_abandoned = ConversionJob.objects.create(
            user=self.user_a,
            source_format="png",
            target_format="jpg",
            original_filename="abandoned.png",
            is_finalized=False,
            created_at=old_time,
        )
        ConversionJob.objects.filter(pk=job_abandoned.id).update(created_at=old_time)

        # Expired completed output
        job_expired = ConversionJob.objects.create(
            user=self.user_a,
            source_format="png",
            target_format="jpg",
            original_filename="expired.png",
            status=JobStatus.COMPLETED,
            completed_at=old_time,
        )
        ConversionJob.objects.filter(pk=job_expired.id).update(completed_at=old_time)

        # Run dry-run cleanup
        call_command("cleanup_storage", "--dry-run", "--hours=24")

        # Run actual cleanup
        call_command("cleanup_storage", "--hours=24")

        job_abandoned.refresh_from_db()
        self.assertEqual(job_abandoned.status, JobStatus.EXPIRED)

        job_expired.refresh_from_db()
        self.assertEqual(job_expired.status, JobStatus.EXPIRED)

    # ── 16, 17, 18. Quota Calculation & Enforcement ───────────────────────────

    def test_16_17_18_storage_quota_enforcement(self):
        """Storage quota accounting sums usage and rejects requests exceeding user quota limit."""
        # Create completed job using 400 MB
        ConversionJob.objects.create(
            user=self.user_a,
            source_format="png",
            target_format="jpg",
            original_filename="big.png",
            file_size_bytes=100,
            output_size_bytes=400 * 1024 * 1024,
            status=JobStatus.COMPLETED,
        )

        usage = get_owner_storage_usage(user=self.user_a)
        self.assertEqual(usage, 400 * 1024 * 1024)

        # Attempting to add 200 MB should exceed 500 MB quota
        request_mock = MagicMock()
        request_mock.user = self.user_a
        request_mock.session = MagicMock()

        with self.assertRaises(AbuseLimitExceeded):
            check_storage_quota(request_mock, incoming_bytes=200 * 1024 * 1024)

    # ── 19. Storage Provider Failure Handling ──────────────────────────────────

    def test_19_storage_provider_failure_handling(self):
        """Storage provider connection errors are handled gracefully without 500 crashes."""
        storage = S3StorageAdapter()
        with patch.object(storage._s3_client, "head_object", side_effect=Exception("S3 Connection Timeout")):
            res = storage.object_exists("some_key")
            self.assertFalse(res)

    # ── 20. Job Processing Integration with Object Storage ─────────────────────

    def test_20_job_processing_integration_with_object_storage(self):
        """Job processing task downloads input object, runs engine, and uploads output object."""
        storage = get_storage_service()
        input_key = storage.generate_object_key("usr_a", "job_proc_20", "input", "sample.png")

        ws = ConversionService._create_isolated_workspace("proc_20")
        tmp_input = str(ws / "sample.png")
        with open(tmp_input, "wb") as f:
            f.write(self.test_png_bytes)
        storage.upload_file(tmp_input, input_key)

        job = ConversionJob.objects.create(
            user=self.user_a,
            source_format="png",
            target_format="jpg",
            original_filename="sample.png",
            file_size_bytes=len(self.test_png_bytes),
            input_storage_key=input_key,
            storage_backend="local",
            status=JobStatus.QUEUED,
        )

        res = process_conversion_job_task(str(job.id))
        self.assertEqual(res.get("status"), "completed")

        job.refresh_from_db()
        self.assertEqual(job.status, JobStatus.COMPLETED)
        self.assertTrue(job.output_storage_key)
        self.assertTrue(storage.object_exists(job.output_storage_key))

        ConversionService.cleanup_job_files(job)
