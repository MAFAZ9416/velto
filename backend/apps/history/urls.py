"""
URL patterns for the history app.
"""

from django.urls import path
from apps.history.views import HistoryListView

app_name = "history"

urlpatterns = [
    # GET /api/history/
    path("", HistoryListView.as_view(), name="history-list"),
]
