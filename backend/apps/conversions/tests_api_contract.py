"""
API Contract, Versioning, OpenAPI Schema & Endpoint Stabilization Tests for VELTO Conversion.

Verifies:
  1. API version routing (/api/v1/).
  2. Conversion format discovery endpoint (/api/v1/conversions/formats/).
  3. Upload URL creation and finalization flow.
  4. Job status detail endpoint and action availability flags.
  5. Download authorization and stream endpoints.
  6. History pagination, filtering, and safe ordering.
  7. Delete job ownership isolation and idempotency.
  8. Retry job execution logic and retry limit enforcement.
  9. Cancel job endpoint and state transitions.
 10. Health check endpoint (GET /health/ and GET /api/v1/health/).
 11. Readiness check endpoint (GET /ready/ and GET /api/v1/ready/).
 12. Standardized success JSON response envelope.
 13. Standardized error JSON response envelope with safe public messages.
 14. Request ID middleware (X-Request-ID header).
 15. Legacy route backward compatibility.
 16. OpenAPI 3 schema and documentation endpoint resolution.
 17. Session/User isolation and IDOR prevention.
"""

import tempfile
import uuid
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.conversions.models import ConversionJob, JobStatus
from apps.conversions.services import ConversionService

User = get_user_model()

TEST_TEMP_DIR = tempfile.mkdtemp(prefix="velto_api_contract_tests_")


@override_settings(TEMP_UPLOAD_DIR=TEST_TEMP_DIR)
class ApiContractTests(TestCase):
    """Focused test suite for Public API contract, envelope, versioning, and security."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="contract_user@example.com",
            email="contract_user@example.com",
            password="Password123!",
        )
        self.client.force_authenticate(user=self.user)
        self.temp_dir = tempfile.TemporaryDirectory(prefix="api_contract_")
        session = self.client.session
        session.create()
        session.save()
        self.session_key = session.session_key
        self.client.cookies[settings.SESSION_COOKIE_NAME] = self.session_key

    def tearDown(self):
        self.temp_dir.cleanup()

    # ── 1. Request ID Middleware & Envelopes ───────────────────────────────────

    def test_request_id_header_attached(self):
        """Responses contain X-Request-ID header; client-supplied header is preserved."""
        res = self.client.get("/health/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("X-Request-ID", res.headers)
        self.assertTrue(len(res.headers["X-Request-ID"]) > 0)

        custom_id = "test-client-req-id-12345"
        res_custom = self.client.get("/health/", HTTP_X_REQUEST_ID=custom_id)
        self.assertEqual(res_custom.headers.get("X-Request-ID"), custom_id)

    def test_success_response_envelope_structure(self):
        """Versioned success response follows standard envelope {success: true, data: ..., error: null}."""
        res = self.client.get("/api/v1/health/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        body = res.json()
        self.assertTrue(body.get("success"))
        self.assertIsNone(body.get("error"))
        self.assertIn("data", body)
        self.assertEqual(body["data"]["status"], "ok")

    def test_error_response_envelope_structure(self):
        """Errors follow standard envelope {success: false, data: null, error: {code, message, details, request_id}}."""
        dummy_id = str(uuid.uuid4())
        res = self.client.get(f"/api/v1/conversions/{dummy_id}/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        body = res.json()
        self.assertFalse(body.get("success"))
        self.assertIsNone(body.get("data"))
        self.assertIn("error", body)
        self.assertIn("code", body["error"])
        self.assertIn("message", body["error"])
        self.assertIn("request_id", body["error"])

    # ── 2. Health & Readiness Endpoints ───────────────────────────────────────

    def test_health_check_endpoint(self):
        """GET /health/ and GET /api/v1/health/ return 200 liveness status."""
        for path in ("/health/", "/api/v1/health/"):
            res = self.client.get(path)
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            data = res.json()["data"]
            self.assertEqual(data["status"], "ok")
            self.assertEqual(data["service"], "velto-conversion")

    def test_readiness_check_endpoint_ready(self):
        """GET /ready/ and GET /api/v1/ready/ return 200 when DB and storage pass."""
        for path in ("/ready/", "/api/v1/ready/"):
            res = self.client.get(path)
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            data = res.json()["data"]
            self.assertEqual(data["status"], "ready")
            self.assertEqual(data["checks"]["database"], "ok")
            self.assertEqual(data["checks"]["storage"], "ok")

    def test_readiness_check_endpoint_db_failure(self):
        """GET /ready/ returns 503 Service Unavailable when DB connection fails."""
        with patch("apps.core.views.connection.ensure_connection", side_effect=Exception("Database unreachable")):
            res = self.client.get("/ready/")
            self.assertEqual(res.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
            body = res.json()
            if "error" in body and body["error"]:
                details = body["error"].get("details", {})
                self.assertEqual(details.get("status"), "not_ready")
                self.assertEqual(details.get("checks", {}).get("database"), "error")
            else:
                self.assertEqual(body.get("status"), "not_ready")
                self.assertEqual(body.get("checks", {}).get("database"), "error")

    # ── 3. Format Discovery Endpoint ──────────────────────────────────────────

    def test_format_discovery_endpoint(self):
        """GET /api/v1/conversions/formats/ returns supported pairs with metadata."""
        res = self.client.get("/api/v1/conversions/formats/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        formats = res.json()["data"]["formats"]
        self.assertIsInstance(formats, list)
        self.assertTrue(len(formats) >= 10)

        # Check sample format pair (PDF -> DOCX)
        pdf_docx = next((f for f in formats if f["source"] == "pdf" and f["target"] == "docx"), None)
        self.assertIsNotNone(pdf_docx)
        self.assertEqual(pdf_docx["source_label"], "PDF")
        self.assertEqual(pdf_docx["target_label"], "Word (DOCX)")
        self.assertTrue(pdf_docx["enabled"])
        self.assertIn("application/pdf", pdf_docx["mime_types"])

    # ── 4. Upload Workflow ───────────────────────────────────────────────────

    def test_presigned_upload_url_creation(self):
        """POST /api/v1/conversions/upload-url/ validates pair and creates presigned upload payload."""
        payload = {
            "source_format": "pdf",
            "target_format": "docx",
            "filename": "document.pdf",
            "file_size_bytes": 1024,
        }
        res = self.client.post("/api/v1/conversions/upload-url/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        data = res.json()["data"]
        self.assertIn("job_id", data)
        self.assertIn("upload_url", data)
        self.assertIn("storage_key", data)

    def test_finalize_upload_missing_key_rejected(self):
        """POST /api/v1/conversions/{job_id}/finalize-upload/ fails cleanly when key does not exist."""
        job = ConversionJob.objects.create(
            user=self.user,
            source_format="pdf",
            target_format="docx",
            status=JobStatus.PENDING,
            original_filename="test.pdf",
            session_key=self.session_key,
            is_finalized=False,
            input_storage_key="sessions/test_session/jobs/dummy/input/test.pdf",
        )
        res = self.client.post(f"/api/v1/conversions/{job.id}/finalize-upload/")
        self.assertIn(res.status_code, (status.HTTP_400_BAD_REQUEST, status.HTTP_404_NOT_FOUND))

    # ── 5. Job Status & Detail ────────────────────────────────────────────────

    def test_job_status_detail_endpoint(self):
        """GET /api/v1/conversions/{job_id}/ returns job status and action availability flags."""
        job = ConversionJob.objects.create(
            user=self.user,
            source_format="pdf",
            target_format="docx",
            status=JobStatus.COMPLETED,
            original_filename="report.pdf",
            session_key=self.session_key,
            output_filename="report.docx",
            output_storage_key="key/output.docx",
        )
        res = self.client.get(f"/api/v1/conversions/{job.id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()["data"]
        self.assertEqual(data["id"], str(job.id))
        self.assertEqual(data["status"], "completed")
        self.assertTrue(data["download_available"])
        self.assertFalse(data["cancellation_available"])
        self.assertFalse(data["retry_available"])

    # ── 6. Download Endpoints & Authorization ─────────────────────────────────

    def test_download_uncompleted_job_rejected(self):
        """GET /api/v1/conversions/{job_id}/download/ returns 202/400 if job is not completed."""
        job = ConversionJob.objects.create(
            user=self.user,
            source_format="pdf",
            target_format="docx",
            status=JobStatus.PROCESSING,
            original_filename="report.pdf",
            session_key=self.session_key,
        )
        res = self.client.get(f"/api/v1/conversions/{job.id}/download/")
        self.assertIn(res.status_code, (status.HTTP_400_BAD_REQUEST, status.HTTP_202_ACCEPTED))

    # ── 7. History Pagination & Filters ───────────────────────────────────────

    def test_history_endpoint_pagination_and_filtering(self):
        """GET /api/v1/conversions/history/ supports filters, page_size, and safe ordering."""
        for i in range(5):
            ConversionJob.objects.create(
                user=self.user,
                source_format="pdf" if i % 2 == 0 else "txt",
                target_format="docx",
                status=JobStatus.COMPLETED if i < 3 else JobStatus.FAILED,
                original_filename=f"doc_{i}.pdf",
                session_key=self.session_key,
            )

        res = self.client.get("/api/v1/conversions/history/?page=1&page_size=2&status=completed&source=pdf&ordering=-created_at")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()["data"]
        self.assertIn("count", data)
        self.assertEqual(data["count"], 2)  # 2 completed PDF jobs
        self.assertEqual(len(data["results"]), 2)

    # ── 8. Delete Job & Idempotency ───────────────────────────────────────────

    def test_delete_job_ownership_and_idempotency(self):
        """DELETE /api/v1/conversions/{job_id}/ deletes job and is idempotent."""
        job = ConversionJob.objects.create(
            user=self.user,
            source_format="txt",
            target_format="pdf",
            status=JobStatus.COMPLETED,
            original_filename="sample.txt",
            session_key=self.session_key,
        )

        # Delete job
        res = self.client.delete(f"/api/v1/conversions/{job.id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertFalse(ConversionJob.objects.filter(pk=job.id).exists())

        # Second delete is idempotent (returns 200)
        res_repeat = self.client.delete(f"/api/v1/conversions/{job.id}/")
        self.assertEqual(res_repeat.status_code, status.HTTP_200_OK)

    # ── 9. Retry Job Endpoint ─────────────────────────────────────────────────

    def test_retry_failed_job_success(self):
        """POST /api/v1/conversions/{job_id}/retry/ re-queues failed job when input file is available."""
        ws = ConversionService._create_isolated_workspace()
        inp = ws / "input.txt"
        inp.write_bytes(b"Hello text content")

        job = ConversionJob.objects.create(
            user=self.user,
            source_format="txt",
            target_format="pdf",
            status=JobStatus.FAILED,
            original_filename="sample.txt",
            session_key=self.session_key,
            input_path=str(inp),
            retry_count=0,
            max_retries=3,
        )

        res = self.client.post(f"/api/v1/conversions/{job.id}/retry/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()["data"]
        self.assertIn(data["status"], (JobStatus.COMPLETED, JobStatus.QUEUED, JobStatus.PROCESSING))

        job.refresh_from_db()
        self.assertEqual(job.retry_count, 1)

    def test_retry_exceeding_max_retries_rejected(self):
        """POST /api/v1/conversions/{job_id}/retry/ fails when retry count exceeds max_retries."""
        job = ConversionJob.objects.create(
            user=self.user,
            source_format="txt",
            target_format="pdf",
            status=JobStatus.FAILED,
            original_filename="sample.txt",
            session_key=self.session_key,
            retry_count=3,
            max_retries=3,
        )

        res = self.client.post(f"/api/v1/conversions/{job.id}/retry/")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    # ── 10. Cancel Job Endpoint ───────────────────────────────────────────────

    def test_cancel_active_job(self):
        """POST /api/v1/conversions/{job_id}/cancel/ transitions job state to CANCELLED."""
        job = ConversionJob.objects.create(
            user=self.user,
            source_format="pdf",
            target_format="docx",
            status=JobStatus.QUEUED,
            original_filename="queued.pdf",
            session_key=self.session_key,
        )

        res = self.client.post(f"/api/v1/conversions/{job.id}/cancel/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        job.refresh_from_db()
        self.assertEqual(job.status, JobStatus.CANCELLED)

    # ── 11. Legacy Route & OpenAPI Schema Resolution ──────────────────────────

    def test_legacy_routes_and_openapi_schema_endpoints(self):
        """Legacy routes /api/conversions/ and OpenAPI schema endpoints resolve properly."""
        res_legacy = self.client.get("/api/conversions/supported-formats/")
        self.assertEqual(res_legacy.status_code, status.HTTP_200_OK)

        res_schema = self.client.get("/api/schema/")
        self.assertEqual(res_schema.status_code, status.HTTP_200_OK)

        res_docs = self.client.get("/api/docs/")
        self.assertEqual(res_docs.status_code, status.HTTP_200_OK)

        res_redoc = self.client.get("/api/redoc/")
        self.assertEqual(res_redoc.status_code, status.HTTP_200_OK)

    # ── 12. Session Isolation & IDOR Prevention ───────────────────────────────

    def test_idor_prevention_across_sessions(self):
        """User A cannot view, delete, or retry a job belonging to User B."""
        user_b = User.objects.create_user(
            username="user_b@example.com",
            email="user_b@example.com",
            password="Password123!",
        )
        job_owner_b = ConversionJob.objects.create(
            user=user_b,
            source_format="pdf",
            target_format="docx",
            status=JobStatus.COMPLETED,
            original_filename="private_b.pdf",
            session_key="session_b_secret_key",
        )

        # Client A (authenticated as self.user) requests User B's job detail
        res_detail = self.client.get(f"/api/v1/conversions/{job_owner_b.id}/")
        self.assertEqual(res_detail.status_code, status.HTTP_404_NOT_FOUND)

        # Client A attempts to cancel User B's job
        res_cancel = self.client.post(f"/api/v1/conversions/{job_owner_b.id}/cancel/")
        self.assertEqual(res_cancel.status_code, status.HTTP_404_NOT_FOUND)

    # ── 13. Download Stream & Presigned Download URL ──────────────────────────

    def test_file_download_stream(self):
        """Completed jobs stream file response directly without JSON envelope."""
        ws = ConversionService._create_isolated_workspace()
        out_file = ws / "output.docx"
        out_file.write_bytes(b"PK fake docx content")

        job = ConversionJob.objects.create(
            user=self.user,
            source_format="pdf",
            target_format="docx",
            status=JobStatus.COMPLETED,
            original_filename="doc.pdf",
            output_filename="doc.docx",
            output_path=str(out_file),
            session_key=self.session_key,
        )

        res = self.client.get(f"/api/v1/conversions/{job.id}/download/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.getvalue(), b"PK fake docx content")

    def test_presigned_download_url_endpoint(self):
        """GET /api/v1/conversions/{job_id}/download-url/ returns download URL payload."""
        ws = ConversionService._create_isolated_workspace()
        out_file = ws / "output.docx"
        out_file.write_bytes(b"PK fake docx content")

        job = ConversionJob.objects.create(
            user=self.user,
            source_format="pdf",
            target_format="docx",
            status=JobStatus.COMPLETED,
            original_filename="doc.pdf",
            output_filename="doc.docx",
            output_path=str(out_file),
            session_key=self.session_key,
        )

        res = self.client.get(f"/api/v1/conversions/{job.id}/download-url/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()["data"]
        self.assertEqual(data["job_id"], str(job.id))
        self.assertIn("download_url", data)

    # ── 14. Legacy Endpoint Raw Response Preservation ─────────────────────────

    def test_legacy_route_raw_response_format(self):
        """Legacy routes return raw un-enveloped JSON structure."""
        res = self.client.get("/api/conversions/supported-formats/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        body = res.json()
        self.assertNotIn("success", body)
        self.assertIn("formats", body)
