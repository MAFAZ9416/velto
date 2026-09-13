"""
Storage quota enforcement and usage accounting.
"""

import logging
from typing import Tuple

from django.conf import settings
from django.db import models
from django.db.models import Sum, Q

from apps.conversions.models import ConversionJob, JobStatus
from apps.conversions.security.exceptions import AbuseLimitExceeded
from apps.conversions.security.ownership import get_request_owner_identity

logger = logging.getLogger(__name__)


def get_owner_storage_usage(user=None, session_key: str = "") -> int:
    """
    Calculate the total storage usage in bytes for a given owner.

    Accounts for:
      - Pending upload reservations (`file_size_bytes`)
      - Active job inputs (`file_size_bytes`)
      - Completed job outputs (`output_size_bytes`)
    """
    if user is not None:
        qs = ConversionJob.objects.filter(user=user)
    elif session_key:
        qs = ConversionJob.objects.filter(session_key=session_key, user__isnull=True)
    else:
        return 0

    # Exclude expired or cancelled jobs whose files were deleted
    active_qs = qs.exclude(status__in=[JobStatus.CANCELLED, JobStatus.EXPIRED])

    # Sum input file sizes
    input_sum = active_qs.filter(
        status__in=[JobStatus.PENDING, JobStatus.QUEUED, JobStatus.STARTED, JobStatus.PROCESSING, JobStatus.RETRYING]
    ).aggregate(total=Sum("file_size_bytes"))["total"] or 0

    # Sum output file sizes
    output_sum = active_qs.filter(
        status=JobStatus.COMPLETED
    ).aggregate(total=Sum("output_size_bytes"))["total"] or 0

    return input_sum + output_sum


def check_storage_quota(request, incoming_bytes: int = 0) -> int:
    """
    Validate that the incoming upload/conversion request will not exceed owner storage quota.

    Raises
    ------
    AbuseLimitExceeded
        If adding `incoming_bytes` exceeds `settings.STORAGE_QUOTA_BYTES`.
    """
    quota_limit = getattr(settings, "STORAGE_QUOTA_BYTES", 524_288_000)
    user, session_key = get_request_owner_identity(request)

    current_usage = get_owner_storage_usage(user=user, session_key=session_key)
    projected_usage = current_usage + incoming_bytes

    if projected_usage > quota_limit:
        quota_mb = quota_limit // (1024 * 1024)
        current_mb = current_usage // (1024 * 1024)
        inc_mb = incoming_bytes // (1024 * 1024)
        logger.warning(
            "Storage quota exceeded for owner (user=%s, session=%s): current=%dMB, incoming=%dMB, limit=%dMB",
            user, session_key, current_mb, inc_mb, quota_mb
        )
        raise AbuseLimitExceeded(
            f"Storage quota of {quota_mb} MB exceeded. "
            f"Current usage is {current_mb} MB. Adding {inc_mb} MB would exceed your limit."
        )

    return current_usage
