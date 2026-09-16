"""
Comprehensive unit tests for authentication, user profiles, email verification, password reset,
ownership isolation, quota limits, and account deletion in VELTO Conversion.
"""

from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core import mail
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.conversions.models import ConversionJob, JobStatus
from apps.users.models import UserProfile
from apps.users.utils import generate_secure_token, hash_token

User = get_user_model()


def _get_data(response):
    """Extract data payload from DRF response, handling VELTO response envelope."""
    try:
        json_body = response.json()
        if isinstance(json_body, dict) and "data" in json_body and json_body["data"] is not None:
            return json_body["data"]
        return json_body
    except Exception:
        if isinstance(response.data, dict) and "data" in response.data and response.data["data"] is not None:
            return response.data["data"]
        return response.data


class UserAuthenticationTests(APITestCase):
    """Tests for registration, login, token refresh, logout, and me endpoints."""

    def test_registration_success(self):
        url = "/api/v1/auth/register/"
        data = {
            "email": "testuser@example.com",
            "password": "SecurePassword123!",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user_data = _get_data(response)
        self.assertEqual(user_data["email"], "testuser@example.com")
        self.assertFalse(user_data["is_email_verified"])
        self.assertNotIn("password", user_data)

        # Check DB records
        user = User.objects.get(email="testuser@example.com")
        self.assertTrue(hasattr(user, "profile"))
        self.assertFalse(user.profile.is_email_verified)

        # Check verification email sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Verify Your Email Address", mail.outbox[0].subject)

    def test_duplicate_email_rejection(self):
        User.objects.create_user(username="testuser@example.com", email="testuser@example.com", password="SecurePassword123!")
        url = "/api/v1/auth/register/"
        data = {
            "email": "testuser@example.com",
            "password": "AnotherPassword123!",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_email_rejection(self):
        url = "/api/v1/auth/register/"
        data = {
            "email": "not-an-email",
            "password": "SecurePassword123!",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_success_and_tokens(self):
        user = User.objects.create_user(username="login@example.com", email="login@example.com", password="Password123!")
        url = "/api/v1/auth/login/"
        data = {
            "email": "login@example.com",
            "password": "Password123!",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        res_data = _get_data(response)
        tokens = res_data["tokens"]
        self.assertIn("access", tokens)
        self.assertIn("refresh", tokens)
        self.assertEqual(res_data["user"]["email"], "login@example.com")

    def test_login_invalid_credentials(self):
        User.objects.create_user(username="login@example.com", email="login@example.com", password="Password123!")
        url = "/api/v1/auth/login/"
        data = {
            "email": "login@example.com",
            "password": "WrongPassword!",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_refresh_and_rotation(self):
        User.objects.create_user(username="refresh@example.com", email="refresh@example.com", password="Password123!")
        login_res = self.client.post("/api/v1/auth/login/", {"email": "refresh@example.com", "password": "Password123!"}, format="json")
        tokens = _get_data(login_res)["tokens"]
        refresh_token = tokens["refresh"]

        # Refresh
        refresh_url = "/api/v1/auth/token/refresh/"
        ref_res = self.client.post(refresh_url, {"refresh": refresh_token}, format="json")
        self.assertEqual(ref_res.status_code, status.HTTP_200_OK)
        new_tokens = _get_data(ref_res)["tokens"]
        self.assertIn("access", new_tokens)
        self.assertIn("refresh", new_tokens)
        self.assertNotEqual(refresh_token, new_tokens["refresh"])

        # Old refresh token should now be blacklisted
        old_ref_res = self.client.post(refresh_url, {"refresh": refresh_token}, format="json")
        self.assertEqual(old_ref_res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout(self):
        User.objects.create_user(username="logout@example.com", email="logout@example.com", password="Password123!")
        login_res = self.client.post("/api/v1/auth/login/", {"email": "logout@example.com", "password": "Password123!"}, format="json")
        tokens = _get_data(login_res)["tokens"]
        access_token = tokens["access"]
        refresh_token = tokens["refresh"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        logout_res = self.client.post("/api/v1/auth/logout/", {"refresh": refresh_token}, format="json")
        self.assertEqual(logout_res.status_code, status.HTTP_200_OK)

        # Confirm refresh token is blacklisted
        ref_res = self.client.post("/api/v1/auth/token/refresh/", {"refresh": refresh_token}, format="json")
        self.assertEqual(ref_res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_current_user_me(self):
        user = User.objects.create_user(username="me@example.com", email="me@example.com", password="Password123!")
        login_res = self.client.post("/api/v1/auth/login/", {"email": "me@example.com", "password": "Password123!"}, format="json")
        access_token = _get_data(login_res)["tokens"]["access"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        me_res = self.client.get("/api/v1/auth/me/")
        self.assertEqual(me_res.status_code, status.HTTP_200_OK)
        profile_data = _get_data(me_res)
        self.assertEqual(profile_data["email"], "me@example.com")
        self.assertIn("storage_limit_bytes", profile_data)
        self.assertIn("daily_conversion_limit", profile_data)
        self.assertNotIn("password", profile_data)


class UserEmailAndPasswordTests(APITestCase):
    """Tests for email verification and password reset workflows."""

    def test_password_reset_flow(self):
        user = User.objects.create_user(username="reset@example.com", email="reset@example.com", password="OldPassword123!")
        req_url = "/api/v1/auth/password-reset/request/"

        # Non-existent email enumeration protection
        res1 = self.client.post(req_url, {"email": "nonexistent@example.com"}, format="json")
        self.assertEqual(res1.status_code, status.HTTP_200_OK)

        # Real user reset request
        res2 = self.client.post(req_url, {"email": "reset@example.com"}, format="json")
        self.assertEqual(res2.status_code, status.HTTP_200_OK)

        # Email sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Password Reset", mail.outbox[0].subject)

        # Extract token from profile
        profile = user.profile
        profile.refresh_from_db()
        raw_token = "test_raw_reset_token"
        profile.password_reset_token = hash_token(raw_token)
        profile.password_reset_sent_at = timezone.now()
        profile.save()

        # Confirm password reset
        conf_url = "/api/v1/auth/password-reset/confirm/"
        conf_res = self.client.post(
            conf_url,
            {
                "email": "reset@example.com",
                "token": raw_token,
                "new_password": "NewSecurePassword123!",
            },
            format="json",
        )
        self.assertEqual(conf_res.status_code, status.HTTP_200_OK)

        # Verify password changed
        user.refresh_from_db()
        self.assertTrue(user.check_password("NewSecurePassword123!"))

        # Invalidate token after use
        reuse_res = self.client.post(
            conf_url,
            {
                "email": "reset@example.com",
                "token": raw_token,
                "new_password": "AnotherPassword123!",
            },
            format="json",
        )
        self.assertEqual(reuse_res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_email_verification_flow(self):
        user = User.objects.create_user(username="unverified@example.com", email="unverified@example.com", password="Password123!")
        raw_token = generate_secure_token()
        user.profile.email_verification_token = hash_token(raw_token)
        user.profile.email_verification_sent_at = timezone.now()
        user.profile.save()

        conf_url = "/api/v1/auth/email-verification/confirm/"
        res = self.client.post(conf_url, {"email": "unverified@example.com", "token": raw_token}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        user.profile.refresh_from_db()
        self.assertTrue(user.profile.is_email_verified)

        # Token reuse rejection
        reuse_res = self.client.post(conf_url, {"email": "unverified@example.com", "token": raw_token}, format="json")
        self.assertEqual(reuse_res.status_code, status.HTTP_400_BAD_REQUEST)


class ConversionOwnershipTests(APITestCase):
    """Tests for job ownership isolation between User A, User B, and anonymous requests."""

    def setUp(self):
        self.user_a = User.objects.create_user(username="usera@example.com", email="usera@example.com", password="Password123!")
        self.user_b = User.objects.create_user(username="userb@example.com", email="userb@example.com", password="Password123!")

        self.job_a = ConversionJob.objects.create(
            user=self.user_a,
            source_format="pdf",
            target_format="docx",
            original_filename="user_a_doc.pdf",
            status=JobStatus.COMPLETED,
        )

        self.job_b = ConversionJob.objects.create(
            user=self.user_b,
            source_format="png",
            target_format="jpg",
            original_filename="user_b_img.png",
            status=JobStatus.COMPLETED,
        )

        login_a = self.client.post("/api/v1/auth/login/", {"email": "usera@example.com", "password": "Password123!"}, format="json")
        self.token_a = _get_data(login_a)["tokens"]["access"]

        login_b = self.client.post("/api/v1/auth/login/", {"email": "userb@example.com", "password": "Password123!"}, format="json")
        self.token_b = _get_data(login_b)["tokens"]["access"]

    def test_user_a_access_own_job(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        res = self.client.get(f"/api/v1/conversions/{self.job_a.id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_user_b_cannot_access_user_a_job(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_b}")
        res = self.client.get(f"/api/v1/conversions/{self.job_a.id}/")
        self.assertIn(res.status_code, (status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN))

    def test_user_b_cannot_retry_user_a_job(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_b}")
        res = self.client.post(f"/api/v1/conversions/{self.job_a.id}/retry/")
        self.assertIn(res.status_code, (status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN))

    def test_user_b_cannot_cancel_user_a_job(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_b}")
        res = self.client.post(f"/api/v1/conversions/{self.job_a.id}/cancel/")
        self.assertIn(res.status_code, (status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN))

    def test_user_b_cannot_delete_user_a_job(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_b}")
        res = self.client.delete(f"/api/v1/conversions/{self.job_a.id}/")
        # Should return normal message or forbidden, but MUST NOT delete Job A!
        self.assertTrue(ConversionJob.objects.filter(id=self.job_a.id).exists())

    def test_history_filtering_by_owner(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        res = self.client.get("/api/v1/conversions/history/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = _get_data(res)
        results = data["results"] if isinstance(data, dict) and "results" in data else data
        job_ids = [j["id"] for j in results]
        self.assertIn(str(self.job_a.id), job_ids)
        self.assertNotIn(str(self.job_b.id), job_ids)


class UsageLimitsTests(APITestCase):
    """Tests for per-user daily, monthly, and storage quota enforcement."""

    def setUp(self):
        self.user = User.objects.create_user(username="limited@example.com", email="limited@example.com", password="Password123!")
        login_res = self.client.post("/api/v1/auth/login/", {"email": "limited@example.com", "password": "Password123!"}, format="json")
        self.token = _get_data(login_res)["tokens"]["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

    def test_daily_limit_exceeded(self):
        profile = self.user.profile
        profile.daily_conversion_count = profile.daily_conversion_limit
        profile.last_conversion_date = timezone.now().date()
        profile.save()

        profile.refresh_from_db()
        self.assertFalse(profile.check_daily_limit())

    def test_storage_limit_exceeded(self):
        profile = self.user.profile
        profile.storage_used_bytes = profile.storage_limit_bytes + 100
        profile.save()

        profile.refresh_from_db()
        self.assertFalse(profile.check_storage_limit(10))

    def test_atomic_usage_recording(self):
        profile = self.user.profile
        initial_daily = profile.daily_conversion_count
        initial_storage = profile.storage_used_bytes

        profile.record_conversion_job(1024)
        profile.refresh_from_db()

        self.assertEqual(profile.daily_conversion_count, initial_daily + 1)
        self.assertEqual(profile.storage_used_bytes, initial_storage + 1024)

    def test_counter_resets_on_new_day(self):
        profile = self.user.profile
        profile.daily_conversion_count = 45
        profile.last_conversion_date = timezone.now().date() - timedelta(days=2)
        profile.save()

        profile.refresh_from_db()
        self.assertTrue(profile.check_daily_limit())
        self.assertEqual(profile.daily_conversion_count, 0)


class AccountDeletionTests(APITestCase):
    """Tests for user account deletion and workspace cleanup."""

    def test_account_deletion_with_password_confirmation(self):
        user = User.objects.create_user(username="delete_me@example.com", email="delete_me@example.com", password="DeletePassword123!")
        login_res = self.client.post("/api/v1/auth/login/", {"email": "delete_me@example.com", "password": "DeletePassword123!"}, format="json")
        tokens = _get_data(login_res)["tokens"]
        access_token = tokens["access"]
        refresh_token = tokens["refresh"]

        # Create a conversion job owned by user
        job = ConversionJob.objects.create(
            user=user,
            source_format="pdf",
            target_format="txt",
            original_filename="to_be_deleted.pdf",
        )

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

        # Missing password confirmation
        del_fail = self.client.delete("/api/v1/auth/me/", format="json")
        self.assertEqual(del_fail.status_code, status.HTTP_400_BAD_REQUEST)

        # Correct password confirmation
        del_success = self.client.delete("/api/v1/auth/me/?password=DeletePassword123!")
        self.assertEqual(del_success.status_code, status.HTTP_200_OK)

        # User and jobs deleted
        self.assertFalse(User.objects.filter(email="delete_me@example.com").exists())
        self.assertFalse(ConversionJob.objects.filter(id=job.id).exists())

        # Refresh token blacklisted
        ref_res = self.client.post("/api/v1/auth/token/refresh/", {"refresh": refresh_token}, format="json")
        self.assertEqual(ref_res.status_code, status.HTTP_401_UNAUTHORIZED)
