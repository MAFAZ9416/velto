"""
Tests for the core app — health endpoint and project configuration.
"""

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status


class ProjectConfigTest(TestCase):
    """Verify that Django is configured correctly."""

    def test_settings_are_loaded(self):
        from django.conf import settings
        self.assertTrue(hasattr(settings, "INSTALLED_APPS"))

    def test_required_apps_installed(self):
        from django.conf import settings
        required = [
            "rest_framework",
            "corsheaders",
            "apps.core",
            "apps.users",
            "apps.conversions",
            "apps.history",
        ]
        for app in required:
            self.assertIn(app, settings.INSTALLED_APPS, f"Missing app: {app}")

    def test_session_engine_configured(self):
        from django.conf import settings
        self.assertEqual(
            settings.SESSION_ENGINE,
            "django.contrib.sessions.backends.db",
        )

    def test_drf_multipart_parser_configured(self):
        from django.conf import settings
        parsers = settings.REST_FRAMEWORK.get("DEFAULT_PARSER_CLASSES", [])
        self.assertIn("rest_framework.parsers.MultiPartParser", parsers)


class HealthCheckTest(TestCase):
    """Health endpoint returns 200 with expected fields."""

    def setUp(self):
        self.client = APIClient()

    def test_health_returns_200(self):
        url = reverse("core:health")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_health_response_structure(self):
        url = reverse("core:health")
        response = self.client.get(url)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("service", data)
        self.assertIn("django_version", data)
        self.assertIn("environment", data)

    def test_health_requires_no_auth(self):
        """Health endpoint must work without any credentials."""
        url = reverse("core:health")
        response = self.client.get(url)
        self.assertNotEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)
