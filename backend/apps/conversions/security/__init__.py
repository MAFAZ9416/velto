"""
VELTO Conversion Security Package.

Exposes centralized security validation, path protection, filename sanitization,
antivirus scanning, sandbox execution, rate throttling, and resource limit routines.
"""

from apps.conversions.security.exceptions import (
    AbuseLimitExceeded,
    AntivirusUnavailable,
    ArchiveLimitExceeded,
    DocumentLimitExceeded,
    FileTooLarge,
    InvalidFileSignature,
    InvalidMimeType,
    MalwareDetected,
    OutputTooLarge,
    OwnershipDenied,
    PathTraversalAttempt,
    ProcessingTimeout,
    RateLimitExceeded,
    SandboxUnavailable,
    SecurityValidationError,
    UnsafeFilename,
)
from apps.conversions.security.filenames import (
    generate_internal_filename,
    sanitize_filename,
)
from apps.conversions.security.mime_validation import (
    detect_file_mime_type,
    validate_mime_type,
)
from apps.conversions.security.ownership import (
    check_job_ownership,
    filter_jobs_for_request,
    get_request_owner_identity,
)
from apps.conversions.security.paths import (
    resolve_safe_path,
    validate_path_containment,
)
from apps.conversions.security.signatures import (
    validate_file_signature,
    validate_office_zip_signature,
    validate_text_signature,
)
from apps.conversions.security.limits import (
    MAX_UPLOAD_SIZE,
    MAX_SINGLE_FILE_SIZE,
    MAX_COMBINED_REQUEST_SIZE,
    MAX_OUTPUT_SIZE,
)
from apps.conversions.security.antivirus import scan_file_security
from apps.conversions.security.sandbox import run_sandboxed_command
from apps.conversions.security.archive_limits import validate_zip_archive_security
from apps.conversions.security.abuse import check_concurrent_jobs, check_job_timeout
from apps.conversions.security.diagnostics import get_security_diagnostics
from apps.conversions.security.rate_limits import (
    DownloadRateThrottle,
    JobCreateRateThrottle,
    OcrRateThrottle,
    PdfUtilityRateThrottle,
    UploadRateThrottle,
)

__all__ = [
    "SecurityValidationError",
    "InvalidMimeType",
    "InvalidFileSignature",
    "FileTooLarge",
    "OutputTooLarge",
    "UnsafeFilename",
    "PathTraversalAttempt",
    "OwnershipDenied",
    "RateLimitExceeded",
    "AbuseLimitExceeded",
    "MalwareDetected",
    "AntivirusUnavailable",
    "SandboxUnavailable",
    "ArchiveLimitExceeded",
    "ProcessingTimeout",
    "DocumentLimitExceeded",
    "sanitize_filename",
    "generate_internal_filename",
    "resolve_safe_path",
    "validate_path_containment",
    "validate_file_signature",
    "validate_office_zip_signature",
    "validate_text_signature",
    "detect_file_mime_type",
    "validate_mime_type",
    "check_job_ownership",
    "filter_jobs_for_request",
    "get_request_owner_identity",
    "scan_file_security",
    "run_sandboxed_command",
    "validate_zip_archive_security",
    "check_concurrent_jobs",
    "check_job_timeout",
    "get_security_diagnostics",
    "MAX_UPLOAD_SIZE",
    "MAX_SINGLE_FILE_SIZE",
    "MAX_COMBINED_REQUEST_SIZE",
    "MAX_OUTPUT_SIZE",
    "UploadRateThrottle",
    "JobCreateRateThrottle",
    "OcrRateThrottle",
    "PdfUtilityRateThrottle",
    "DownloadRateThrottle",
]
