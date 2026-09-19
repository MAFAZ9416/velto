"""
Structured JSON Logging & Security Event Tracing for VELTO Conversion.

Provides:
- VeltoJsonFormatter: Production JSON log formatter with sensitive data redaction.
- Structured event logging helper `log_event(event_name, ...)` for consistent log structures.
- Sensitive credential and token redaction filter.
"""

import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any

from django.conf import settings

# Sensitive parameter keys that must never appear in raw log dictionaries
SENSITIVE_KEYS = {
    "password",
    "old_password",
    "new_password",
    "password_confirm",
    "token",
    "access",
    "refresh",
    "secret",
    "secret_key",
    "access_key",
    "api_key",
    "authorization",
    "email_verification_token",
    "password_reset_token",
    "s3_secret_access_key",
}

# Regex for stripping S3 signature parameters from logged URLs
S3_SIG_REGEX = re.compile(r"X-Amz-Signature=[a-f0-9]+", re.IGNORECASE)


def sanitize_log_value(key: str, value: Any) -> Any:
    """Redact sensitive fields or secrets in log dictionaries."""
    key_lower = str(key).lower()
    if any(s in key_lower for s in SENSITIVE_KEYS):
        return "[REDACTED]"

    if isinstance(value, str):
        if "X-Amz-Signature=" in value or "Signature=" in value:
            return S3_SIG_REGEX.sub("X-Amz-Signature=[REDACTED]", value)
        if any(sec in value.lower() for sec in ("bearer ", "password=", "secret_key=")):
            return "[REDACTED]"

    return value


def redact_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively redact sensitive keys from a dictionary before serializing."""
    clean = {}
    for k, v in data.items():
        if isinstance(v, dict):
            clean[k] = redact_dict(v)
        elif isinstance(v, list):
            clean[k] = [redact_dict(item) if isinstance(item, dict) else sanitize_log_value(k, item) for item in v]
        else:
            clean[k] = sanitize_log_value(k, v)
    return clean


class SensitiveDataRedactionFilter(logging.Filter):
    """
    Logging Filter that redacts sensitive keywords (passwords, tokens, keys)
    from log messages before handlers format or write them.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = sanitize_log_value("msg", record.msg)
        return True


class VeltoJsonFormatter(logging.Formatter):
    """
    JSON Formatter for production logging.
    Emits structured JSON log records with standard observability context.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "event": getattr(record, "event", record.name),
            "service": getattr(record, "service", "velto-backend"),
            "environment": getattr(settings, "DJANGO_ENV", "production"),
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add optional observability correlation attributes if present on record
        for attr in (
            "request_id",
            "user_id",
            "job_id",
            "task_id",
            "source_format",
            "target_format",
            "status",
            "duration_ms",
            "error_code",
            "error_category",
            "queue_name",
            "file_size_bytes",
            "output_size_bytes",
        ):
            val = getattr(record, attr, None)
            if val is not None:
                log_payload[attr] = sanitize_log_value(attr, val)

        # Include sanitized extra context if passed
        extra_ctx = getattr(record, "extra_ctx", None)
        if isinstance(extra_ctx, dict):
            log_payload["details"] = redact_dict(extra_ctx)

        if record.exc_info and not record.exc_text:
            record.exc_text = self.formatException(record.exc_info)

        if record.exc_text:
            log_payload["exception"] = record.exc_text.splitlines()[-1]  # Safe summary line only

        return json.dumps(log_payload)


def log_event(event_name_or_logger: Any, *args, **kwargs) -> None:
    """
    Flexible helper function for emitting structured log events across VELTO components.

    Supports both:
      log_event("conversion.started", service="conversion", job_id="...")
    and:
      log_event(logger_instance, logging.INFO, "conversion.started", "Started job", job_id="...")
    """
    if isinstance(event_name_or_logger, logging.Logger):
        target_logger = event_name_or_logger
        level = args[0] if len(args) > 0 else logging.INFO
        event_name = args[1] if len(args) > 1 else "event"
        message = args[2] if len(args) > 2 else f"Event: {event_name}"
    else:
        target_logger = logging.getLogger("velto.observability")
        event_name = str(event_name_or_logger)
        level = kwargs.pop("level", logging.INFO)
        message = kwargs.pop("message", f"Event: {event_name}")

    extra = {"event": event_name}
    for k, v in list(kwargs.items()):
        if k not in ("event", "level", "message"):
            extra[k] = sanitize_log_value(k, v)

    target_logger.log(level, message, extra=extra)
