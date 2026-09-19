"""
Prometheus Metrics Engine for VELTO Conversion.

Defines production metrics with strictly low-cardinality labels.
Exposes metric increment and duration recording helpers.
"""

import logging
import time
from prometheus_client import Counter, Gauge, Histogram, REGISTRY, generate_latest, CONTENT_TYPE_LATEST

logger = logging.getLogger(__name__)

# ── Counters ──────────────────────────────────────────────────────────────────
CONVERSIONS_TOTAL = Counter(
    "velto_conversions_total",
    "Total conversion jobs processed",
    ["source_format", "target_format", "status", "error_category"],
)

CONVERSIONS_SUCCEEDED_TOTAL = Counter(
    "velto_conversions_succeeded_total",
    "Total successful conversion jobs",
    ["source_format", "target_format"],
)

CONVERSIONS_FAILED_TOTAL = Counter(
    "velto_conversions_failed_total",
    "Total failed conversion jobs",
    ["source_format", "target_format", "error_category"],
)

CONVERSIONS_CANCELLED_TOTAL = Counter(
    "velto_conversions_cancelled_total",
    "Total cancelled conversion jobs",
    ["source_format", "target_format"],
)

CONVERSIONS_RETRIED_TOTAL = Counter(
    "velto_conversions_retried_total",
    "Total conversion job retries",
    ["source_format", "target_format"],
)

AUTHENTICATION_ATTEMPTS_TOTAL = Counter(
    "velto_authentication_attempts_total",
    "Total authentication attempts",
    ["status"],
)

AUTHENTICATION_FAILURES_TOTAL = Counter(
    "velto_authentication_failures_total",
    "Total authentication failures",
    ["reason"],
)

STORAGE_OPERATIONS_TOTAL = Counter(
    "velto_storage_operations_total",
    "Total storage operations executed",
    ["operation", "backend"],
)

STORAGE_FAILURES_TOTAL = Counter(
    "velto_storage_failures_total",
    "Total storage operation failures",
    ["operation", "backend"],
)


# ── Histograms ────────────────────────────────────────────────────────────────
CONVERSION_DURATION_SECONDS = Histogram(
    "velto_conversion_duration_seconds",
    "Duration of file conversions in seconds",
    ["source_format", "target_format", "status"],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0),
)

CONVERSION_QUEUE_WAIT_SECONDS = Histogram(
    "velto_conversion_queue_wait_seconds",
    "Time spent in queue before worker processing in seconds",
    ["source_format", "target_format"],
    buckets=(0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
)

API_REQUEST_DURATION_SECONDS = Histogram(
    "velto_api_request_duration_seconds",
    "Duration of HTTP API requests in seconds",
    ["method", "route", "status_code"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

STORAGE_OPERATION_DURATION_SECONDS = Histogram(
    "velto_storage_operation_duration_seconds",
    "Duration of storage read/write/delete operations in seconds",
    ["operation", "backend"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)


# ── Gauges ────────────────────────────────────────────────────────────────────
ACTIVE_CONVERSION_JOBS = Gauge(
    "velto_active_conversion_jobs",
    "Current number of active processing conversion jobs",
)

QUEUED_CONVERSION_JOBS = Gauge(
    "velto_queued_conversion_jobs",
    "Current number of queued conversion jobs",
)

STORAGE_BYTES_USED = Gauge(
    "velto_storage_bytes_used",
    "Current total storage bytes used across active profiles",
)

REGISTERED_USERS = Gauge(
    "velto_registered_users",
    "Total registered user accounts",
)


# ── Celery Metrics ───────────────────────────────────────────────────────────
CELERY_TASKS_STARTED_TOTAL = Counter(
    "velto_celery_tasks_started_total",
    "Total Celery tasks started",
    ["queue_name"],
)

CELERY_TASKS_COMPLETED_TOTAL = Counter(
    "velto_celery_tasks_completed_total",
    "Total Celery tasks completed",
    ["queue_name"],
)

CELERY_TASKS_FAILED_TOTAL = Counter(
    "velto_celery_tasks_failed_total",
    "Total Celery tasks failed",
    ["queue_name"],
)

CELERY_TASKS_RETRIED_TOTAL = Counter(
    "velto_celery_tasks_retried_total",
    "Total Celery tasks retried",
    ["queue_name"],
)


# ── Helper metric dispatch functions ──────────────────────────────────────────
def record_conversion_metrics(
    status: str = "unknown",
    source_format: str = "unknown",
    target_format: str = "unknown",
    duration_seconds: float = 0.0,
    queue_wait_seconds: float = 0.0,
    error_category: str = "none",
    **kwargs,
) -> None:
    """Record comprehensive conversion metrics upon job state transition."""
    # Allow source_format or status to be passed as first positional arg
    if status in ("created", "queued", "started", "processing", "completed", "failed", "cancelled", "retrying"):
        st = status.lower()
        src = source_format.lower()
        tgt = target_format.lower()
    else:
        src = status.lower()
        tgt = source_format.lower()
        st = target_format.lower()

    cat = error_category.lower() or "none"

    CONVERSIONS_TOTAL.labels(source_format=src, target_format=tgt, status=st, error_category=cat).inc()

    if duration_seconds > 0:
        CONVERSION_DURATION_SECONDS.labels(source_format=src, target_format=tgt, status=st).observe(duration_seconds)

    if queue_wait_seconds > 0:
        CONVERSION_QUEUE_WAIT_SECONDS.labels(source_format=src, target_format=tgt).observe(queue_wait_seconds)

    if st == "completed":
        CONVERSIONS_SUCCEEDED_TOTAL.labels(source_format=src, target_format=tgt).inc()
    elif st == "failed":
        CONVERSIONS_FAILED_TOTAL.labels(source_format=src, target_format=tgt, error_category=cat).inc()
    elif st == "cancelled":
        CONVERSIONS_CANCELLED_TOTAL.labels(source_format=src, target_format=tgt).inc()


def record_storage_metrics(
    operation: str,
    backend: str = "local",
    duration_seconds: float = 0.0,
    success: bool = True,
    status: str = "success",
    bytes_transferred: int = 0,
) -> None:
    """Record storage read/write/delete metrics."""
    op = operation.lower()
    bk = backend.lower()
    STORAGE_OPERATIONS_TOTAL.labels(operation=op, backend=bk).inc()
    if duration_seconds > 0:
        STORAGE_OPERATION_DURATION_SECONDS.labels(operation=op, backend=bk).observe(duration_seconds)
    if not success or status == "failure":
        STORAGE_FAILURES_TOTAL.labels(operation=op, backend=bk).inc()


def record_storage_failure(operation: str, backend: str = "local") -> None:
    """Record a failed storage operation."""
    record_storage_metrics(operation=operation, backend=backend, duration_seconds=0.0, success=False, status="failure")


def record_celery_task_started(queue_name: str = "celery") -> None:
    CELERY_TASKS_STARTED_TOTAL.labels(queue_name=queue_name.lower()).inc()


def record_celery_task_completed(queue_name: str = "celery") -> None:
    CELERY_TASKS_COMPLETED_TOTAL.labels(queue_name=queue_name.lower()).inc()


def record_celery_task_failed(queue_name: str = "celery") -> None:
    CELERY_TASKS_FAILED_TOTAL.labels(queue_name=queue_name.lower()).inc()


def record_celery_task_retried(queue_name: str = "celery") -> None:
    CELERY_TASKS_RETRIED_TOTAL.labels(queue_name=queue_name.lower()).inc()


def get_metrics_summary() -> dict:
    """Return serialized Prometheus text exposition summary for testing."""
    from prometheus_client import generate_latest
    return {"conversions_total": generate_latest().decode("utf-8")}
