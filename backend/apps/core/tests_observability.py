"""
Observability and Operational Monitoring Test Suite for VELTO Conversion.

Tests:
  - Structured JSON logging & sensitive data redaction filter.
  - Request-ID correlation middleware & route normalization.
  - Conversion duration tracking & error categorization.
  - Prometheus metrics collection & secure exposition at /internal/metrics/.
  - Health and readiness endpoints (/health/, /ready/, /api/v1/ready/).
  - Sentry safe initialization & header redaction filter.
  - Staff operational monitoring endpoint (/api/v1/internal/operations/).
"""

import json
import logging
import uuid
from unittest.mock import patch, MagicMock

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.conversions.models import ConversionJob, JobStatus
from apps.conversions.services import ConversionService
from apps.core.exceptions import derive_error_category
from apps.core.logging import VeltoJsonFormatter, SensitiveDataRedactionFilter, log_event
from apps.core.metrics import (
    record_conversion_metrics,
    record_storage_metrics,
    record_celery_task_started,
    get_metrics_summary,
)

User = get_user_model()


class StructuredLoggingTestCase(TestCase):
    """Test JSON log formatting and sensitive field redaction."""

    def test_velto_json_formatter(self):
        formatter = VeltoJsonFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="User login successful",
            args=(),
            exc_info=None,
        )
        record.event = "auth.login.success"
        record.request_id = "req_12345"
        record.user_id = "usr_99"

        formatted = formatter.format(record)
        data = json.loads(formatted)

        self.assertEqual(data["event"], "auth.login.success")
        self.assertEqual(data["request_id"], "req_12345")
        self.assertEqual(data["user_id"], "usr_99")
        self.assertEqual(data["level"], "INFO")
        self.assertEqual(data["service"], "velto-backend")
        self.assertIn("timestamp", data)

    def test_sensitive_data_redaction_filter(self):
        redaction_filter = SensitiveDataRedactionFilter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="User credentials password=Secret123 token=Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxfQ.test",
            args=(),
            exc_info=None,
        )
        redaction_filter.filter(record)
        self.assertNotIn("Secret123", record.msg)
        self.assertIn("[REDACTED]", record.msg)


class CorrelationAndMiddlewareTestCase(TestCase):
    """Test Request-ID middleware generation, propagation, and header output."""

    def setUp(self):
        self.client = APIClient()

    def test_request_id_generated_when_absent(self):
        response = self.client.get("/health/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("X-Request-ID", response.headers)
        self.assertTrue(len(response.headers["X-Request-ID"]) > 0)

    def test_incoming_request_id_preserved(self):
        custom_id = "req_custom_test_12345"
        response = self.client.get("/health/", HTTP_X_REQUEST_ID=custom_id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.headers.get("X-Request-ID"), custom_id)


class ErrorTaxonomyTestCase(TestCase):
    """Test centralized error categorization mapping."""

    def test_error_category_mapping(self):
        from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
        from apps.conversions.security import FileTooLarge, SecurityValidationError
        from apps.conversions.engines.base import ConversionError

        self.assertEqual(derive_error_category(AuthenticationFailed()), "authentication_error")
        self.assertEqual(derive_error_category(PermissionDenied()), "authorization_error")
        self.assertEqual(derive_error_category(FileTooLarge("Too big")), "file_error")
        self.assertEqual(derive_error_category(SecurityValidationError("Unsafe")), "validation_error")
        self.assertEqual(derive_error_category(ConversionError("Engine failed")), "conversion_engine_error")
        self.assertEqual(derive_error_category(Exception("Unknown")), "internal_error")


class ConversionDurationTestCase(TestCase):
    """Test ConversionJob duration_ms and error_category field population."""

    def test_conversion_job_duration_tracking_success(self):
        job_id = uuid.uuid4().hex
        workspace = ConversionService._create_isolated_workspace(job_id)
        input_p = workspace / "test_input.pdf"
        input_p.write_bytes(b"%PDF-1.4 dummycontent")
        out_p = workspace / "test_out.docx"
        out_p.write_bytes(b"PK\x03\x04 dummy docx content")

        job = ConversionJob.objects.create(
            id=job_id,
            source_format="pdf",
            target_format="docx",
            status=JobStatus.PENDING,
            original_filename="document.pdf",
            file_size_bytes=1024,
            input_path=str(input_p),
            is_finalized=True,
        )

        with patch("apps.conversions.services.engine_registry.get") as mock_get_engine, \
             patch("apps.conversions.services.validate_mime_type"), \
             patch("apps.conversions.services.validate_file_signature"), \
             patch("apps.conversions.services.scan_file_security"), \
             patch("apps.conversions.engines.validators.validate_conversion_output"):

            mock_engine_cls = MagicMock()
            mock_engine_inst = MagicMock()
            mock_engine_inst.convert.return_value = str(out_p)
            mock_engine_cls.return_value = mock_engine_inst
            mock_get_engine.return_value = mock_engine_cls

            updated_job = ConversionService.process_job(job)

            self.assertEqual(updated_job.status, JobStatus.COMPLETED)
            self.assertIsNotNone(updated_job.duration_ms)
            self.assertGreaterEqual(updated_job.duration_ms, 0)
            self.assertIsNotNone(updated_job.completed_at)

    def test_conversion_job_duration_tracking_failure(self):
        job = ConversionJob.objects.create(
            id=uuid.uuid4().hex,
            source_format="pdf",
            target_format="docx",
            status=JobStatus.PENDING,
            original_filename="corrupted.pdf",
            file_size_bytes=1024,
            is_finalized=True,
        )

        with patch("apps.conversions.services.engine_registry.get") as mock_get_engine:
            mock_get_engine.return_value = None  # engine missing -> triggers failure

            updated_job = ConversionService.process_job(job)

            self.assertEqual(updated_job.status, JobStatus.FAILED)
            self.assertIsNotNone(updated_job.duration_ms)
            self.assertGreaterEqual(updated_job.duration_ms, 0)
            self.assertEqual(updated_job.error_category, "conversion_engine_error")


class PrometheusMetricsTestCase(TestCase):
    """Test metrics calculation and exposition."""

    def setUp(self):
        self.client = APIClient()
        self.staff_user = User.objects.create_user(
            email="staff@velto.app",
            username="staff_user",
            password="StaffPassword123!",
            is_staff=True,
        )

    def test_record_conversion_metrics(self):
        record_conversion_metrics(
            status=JobStatus.COMPLETED,
            source_format="pdf",
            target_format="docx",
            duration_seconds=1.2,
            queue_wait_seconds=0.3,
        )
        summary = get_metrics_summary()
        self.assertIn("conversions_total", summary)

    def test_metrics_endpoint_access_control(self):
        with override_settings(METRICS_TOKEN="secret_metrics_token_123"):
            res_no_token = self.client.get("/internal/metrics/")
            self.assertIn(res_no_token.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

            res_valid_token = self.client.get("/internal/metrics/", HTTP_AUTHORIZATION="Bearer secret_metrics_token_123")
            self.assertEqual(res_valid_token.status_code, status.HTTP_200_OK)
            self.assertIn("velto_conversions_total", res_valid_token.content.decode("utf-8"))

    def test_metrics_endpoint_staff_user_access(self):
        with override_settings(METRICS_TOKEN=None):
            self.client.force_authenticate(user=self.staff_user)
            res = self.client.get("/internal/metrics/")
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            self.assertIn("# HELP", res.content.decode("utf-8"))


class HealthAndReadinessTestCase(TestCase):
    """Test liveness and readiness health checks."""

    def setUp(self):
        self.client = APIClient()

    def test_liveness_endpoint(self):
        res = self.client.get("/health/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["status"], "ok")

    def test_readiness_endpoint_success(self):
        res = self.client.get("/ready/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["status"], "ready")
        self.assertIn("checks", data["data"])

    def test_readiness_endpoint_database_failure(self):
        with patch("apps.core.views.connection.ensure_connection", side_effect=Exception("Database connection lost")):
            res = self.client.get("/ready/")
            self.assertEqual(res.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
            body = res.json()
            self.assertFalse(body["success"])
            self.assertEqual(body["error"]["details"]["checks"]["database"], "error")
        # Force Django to create a fresh DB connection after simulating failure
        connection.close()


class OperationalMonitoringTestCase(TestCase):
    """Test staff-only operational monitoring endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.regular_user = User.objects.create_user(
            email="user@velto.app",
            username="regular_user",
            password="UserPassword123!",
        )
        self.staff_user = User.objects.create_user(
            email="ops@velto.app",
            username="ops_user",
            password="OpsPassword123!",
            is_staff=True,
        )

    def test_unauthenticated_access_denied(self):
        res = self.client.get("/api/v1/internal/operations/")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_regular_user_access_denied(self):
        self.client.force_authenticate(user=self.regular_user)
        res = self.client.get("/api/v1/internal/operations/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_user_access_granted(self):
        self.client.force_authenticate(user=self.staff_user)
        res = self.client.get("/api/v1/internal/operations/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()
        self.assertTrue(data["success"])
        ops_data = data["data"]
        self.assertIn("users", ops_data)
        self.assertIn("conversions", ops_data)
        self.assertIn("total", ops_data["users"])
        self.assertIn("successful", ops_data["conversions"])
        self.assertIn("failed", ops_data["conversions"])


class SentryConfigurationTestCase(TestCase):
    """Test Sentry before_send sensitive data filter."""

    def test_sentry_before_send_redaction(self):
        from config.settings import _sentry_before_send
        event = {
            "request": {
                "headers": {
                    "Authorization": "Bearer secret_jwt_token",
                    "Cookie": "sessionid=xyz",
                    "User-Agent": "Mozilla/5.0",
                }
            }
        }
        filtered = _sentry_before_send(event, {})
        headers = filtered["request"]["headers"]
        self.assertEqual(headers["Authorization"], "[REDACTED]")
        self.assertEqual(headers["Cookie"], "[REDACTED]")
        self.assertEqual(headers["User-Agent"], "Mozilla/5.0")
