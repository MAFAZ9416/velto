"""
Token generation, verification, and email utilities for VELTO Conversion authentication.
"""

import hashlib
import logging
import secrets
from datetime import timedelta
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

logger = logging.getLogger(__name__)

PASSWORD_RESET_EXPIRY_MINUTES = 60
EMAIL_VERIFICATION_EXPIRY_HOURS = 24


def generate_secure_token() -> str:
    """Generate a crypto-secure URL-safe token string."""
    return secrets.token_urlsafe(32)


def hash_token(raw_token: str) -> str:
    """Hash raw token string using SHA-256 for secure storage."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def send_password_reset_email(user, raw_token: str) -> None:
    """Send password reset email via Django mail backend."""
    subject = "VELTO Conversion — Password Reset Request"
    message = (
        f"Hello,\n\n"
        f"A password reset was requested for your VELTO Conversion account ({user.email}).\n"
        f"Reset Token: {raw_token}\n\n"
        f"This token will expire in {PASSWORD_RESET_EXPIRY_MINUTES} minutes.\n"
        f"If you did not request this, please ignore this message.\n"
    )
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@velto.app")
    try:
        send_mail(subject, message, from_email, [user.email], fail_silently=False)
    except Exception as exc:
        logger.warning("Could not send password reset email to %s: %s", user.email, exc)


def send_verification_email(user, raw_token: str) -> None:
    """Send email verification email via Django mail backend."""
    subject = "VELTO Conversion — Verify Your Email Address"
    message = (
        f"Hello,\n\n"
        f"Thank you for registering with VELTO Conversion.\n"
        f"Verification Token: {raw_token}\n\n"
        f"Please confirm your email address within {EMAIL_VERIFICATION_EXPIRY_HOURS} hours.\n"
    )
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@velto.app")
    try:
        send_mail(subject, message, from_email, [user.email], fail_silently=False)
    except Exception as exc:
        logger.warning("Could not send verification email to %s: %s", user.email, exc)


def is_token_expired(sent_at, max_minutes: int) -> bool:
    """Check if token sent_at timestamp is older than max_minutes."""
    if not sent_at:
        return True
    return timezone.now() > (sent_at + timedelta(minutes=max_minutes))
