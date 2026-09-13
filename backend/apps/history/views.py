"""
History views — returns a session- or user-scoped list of terminal jobs.

GET /api/history/

Returns all jobs in a terminal state (completed, failed, cancelled) for the
current session or authenticated user. Anonymous users see only their own
session's history.

Ordering: most recent first.
"""

import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.conversions.models import ConversionJob, JobStatus
from apps.conversions.serializers import ConversionJobSerializer

logger = logging.getLogger(__name__)

TERMINAL_STATUSES = [
    JobStatus.COMPLETED,
    JobStatus.FAILED,
    JobStatus.CANCELLED,
]


class HistoryListView(APIView):
    """
    GET /api/history/

    Returns terminal conversion jobs for the current session or user.
    Supports optional query-param filtering:
      ?status=completed|failed|cancelled
      ?source_format=pdf|docx|...
      ?target_format=pdf|docx|...
    """

    def get(self, request):
        # Base queryset — owned by this session or user
        if request.user and request.user.is_authenticated:
            jobs = ConversionJob.objects.filter(user=request.user)
        else:
            session_key = request.session.session_key
            if not session_key:
                return Response({"count": 0, "results": []})
            jobs = ConversionJob.objects.filter(
                session_key=session_key, user__isnull=True
            )

        # Only terminal states
        jobs = jobs.filter(status__in=TERMINAL_STATUSES)

        # Optional filters
        status_filter = request.query_params.get("status")
        if status_filter and status_filter in [s.value for s in JobStatus]:
            jobs = jobs.filter(status=status_filter)

        source_filter = request.query_params.get("source_format")
        if source_filter:
            jobs = jobs.filter(source_format=source_filter)

        target_filter = request.query_params.get("target_format")
        if target_filter:
            jobs = jobs.filter(target_format=target_filter)

        serializer = ConversionJobSerializer(jobs, many=True)
        return Response(
            {
                "count": jobs.count(),
                "results": serializer.data,
            }
        )
