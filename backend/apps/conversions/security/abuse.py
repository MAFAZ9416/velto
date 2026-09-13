"""
Resource abuse controls and concurrency protection.

Prevents single session or user from overwhelming backend resources with concurrent jobs,
excessive queued requests, or unbounded conversion processing durations.
"""

import logging
import time
from django.utils import timezone

from apps.conversions.models import ConversionJob, JobStatus
from apps.conversions.security.exceptions import AbuseLimitExceeded, ProcessingTimeout
from apps.conversions.security.limits import (
    MAX_CONCURRENT_JOBS_PER_OWNER,
    MAX_JOB_PROCESSING_TIMEOUT,
)
from apps.conversions.security.ownership import get_request_owner_identity

logger = logging.getLogger(__name__)


def check_concurrent_jobs(request) -> None:
    """
    Check if the current request user/session has reached the maximum allowed concurrent active jobs.

    Raises
    ------
    AbuseLimitExceeded
        If active job count >= MAX_CONCURRENT_JOBS_PER_OWNER.
    """
    user, session_key = get_request_owner_identity(request)

    active_statuses = [JobStatus.PENDING, JobStatus.PROCESSING]

    if user is not None:
        active_count = ConversionJob.objects.filter(
            user=user, status__in=active_statuses
        ).count()
    elif session_key:
        active_count = ConversionJob.objects.filter(
            session_key=session_key, user__isnull=True, status__in=active_statuses
        ).count()
    else:
        active_count = 0

    if active_count >= MAX_CONCURRENT_JOBS_PER_OWNER:
        logger.warning(
            "Concurrent job limit exceeded (%d active) for owner (user=%s, session=%s)",
            active_count,
            user,
            session_key,
        )
        raise AbuseLimitExceeded(
            f"Maximum concurrent job limit ({MAX_CONCURRENT_JOBS_PER_OWNER}) reached. "
            "Please wait for your active conversions to complete before starting a new request."
        )


def check_job_timeout(start_timestamp: float) -> None:
    """
    Check if processing duration has exceeded MAX_JOB_PROCESSING_TIMEOUT.

    Raises
    ------
    ProcessingTimeout
        If elapsed time > MAX_JOB_PROCESSING_TIMEOUT.
    """
    elapsed = time.time() - start_timestamp
    if elapsed > MAX_JOB_PROCESSING_TIMEOUT:
        raise ProcessingTimeout(
            f"Conversion processing timed out after {int(elapsed)} seconds (limit: {MAX_JOB_PROCESSING_TIMEOUT}s)."
        )
