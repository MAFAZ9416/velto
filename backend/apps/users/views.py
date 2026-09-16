"""
Authentication and User Account Views for VELTO Conversion.
"""

import logging
from django.contrib.auth import authenticate, get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from drf_spectacular.utils import extend_schema

from apps.users.models import UserProfile
from apps.users.serializers import (
    AccountDeleteSerializer,
    EmailVerificationConfirmSerializer,
    EmailVerificationRequestSerializer,
    LoginRequestSerializer,
    LoginResponseSerializer,
    LogoutRequestSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    TokenRefreshRequestSerializer,
    TokenRefreshResponseSerializer,
    UserProfileDetailSerializer,
    UserRegisterSerializer,
    UserSummarySerializer,
)
from apps.users.utils import (
    EMAIL_VERIFICATION_EXPIRY_HOURS,
    PASSWORD_RESET_EXPIRY_MINUTES,
    generate_secure_token,
    hash_token,
    is_token_expired,
    send_password_reset_email,
    send_verification_email,
)
from apps.conversions.models import ConversionJob, JobStatus
from apps.conversions.services import ConversionService
from apps.core.exceptions import _derive_error_code

User = get_user_model()
logger = logging.getLogger(__name__)


class RegisterView(APIView):
    """
    POST /api/v1/auth/register/
    Registers a new user account, initializes user profile, and dispatches verification email.
    """
    authentication_classes = []
    permission_classes = []

    @extend_schema(
        summary="User Registration",
        description="Creates a new user account with normalized email, password strength validation, and initial usage limits.",
        request=UserRegisterSerializer,
        responses={201: UserSummarySerializer},
        tags=["Authentication"],
        operation_id="v1_auth_register",
    )
    def post(self, request):
        serializer = UserRegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.save()
        profile, _ = UserProfile.objects.get_or_create(user=user)

        # Generate email verification token
        raw_token = generate_secure_token()
        profile.email_verification_token = hash_token(raw_token)
        profile.email_verification_sent_at = timezone.now()
        profile.save(update_fields=["email_verification_token", "email_verification_sent_at"])

        send_verification_email(user, raw_token)

        summary = UserSummarySerializer(user).data
        return Response(summary, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """
    POST /api/v1/auth/login/
    Authenticates email and password, returning JWT access and refresh tokens.
    """
    authentication_classes = []
    permission_classes = []

    @extend_schema(
        summary="User Login",
        description="Authenticates credentials and returns JWT access and refresh tokens.",
        request=LoginRequestSerializer,
        responses={200: LoginResponseSerializer},
        tags=["Authentication"],
        operation_id="v1_auth_login",
    )
    def post(self, request):
        serializer = LoginRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data["email"].strip().lower()
        password = serializer.validated_data["password"]

        user = authenticate(request, username=email, password=password)
        if not user or not user.is_active:
            return Response(
                {"detail": "Invalid email address or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Ensure user profile exists
        UserProfile.objects.get_or_create(user=user)

        refresh = RefreshToken.for_user(user)
        summary = UserSummarySerializer(user).data

        return Response(
            {
                "tokens": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                },
                "user": summary,
            },
            status=status.HTTP_200_OK,
        )


class TokenRefreshView(APIView):
    """
    POST /api/v1/auth/token/refresh/
    Refreshes JWT access token using a valid refresh token.
    """
    authentication_classes = []
    permission_classes = []

    @extend_schema(
        summary="Refresh JWT Token",
        description="Exchanges a valid refresh token for a new access token.",
        request=TokenRefreshRequestSerializer,
        responses={200: TokenRefreshResponseSerializer},
        tags=["Authentication"],
        operation_id="v1_auth_token_refresh",
    )
    def post(self, request):
        serializer = TokenRefreshRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            refresh_token_str = serializer.validated_data["refresh"]
            refresh = RefreshToken(refresh_token_str)
            user_id = refresh.payload.get("user_id")
            user = User.objects.get(pk=user_id)

            try:
                refresh.blacklist()
            except Exception:
                pass

            new_refresh = RefreshToken.for_user(user)
            return Response(
                {
                    "tokens": {
                        "access": str(new_refresh.access_token),
                        "refresh": str(new_refresh),
                    }
                },
                status=status.HTTP_200_OK,
            )
        except Exception:
            return Response(
                {"detail": "Invalid or expired refresh token."},
                status=status.HTTP_401_UNAUTHORIZED,
            )


class LogoutView(APIView):
    """
    POST /api/v1/auth/logout/
    Blacklists the active refresh token.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="User Logout",
        description="Blacklists active refresh token to end user session.",
        request=LogoutRequestSerializer,
        responses={200: dict},
        tags=["Authentication"],
        operation_id="v1_auth_logout",
    )
    def post(self, request):
        serializer = LogoutRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            token = RefreshToken(serializer.validated_data["refresh"])
            token.blacklist()
            return Response({"message": "Successfully logged out."}, status=status.HTTP_200_OK)
        except TokenError:
            return Response({"message": "Token is invalid or already logged out."}, status=status.HTTP_200_OK)


class CurrentUserView(APIView):
    """
    GET /api/v1/auth/me/ — Get active user profile, storage, and conversion usage details.
    DELETE /api/v1/auth/me/ — Delete user account, cancel jobs, and clean up files.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get Current User Profile & Usage",
        description="Returns detailed user account status, storage capacity, and conversion limits.",
        responses={200: UserProfileDetailSerializer},
        tags=["Account"],
        operation_id="v1_auth_me_detail",
    )
    def get(self, request):
        user = request.user
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.reset_usage_if_needed()

        data = {
            "user_id": str(user.id),
            "email": user.email,
            "is_email_verified": profile.is_email_verified,
            "account_status": "active" if user.is_active else "inactive",
            "storage_limit_bytes": profile.storage_limit_bytes,
            "storage_used_bytes": profile.storage_used_bytes,
            "daily_conversion_count": profile.daily_conversion_count,
            "daily_conversion_limit": profile.daily_conversion_limit,
            "monthly_conversion_count": profile.monthly_conversion_count,
            "monthly_conversion_limit": profile.monthly_conversion_limit,
            "created_at": user.date_joined,
        }
        return Response(data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Delete Account",
        description="Deletes account, revokes tokens, cancels pending jobs, and purges user files.",
        request=AccountDeleteSerializer,
        responses={200: dict},
        tags=["Account"],
        operation_id="v1_auth_me_delete",
    )
    def delete(self, request):
        data = request.data if request.data else request.query_params
        serializer = AccountDeleteSerializer(data=data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        password = serializer.validated_data["password"]

        if not user.check_password(password):
            raise PermissionDenied("Invalid password confirmation for account deletion.")

        # 1. Cancel active jobs and clean up files
        user_jobs = ConversionJob.objects.filter(user=user)
        for job in user_jobs:
            try:
                if job.status in (JobStatus.PENDING, JobStatus.QUEUED, JobStatus.STARTED, JobStatus.PROCESSING):
                    job.status = JobStatus.CANCELLED
                    job.save(update_fields=["status"])
                ConversionService.cleanup_job_files(job)
            except Exception as exc:
                logger.warning("Error cleaning up job %s during account deletion: %s", job.id, exc)

        user_jobs.delete()

        # 2. Delete user record (cascades to profile)
        user.delete()
        return Response(
            {"message": "Account and associated data deleted successfully."},
            status=status.HTTP_200_OK,
        )


class PasswordResetRequestView(APIView):
    """
    POST /api/v1/auth/password-reset/request/
    Initiates password reset flow. Always returns generic success payload.
    """
    authentication_classes = []
    permission_classes = []

    @extend_schema(
        summary="Request Password Reset",
        description="Dispatches password reset token email if account exists (prevents account enumeration).",
        request=PasswordResetRequestSerializer,
        responses={200: dict},
        tags=["Authentication"],
        operation_id="v1_auth_password_reset_request",
    )
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data["email"].strip().lower()
        user = User.objects.filter(email__iexact=email).first()

        if user:
            profile, _ = UserProfile.objects.get_or_create(user=user)
            raw_token = generate_secure_token()
            profile.password_reset_token = hash_token(raw_token)
            profile.password_reset_sent_at = timezone.now()
            profile.save(update_fields=["password_reset_token", "password_reset_sent_at"])
            send_password_reset_email(user, raw_token)

        return Response(
            {"message": "If an account exists for this email address, a password reset email has been sent."},
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    """
    POST /api/v1/auth/password-reset/confirm/
    Confirms password reset using single-use token and sets new password.
    """
    authentication_classes = []
    permission_classes = []

    @extend_schema(
        summary="Confirm Password Reset",
        description="Validates reset token and sets new user password.",
        request=PasswordResetConfirmSerializer,
        responses={200: dict},
        tags=["Authentication"],
        operation_id="v1_auth_password_reset_confirm",
    )
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data["email"].strip().lower()
        raw_token = serializer.validated_data["token"]
        new_password = serializer.validated_data["new_password"]

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            raise ValidationError("Invalid or expired password reset token.")

        profile = getattr(user, "profile", None)
        if not profile or not profile.password_reset_token:
            raise ValidationError("Invalid or expired password reset token.")

        if profile.password_reset_token != hash_token(raw_token):
            raise ValidationError("Invalid or expired password reset token.")

        if is_token_expired(profile.password_reset_sent_at, PASSWORD_RESET_EXPIRY_MINUTES):
            raise ValidationError("Password reset token has expired. Please request a new one.")

        # Update password and invalidate token
        user.set_password(new_password)
        user.save()

        profile.password_reset_token = None
        profile.password_reset_sent_at = None
        profile.save(update_fields=["password_reset_token", "password_reset_sent_at"])

        return Response(
            {"message": "Password reset successfully. You may now log in with your new password."},
            status=status.HTTP_200_OK,
        )


class EmailVerificationRequestView(APIView):
    """
    POST /api/v1/auth/email-verification/request/
    Re-sends email verification token to user.
    """
    @extend_schema(
        summary="Request Email Verification",
        description="Generates and dispatches a new email verification token.",
        request=EmailVerificationRequestSerializer,
        responses={200: dict},
        tags=["Authentication"],
        operation_id="v1_auth_email_verification_request",
    )
    def post(self, request):
        if request.user and request.user.is_authenticated:
            user = request.user
        else:
            email = request.data.get("email", "").strip().lower()
            user = User.objects.filter(email__iexact=email).first()

        if user:
            profile, _ = UserProfile.objects.get_or_create(user=user)
            if not profile.is_email_verified:
                raw_token = generate_secure_token()
                profile.email_verification_token = hash_token(raw_token)
                profile.email_verification_sent_at = timezone.now()
                profile.save(update_fields=["email_verification_token", "email_verification_sent_at"])
                send_verification_email(user, raw_token)

        return Response(
            {"message": "If an unverified account exists, a verification email has been sent."},
            status=status.HTTP_200_OK,
        )


class EmailVerificationConfirmView(APIView):
    """
    POST /api/v1/auth/email-verification/confirm/
    Confirms email verification token and marks profile verified.
    """
    authentication_classes = []
    permission_classes = []

    @extend_schema(
        summary="Confirm Email Verification",
        description="Validates email verification token and marks account as verified.",
        request=EmailVerificationConfirmSerializer,
        responses={200: dict},
        tags=["Authentication"],
        operation_id="v1_auth_email_verification_confirm",
    )
    def post(self, request):
        serializer = EmailVerificationConfirmSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data["email"].strip().lower()
        raw_token = serializer.validated_data["token"]

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            raise ValidationError("Invalid or expired verification token.")

        profile = getattr(user, "profile", None)
        if not profile or not profile.email_verification_token:
            raise ValidationError("Invalid or expired verification token.")

        if profile.email_verification_token != hash_token(raw_token):
            raise ValidationError("Invalid or expired verification token.")

        if is_token_expired(profile.email_verification_sent_at, EMAIL_VERIFICATION_EXPIRY_HOURS * 60):
            raise ValidationError("Email verification token has expired. Please request a new one.")

        profile.is_email_verified = True
        profile.email_verification_token = None
        profile.email_verification_sent_at = None
        profile.save(update_fields=["is_email_verified", "email_verification_token", "email_verification_sent_at"])

        return Response(
            {"message": "Email address verified successfully."},
            status=status.HTTP_200_OK,
        )
