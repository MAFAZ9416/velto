"""
Tests for the conversions app.

Coverage:
  - Format definitions (supported pairs, labels, MIME types, extensions)
  - ConversionJob model (creation, status, is_terminal)
  - Anonymous ConversionJob creation via API
  - File upload validation (size, extension, MIME, format pair)
  - Session-based ownership filtering
  - Job detail access control
  - Supported formats endpoint
"""

import io
import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.conversions.formats import (
    SUPPORTED_PAIRS,
    FORMAT_LABELS,
    ALLOWED_EXTENSIONS,
    ALLOWED_MIME_TYPES,
    is_valid_conversion,
    get_supported_formats_response,
)
from apps.conversions.models import ConversionJob, JobStatus
from apps.conversions.engines.base import BaseConversionEngine
from apps.conversions.engines.registry import EngineRegistry

User = get_user_model()


# ── Helper ─────────────────────────────────────────────────────────────────────

def make_uploaded_file(
    name="test.pdf",
    content=b"%PDF-1.4 fake content",
    content_type="application/pdf",
    size=None,
):
    """Return a simple in-memory file suitable for multipart upload in tests."""
    f = io.BytesIO(content)
    f.name = name
    f.content_type = content_type
    f.size = size if size is not None else len(content)
    return f


# ── Format tests ───────────────────────────────────────────────────────────────

class FormatDefinitionTest(TestCase):

    def test_supported_pairs_is_not_empty(self):
        self.assertTrue(len(SUPPORTED_PAIRS) > 0)

    def test_every_format_has_a_label(self):
        formats_in_pairs = set()
        for src, tgt in SUPPORTED_PAIRS:
            formats_in_pairs.add(src)
            formats_in_pairs.add(tgt)
        for fmt in formats_in_pairs:
            self.assertIn(fmt, FORMAT_LABELS, f"Format '{fmt}' has no label.")

    def test_every_source_format_has_allowed_extensions(self):
        source_formats = {src for src, _ in SUPPORTED_PAIRS}
        for fmt in source_formats:
            self.assertIn(fmt, ALLOWED_EXTENSIONS, f"Format '{fmt}' has no allowed extensions.")
            self.assertTrue(len(ALLOWED_EXTENSIONS[fmt]) > 0)

    def test_every_source_format_has_allowed_mime_types(self):
        source_formats = {src for src, _ in SUPPORTED_PAIRS}
        for fmt in source_formats:
            self.assertIn(fmt, ALLOWED_MIME_TYPES, f"Format '{fmt}' has no allowed MIME types.")
            self.assertTrue(len(ALLOWED_MIME_TYPES[fmt]) > 0)

    def test_is_valid_conversion_true_for_supported(self):
        for src, tgt in SUPPORTED_PAIRS:
            self.assertTrue(is_valid_conversion(src, tgt))

    def test_is_valid_conversion_false_for_unsupported(self):
        self.assertFalse(is_valid_conversion("pdf", "pdf"))
        self.assertFalse(is_valid_conversion("docx", "xlsx"))
        self.assertFalse(is_valid_conversion("invalid", "pdf"))

    def test_get_supported_formats_response_structure(self):
        result = get_supported_formats_response()
        self.assertEqual(len(result), len(SUPPORTED_PAIRS))
        for item in result:
            self.assertIn("source_format", item)
            self.assertIn("source_label", item)
            self.assertIn("target_format", item)
            self.assertIn("target_label", item)


# ── ConversionJob model tests ──────────────────────────────────────────────────

class ConversionJobModelTest(TestCase):

    def test_create_anonymous_job(self):
        job = ConversionJob.objects.create(
            source_format="pdf",
            target_format="docx",
            original_filename="test.pdf",
            session_key="abc123session",
        )
        self.assertIsNotNone(job.id)
        self.assertIsInstance(job.id, uuid.UUID)
        self.assertIsNone(job.user)
        self.assertEqual(job.status, JobStatus.PENDING)

    def test_default_status_is_pending(self):
        job = ConversionJob.objects.create(
            source_format="pdf",
            target_format="docx",
            original_filename="test.pdf",
            session_key="abc123",
        )
        self.assertEqual(job.status, JobStatus.PENDING)

    def test_is_terminal_pending(self):
        job = ConversionJob(status=JobStatus.PENDING)
        self.assertFalse(job.is_terminal)

    def test_is_terminal_processing(self):
        job = ConversionJob(status=JobStatus.PROCESSING)
        self.assertFalse(job.is_terminal)

    def test_is_terminal_completed(self):
        job = ConversionJob(status=JobStatus.COMPLETED)
        self.assertTrue(job.is_terminal)

    def test_is_terminal_failed(self):
        job = ConversionJob(status=JobStatus.FAILED)
        self.assertTrue(job.is_terminal)

    def test_is_terminal_cancelled(self):
        job = ConversionJob(status=JobStatus.CANCELLED)
        self.assertTrue(job.is_terminal)

    def test_str_representation(self):
        job = ConversionJob(
            id=uuid.uuid4(),
            source_format="pdf",
            target_format="docx",
            status=JobStatus.PENDING,
        )
        self.assertIn("pdf", str(job))
        self.assertIn("docx", str(job))
        self.assertIn("pending", str(job))


# ── Engine registry tests ──────────────────────────────────────────────────────

class EngineRegistryTest(TestCase):

    def _fresh_registry(self):
        return EngineRegistry()

    def test_get_returns_none_for_unregistered_pair(self):
        registry = self._fresh_registry()
        self.assertIsNone(registry.get("pdf", "docx"))

    def test_register_and_get(self):
        registry = self._fresh_registry()

        class FakeEngine(BaseConversionEngine):
            source_format = "pdf"
            target_format = "docx"
            def convert(self, input_path, output_path):
                pass

        registry.register(FakeEngine)
        self.assertIs(registry.get("pdf", "docx"), FakeEngine)

    def test_duplicate_registration_raises(self):
        registry = self._fresh_registry()

        class FakeEngine(BaseConversionEngine):
            source_format = "pdf"
            target_format = "docx"
            def convert(self, input_path, output_path):
                pass

        registry.register(FakeEngine)
        with self.assertRaises(ValueError):
            registry.register(FakeEngine)

    def test_non_engine_registration_raises(self):
        registry = self._fresh_registry()
        with self.assertRaises(TypeError):
            registry.register(object)  # type: ignore


# ── Supported formats endpoint tests ──────────────────────────────────────────

class SupportedFormatsViewTest(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_returns_200(self):
        url = reverse("conversions:supported-formats")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_response_structure(self):
        url = reverse("conversions:supported-formats")
        response = self.client.get(url)
        data = response.json()
        self.assertIn("count", data)
        self.assertIn("formats", data)
        self.assertEqual(data["count"], len(SUPPORTED_PAIRS))

    def test_each_format_item_has_required_fields(self):
        url = reverse("conversions:supported-formats")
        response = self.client.get(url)
        for item in response.json()["formats"]:
            self.assertIn("source_format", item)
            self.assertIn("target_format", item)
            self.assertIn("source_label", item)
            self.assertIn("target_label", item)

    def test_no_auth_required(self):
        url = reverse("conversions:supported-formats")
        response = self.client.get(url)
        self.assertNotEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ── File upload / job creation tests ──────────────────────────────────────────

@override_settings(TEMP_UPLOAD_DIR=__import__('tempfile').mkdtemp(prefix='velto_p1_tests_'))
class ConversionJobCreateTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("conversions:job-list-create")

    def _post_file(self, name="test.pdf", content_type="application/pdf",
                   source="pdf", target="docx", content=b"%PDF-1.4 test"):
        f = io.BytesIO(content)
        f.name = name
        return self.client.post(
            self.url,
            data={"file": f, "source_format": source, "target_format": target},
            format="multipart",
            HTTP_CONTENT_TYPE=content_type,
        )

    def test_valid_upload_returns_2xx(self):
        response = self._post_file()
        # Phase 2: 201 for completed conversion, 202 for failed/pending
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_202_ACCEPTED])

    def test_created_job_has_valid_status(self):
        """
        Phase 2 change: POST /api/conversions/ now runs the conversion engine
        synchronously. The returned status will be 'completed' for a valid PDF
        or 'failed' for an invalid one. 'pending' is only returned if no engine
        is registered (which is not the case after Phase 2).

        The previous assertion (status == 'pending') was correct in Phase 1
        but would now be a lie. Checking for a valid JobStatus value is correct.
        """
        response = self._post_file()
        self.assertIn(response.status_code, [201, 202])
        data = response.json()
        valid_statuses = ["pending", "processing", "completed", "failed", "cancelled"]
        self.assertIn(data["status"], valid_statuses)

    def test_created_job_has_correct_formats(self):
        response = self._post_file()
        data = response.json()
        self.assertEqual(data["source_format"], "pdf")
        self.assertEqual(data["target_format"], "docx")

    def test_created_job_preserves_filename(self):
        response = self._post_file(name="my_document.pdf")
        data = response.json()
        self.assertEqual(data["original_filename"], "my_document.pdf")

    def test_job_id_is_uuid(self):
        response = self._post_file()
        data = response.json()
        # Should not raise
        parsed = uuid.UUID(data["id"])
        self.assertIsNotNone(parsed)

    def test_invalid_format_pair_returns_400(self):
        f = io.BytesIO(b"%PDF-1.4 test")
        f.name = "test.pdf"
        response = self.client.post(
            self.url,
            data={"file": f, "source_format": "pdf", "target_format": "pdf"},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_file_returns_400(self):
        response = self.client.post(
            self.url,
            data={"source_format": "pdf", "target_format": "docx"},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_source_format_returns_400(self):
        f = io.BytesIO(b"%PDF-1.4 test")
        f.name = "test.pdf"
        response = self.client.post(
            self.url,
            data={"file": f, "target_format": "docx"},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unknown_source_format_returns_400(self):
        f = io.BytesIO(b"data")
        f.name = "test.mp4"
        response = self.client.post(
            self.url,
            data={"file": f, "source_format": "mp4", "target_format": "docx"},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_wrong_file_extension_returns_400(self):
        """Declaring source_format=pdf but uploading a .docx file must fail."""
        f = io.BytesIO(b"PK fake docx content")
        f.name = "document.docx"
        response = self.client.post(
            self.url,
            data={"file": f, "source_format": "pdf", "target_format": "docx"},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_session_cookie_is_set_after_upload(self):
        response = self._post_file()
        # Phase 2: 201 for completed, 202 for failed conversion
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_202_ACCEPTED])
        # Django test client stores session in self.client.session
        self.assertIn("velto_session", self.client.cookies)


# ── Session-based ownership tests ─────────────────────────────────────────────

@override_settings(TEMP_UPLOAD_DIR=__import__('tempfile').mkdtemp(prefix='velto_p1_session_'))
class SessionOwnershipTest(TestCase):

    def setUp(self):
        self.client_a = APIClient()
        self.client_b = APIClient()
        self.list_url = reverse("conversions:job-list-create")

    def _upload(self, client):
        f = io.BytesIO(b"%PDF-1.4 test")
        f.name = "test.pdf"
        return client.post(
            self.list_url,
            data={"file": f, "source_format": "pdf", "target_format": "docx"},
            format="multipart",
        )

    def test_client_a_cannot_see_client_b_jobs(self):
        # Client A creates a job
        resp_a = self._upload(self.client_a)
        self.assertIn(resp_a.status_code, [status.HTTP_201_CREATED, status.HTTP_202_ACCEPTED])

        # Client B creates a job
        resp_b = self._upload(self.client_b)
        self.assertIn(resp_b.status_code, [status.HTTP_201_CREATED, status.HTTP_202_ACCEPTED])

        job_a_id = resp_a.json()["id"]
        job_b_id = resp_b.json()["id"]

        # Client A list must only include A's job
        list_resp_a = self.client_a.get(self.list_url)
        ids_a = [j["id"] for j in list_resp_a.json()["results"]]
        self.assertIn(job_a_id, ids_a)
        self.assertNotIn(job_b_id, ids_a)

    def test_client_b_cannot_access_client_a_job_detail(self):
        resp_a = self._upload(self.client_a)
        job_a_id = resp_a.json()["id"]

        detail_url = reverse("conversions:job-detail", kwargs={"job_id": job_a_id})
        response = self.client_b.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_client_can_access_own_job_detail(self):
        resp = self._upload(self.client_a)
        job_id = resp.json()["id"]

        detail_url = reverse("conversions:job-detail", kwargs={"job_id": job_id})
        response = self.client_a.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["id"], job_id)

    def test_anonymous_list_returns_empty_without_session(self):
        """A fresh client with no session must get an empty list."""
        fresh_client = APIClient()
        response = fresh_client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["count"], 0)
