"""
Security exceptions for VELTO Conversion.

All security exceptions inherit from SecurityValidationError, which inherits
from ConversionError. This ensures that any conversion engine or service layer
catching ConversionError will automatically handle security validation failures
with clear, safe, user-friendly error messages and stable error codes.
"""

from apps.conversions.engines.base import ConversionError


class SecurityValidationError(ConversionError):
    """Base class for all security validation failures in VELTO Conversion."""
    error_code = "security_validation_failed"

    def __init__(self, message: str, code: str | None = None):
        super().__init__(message)
        if code:
            self.error_code = code


class InvalidMimeType(SecurityValidationError):
    """Raised when uploaded file MIME type does not match content or operation requirements."""
    error_code = "invalid_mime_type"


class InvalidFileSignature(SecurityValidationError):
    """Raised when magic bytes or file header signatures do not match the expected format."""
    error_code = "invalid_file_signature"


class FileTooLarge(SecurityValidationError):
    """Raised when uploaded file or request exceeds size limits."""
    error_code = "file_too_large"


class OutputTooLarge(SecurityValidationError):
    """Raised when generated output exceeds maximum permitted size."""
    error_code = "output_too_large"


class UnsafeFilename(SecurityValidationError):
    """Raised when a filename contains dangerous characters, traversal sequences, or reserved names."""
    error_code = "invalid_filename"


class PathTraversalAttempt(SecurityValidationError):
    """Raised when a path escapes the authorized workspace directory."""
    error_code = "path_traversal_detected"


class OwnershipDenied(SecurityValidationError):
    """Raised when a user or session attempts to access resources owned by another session/user."""
    error_code = "ownership_denied"


class RateLimitExceeded(SecurityValidationError):
    """Raised when a client exceeds configured request rate limits."""
    error_code = "rate_limit_exceeded"


class AbuseLimitExceeded(SecurityValidationError):
    """Raised when request frequency or resource usage indicates automated abuse."""
    error_code = "abuse_limit_exceeded"


class MalwareDetected(SecurityValidationError):
    """Raised when antivirus scanning detects malicious content."""
    error_code = "malware_detected"


class AntivirusUnavailable(SecurityValidationError):
    """Raised when antivirus scanning is required by policy but the scanner service is offline."""
    error_code = "antivirus_unavailable"


class SandboxUnavailable(SecurityValidationError):
    """Raised when sandboxed execution is required by policy but unavailable."""
    error_code = "sandbox_unavailable"


class ArchiveLimitExceeded(SecurityValidationError):
    """Raised when archive compression ratio, member count, or expanded size exceeds safety limits."""
    error_code = "archive_limit_exceeded"


class ProcessingTimeout(SecurityValidationError):
    """Raised when a conversion or OCR operation exceeds maximum processing duration."""
    error_code = "processing_timeout"


class DocumentLimitExceeded(SecurityValidationError):
    """Raised when document page count, spreadsheet dimensions, or image pixels exceed limits."""
    error_code = "document_limit_exceeded"
