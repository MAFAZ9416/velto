"""
Centralized ownership and authorization helper for conversion jobs.

Ensures every job, upload, history entry, and download request is strictly authorized
based on server-side request context (authenticated user or session key).
Client-supplied owner parameters are NEVER trusted.
"""

from typing import Tuple
from django.db.models import QuerySet

from apps.conversions.models import ConversionJob
from apps.conversions.security.exceptions import OwnershipDenied


def get_request_owner_identity(request) -> Tuple[object | None, str]:
    """
    Extract the server-validated owner identity from request context.

    Returns
    -------
    Tuple[user, session_key]
        (authenticated_user_or_None, django_session_key_str)
    """
    user = request.user if getattr(request, "user", None) and request.user.is_authenticated else None
    session_key = ""
    if hasattr(request, "session"):
        if not request.session.session_key:
            request.session.create()
        session_key = request.session.session_key or ""
    return user, session_key


def check_job_ownership(request, job: ConversionJob) -> None:
    """
    Validate that the current request is authorized to access `job`.

    Raises
    ------
    OwnershipDenied
        If the request user/session does not match job ownership.
    """
    user, session_key = get_request_owner_identity(request)

    if user is not None:
        if job.user_id == user.id:
            return
        raise OwnershipDenied("You are not authorized to access this conversion job.")

    if session_key and job.session_key == session_key and job.user_id is None:
        return

    raise OwnershipDenied("You are not authorized to access this conversion job.")


def filter_jobs_for_request(request) -> QuerySet:
    """
    Return a ConversionJob QuerySet containing only jobs owned by the current request context.
    """
    user, session_key = get_request_owner_identity(request)

    if user is not None:
        return ConversionJob.objects.filter(user=user)

    if session_key:
        return ConversionJob.objects.filter(session_key=session_key, user__isnull=True)

    return ConversionJob.objects.none()
