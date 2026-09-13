"""
Tests for the history app.

Coverage:
  - Empty history returns empty list
  - Only terminal jobs appear in history
  - Pending/processing jobs do not appear in history
  - Session isolation: client A cannot see client B's history
  - Status filter query param
"""

import io
import tempfile

from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.conversions.models import ConversionJob, JobStatus

HISTORY_TEST_TEMP = tempfile.mkdtemp(prefix="velto_history_tests_")


def _force_session(client: APIClient) -> str:
    """
    Force the APIClient to establish a Django session and return the session key.

    We do this by hitting the health endpoint — Django creates a session
    lazily on first access, but only persists it if something writes to it.
    The easier approach for tests: call client.session.create() directly and
    then set the cookie on the client so subsequent requests carry the key.
    """
    session = client.session
    session.create()
    # APIClient reads the session from the DB via the cookie; set it now
    client.cookies["velto_session"] = session.session_key
    return session.session_key


def _make_job(session_key: str, job_status=JobStatus.COMPLETED,
              source="pdf", target="docx") -> ConversionJob:
    return ConversionJob.objects.create(
        source_format=source,
        target_format=target,
        original_filename="test.pdf",
        session_key=session_key,
        status=job_status,
    )


@override_settings(TEMP_UPLOAD_DIR=HISTORY_TEST_TEMP)
class HistoryListViewTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("history:history-list")

    def test_empty_history_returns_200_with_empty_list(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["count"], 0)
        self.assertEqual(data["results"], [])

    def test_completed_job_appears_in_history(self):
        """A COMPLETED job must show up in history."""
        client = APIClient()
        session_key = _force_session(client)
        _make_job(session_key, JobStatus.COMPLETED)

        response = client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)

    def test_failed_job_appears_in_history(self):
        """A FAILED job must show up in history (it is a terminal state)."""
        client = APIClient()
        session_key = _force_session(client)
        _make_job(session_key, JobStatus.FAILED)

        response = client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)

    def test_pending_job_does_not_appear_in_history(self):
        """
        Pending jobs must NOT show up in history.

        Phase 2 note: uploading via the API runs the engine synchronously, so
        a fake PDF upload becomes a FAILED (terminal) job. This test creates a
        PENDING job directly in the DB to test non-terminal exclusion.
        """
        client = APIClient()
        session_key = _force_session(client)
        _make_job(session_key, JobStatus.PENDING)

        response = client.get(self.url)
        self.assertEqual(response.json()["count"], 0)

    def test_processing_job_does_not_appear_in_history(self):
        """PROCESSING jobs must not appear in history."""
        client = APIClient()
        session_key = _force_session(client)
        _make_job(session_key, JobStatus.PROCESSING)

        response = client.get(self.url)
        self.assertEqual(response.json()["count"], 0)

    def test_history_isolation_between_sessions(self):
        """Client A history must not bleed into client B history."""
        client_a = APIClient()
        client_b = APIClient()

        key_a = _force_session(client_a)
        key_b = _force_session(client_b)

        job_a = _make_job(key_a, JobStatus.COMPLETED)
        job_b = _make_job(key_b, JobStatus.FAILED)

        resp_a = client_a.get(self.url)
        resp_b = client_b.get(self.url)

        ids_a = [j["id"] for j in resp_a.json()["results"]]
        ids_b = [j["id"] for j in resp_b.json()["results"]]

        self.assertIn(str(job_a.id), ids_a)
        self.assertNotIn(str(job_b.id), ids_a)
        self.assertIn(str(job_b.id), ids_b)
        self.assertNotIn(str(job_a.id), ids_b)
        self.assertFalse(set(ids_a) & set(ids_b))

    def test_status_filter_completed(self):
        """?status=completed must return only completed jobs."""
        client = APIClient()
        session_key = _force_session(client)

        _make_job(session_key, JobStatus.COMPLETED)
        _make_job(session_key, JobStatus.FAILED)

        resp = client.get(self.url + "?status=completed")
        self.assertEqual(resp.json()["count"], 1)
        self.assertEqual(resp.json()["results"][0]["status"], "completed")

    def test_status_filter_failed(self):
        """?status=failed must return only failed jobs."""
        client = APIClient()
        session_key = _force_session(client)

        _make_job(session_key, JobStatus.COMPLETED)
        _make_job(session_key, JobStatus.FAILED)

        resp = client.get(self.url + "?status=failed")
        self.assertEqual(resp.json()["count"], 1)
        self.assertEqual(resp.json()["results"][0]["status"], "failed")
