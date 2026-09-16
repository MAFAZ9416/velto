"""
Core URL Patterns.
"""

from django.urls import path
from apps.core.views import HealthCheckView, ReadinessCheckView

app_name = "core"

urlpatterns = [
    path("health/", HealthCheckView.as_view(), name="health"),
    path("ready/", ReadinessCheckView.as_view(), name="readiness"),
]
