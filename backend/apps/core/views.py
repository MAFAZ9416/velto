"""
Core views — shared infrastructure endpoints.
"""

import django
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


class HealthCheckView(APIView):
    """
    GET /api/health/

    Returns 200 with basic runtime information.
    No authentication required — used by load balancers, monitoring, and CI.
    """

    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response(
            {
                "status": "ok",
                "service": "velto-conversion-backend",
                "django_version": django.get_version(),
                "environment": "development" if __import__("django").conf.settings.DEBUG else "production",
            },
            status=status.HTTP_200_OK,
        )
