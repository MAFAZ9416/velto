"""
URL patterns for the users app — Authentication & User Account Management.
"""

from django.urls import path
from apps.users.views import (
    CurrentUserView,
    EmailVerificationConfirmView,
    EmailVerificationRequestView,
    LoginView,
    LogoutView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RegisterView,
    TokenRefreshView,
)

app_name = "users"

urlpatterns = [
    # Auth lifecycle
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", CurrentUserView.as_view(), name="me"),

    # Password reset
    path("password-reset/request/", PasswordResetRequestView.as_view(), name="password-reset-request"),
    path("password-reset/confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),

    # Email verification
    path("email-verification/request/", EmailVerificationRequestView.as_view(), name="email-verification-request"),
    path("email-verification/confirm/", EmailVerificationConfirmView.as_view(), name="email-verification-confirm"),
]
