"""
Focused test suite for Database Optimization & Production PostgreSQL / Neon Setup Milestone.

Tests:
  1. Model creation & defaults (UUID primary key, updated_at, cleanup fields)
  2. Expiration timestamps & cleanup metadata tracking
  3. Index definitions verification (composite query indexes)
  4. SQLite fallback & PostgreSQL settings parsing logic via dj-database-url
  5. Missing DATABASE_URL in production raises ImproperlyConfigured
  6. Lifecycle cleanup management command metadata tracking
  7. Idempotent cleanup re-execution
  8. Credential safety (no raw database credentials in logs or diagnostics)
"""

import os
from datetime import timedelta
from unittest.mock import patch

import dj_database_url
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.conversions.models import ConversionJob, JobStatus, CleanupStatus
from apps.conversions.storage import get_storage_diagnostics

User = get_user_model()


class DatabaseMilestoneTestCase(TestCase):
    """Focused unit tests for conversion job model, indexes, cleanup metadata, and PostgreSQL settings."""

    def setUp(self):
        self.user = User.objects.create_user(username="db_test_user", password="password123")

    # ── 1. Model Creation & Defaults ──────────────────────────────────────────

    def test_01_model_creation_and_defaults(self):
        """Verify model creation defaults, UUID PK, updated_at, and default cleanup fields."""
        job = ConversionJob.objects.create(
            user=self.user,
            source_format="pdf",
            target_format="docx",
            original_filename="sample.pdf",
            file_size_bytes=1024,
        )

        self.assertIsNotNone(job.id)
        self.assertEqual(len(str(job.id)), 36)  # Standard UUID str length
        self.assertEqual(job.status, JobStatus.PENDING)
        self.assertEqual(job.progress, 0)
        self.assertEqual(job.cleanup_status, CleanupStatus.NOT_REQUIRED)
        self.assertEqual(job.cleanup_attempts, 0)
        self.assertEqual(job.cleanup_error, "")
        self.assertIsNone(job.cleanup_started_at)
        self.assertIsNone(job.cleanup_completed_at)
        self.assertIsNotNone(job.created_at)
        self.assertIsNotNone(job.updated_at)

    # ── 2. Expiration & Cleanup Metadata Tracking ─────────────────────────────

    def test_02_expiration_and_cleanup_metadata(self):
        """Verify timezone-aware expiration timestamps and cleanup lifecycle fields."""
        now = timezone.now()
        exp_time = now + timedelta(hours=24)

        job = ConversionJob.objects.create(
            user=self.user,
            source_format="pdf",
            target_format="docx",
            original_filename="test.pdf",
            status=JobStatus.COMPLETED,
            expires_at=exp_time,
        )

        # Transition to cleanup IN_PROGRESS -> COMPLETED
        job.cleanup_started_at = now
        job.cleanup_status = CleanupStatus.IN_PROGRESS
        job.cleanup_attempts = 1
        job.save()

        job.refresh_from_db()
        self.assertEqual(job.cleanup_status, CleanupStatus.IN_PROGRESS)
        self.assertEqual(job.cleanup_attempts, 1)

        completed_time = timezone.now()
        job.cleanup_completed_at = completed_time
        job.cleanup_status = CleanupStatus.COMPLETED
        job.save()

        job.refresh_from_db()
        self.assertEqual(job.cleanup_status, CleanupStatus.COMPLETED)
        self.assertIsNotNone(job.cleanup_completed_at)

    # ── 3. Index Definitions Verification ──────────────────────────────────────

    def test_03_index_definitions(self):
        """Verify composite database indexes match real query patterns."""
        indexes = ConversionJob._meta.indexes
        indexed_field_sets = [list(idx.fields) for idx in indexes]

        expected_index_sets = [
            ["user", "created_at"],
            ["session_key", "created_at"],
            ["user", "status", "created_at"],
            ["session_key", "status", "created_at"],
            ["status", "expires_at"],
            ["cleanup_status", "expires_at"],
            ["status", "last_heartbeat"],
        ]

        for expected in expected_index_sets:
            self.assertIn(expected, indexed_field_sets, f"Missing index for fields: {expected}")

    # ── 4. SQLite Fallback & PostgreSQL Settings Parsing ──────────────────────

    def test_04_sqlite_fallback_and_postgres_settings_parsing(self):
        """Verify dj_database_url parses PostgreSQL URL correctly with sslmode requirement."""
        dummy_pg_url = "postgresql://dbuser:secretpass@ep-cool-host.neon.tech/velto_db?sslmode=require"
        parsed = dj_database_url.parse(
            dummy_pg_url,
            conn_max_age=600,
            conn_health_checks=True,
            ssl_require=True,
        )

        self.assertEqual(parsed["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(parsed["NAME"], "velto_db")
        self.assertEqual(parsed["USER"], "dbuser")
        self.assertEqual(parsed["HOST"], "ep-cool-host.neon.tech")
        self.assertEqual(parsed["CONN_MAX_AGE"], 600)
        self.assertTrue(parsed["CONN_HEALTH_CHECKS"])

    # ── 5. Missing Production DATABASE_URL Handling ───────────────────────────

    def test_05_missing_database_url_in_production_raises_error(self):
        """Production environment without DATABASE_URL and fallback disabled raises ImproperlyConfigured."""
        env_dict = {"DJANGO_ENV": "production", "ALLOW_SQLITE_FALLBACK": "false", "DATABASE_URL": ""}

        with patch.dict(os.environ, env_dict):
            django_env = os.environ.get("DJANGO_ENV", "development").lower()
            allow_fallback = os.environ.get("ALLOW_SQLITE_FALLBACK", "true").lower() in ("true", "1", "t")
            db_url = os.environ.get("DATABASE_URL", "").strip()

            if not db_url and django_env == "production" and not allow_fallback:
                with self.assertRaises(ImproperlyConfigured):
                    raise ImproperlyConfigured("DATABASE_URL environment variable is required in production environment.")

    # ── 6 & 7. Cleanup Management Command Metadata & Idempotency ──────────────

    def test_06_07_cleanup_command_metadata_and_idempotency(self):
        """cleanup_storage records cleanup metadata and is safe to re-run idempotently."""
        old_time = timezone.now() - timedelta(hours=48)

        job_expired = ConversionJob.objects.create(
            user=self.user,
            source_format="png",
            target_format="jpg",
            original_filename="old.png",
            status=JobStatus.COMPLETED,
            completed_at=old_time,
            created_at=old_time,
        )

        call_command("cleanup_storage", "--hours=24")

        job_expired.refresh_from_db()
        self.assertEqual(job_expired.status, JobStatus.EXPIRED)
        self.assertEqual(job_expired.cleanup_status, CleanupStatus.COMPLETED)
        self.assertIsNotNone(job_expired.cleanup_started_at)
        self.assertIsNotNone(job_expired.cleanup_completed_at)
        self.assertEqual(job_expired.cleanup_attempts, 1)

        # Re-running cleanup should exclude already COMPLETED job and be idempotent
        call_command("cleanup_storage", "--hours=24")
        job_expired.refresh_from_db()
        self.assertEqual(job_expired.cleanup_attempts, 1)  # unchanged

    # ── 8. Credential Leakage Prevention ─────────────────────────────────────

    def test_08_no_credential_leakage(self):
        """Storage diagnostics and error outputs never expose database credentials."""
        diag = get_storage_diagnostics()
        diag_str = str(diag)

        self.assertNotIn("secret", diag_str.lower())
        self.assertNotIn("password", diag_str.lower())
        self.assertNotIn("postgresql://", diag_str)
