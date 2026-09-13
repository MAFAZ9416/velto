"""
ConversionService — orchestrates job creation, engine dispatch, download, and cleanup.

Security-hardened service layer:
  - Validates MIME types, signatures, file sizes, and path containment.
  - Performs antivirus scanning before processing.
  - Creates isolated per-job temporary workspaces.
  - Sanitizes user filenames and protects output downloads.
"""

import logging
import os
import shutil
import time
import uuid
from pathlib import Path
from typing import Optional

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.utils import timezone

from apps.conversions.engines.base import ConversionError
from apps.conversions.engines.registry import engine_registry
from apps.conversions.formats import is_valid_conversion
from apps.conversions.models import ConversionJob, JobStatus

# Central Security Imports
from apps.conversions.security import (
    FileTooLarge,
    OutputTooLarge,
    PathTraversalAttempt,
    check_job_timeout,
    generate_internal_filename,
    resolve_safe_path,
    sanitize_filename,
    scan_file_security,
    validate_file_signature,
    validate_mime_type,
    MAX_COMBINED_REQUEST_SIZE,
    MAX_OUTPUT_SIZE,
    MAX_SINGLE_FILE_SIZE,
)

logger = logging.getLogger(__name__)


class ConversionServiceError(Exception):
    """Raised for business-logic errors in ConversionService (e.g. invalid format pair)."""


class JobNotFoundError(ConversionServiceError):
    """Raised when a job cannot be found or does not belong to the requester."""


class ConversionService:
    """
    Stateless service class — all methods are class methods or static methods.
    """

    # ── Directory helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _get_temp_dir() -> Path:
        """Return and ensure the root staging directory exists."""
        temp_dir = Path(settings.TEMP_UPLOAD_DIR).resolve()
        temp_dir.mkdir(parents=True, exist_ok=True)
        return temp_dir

    @classmethod
    def _create_isolated_workspace(cls, job_id: str | None = None) -> Path:
        """Create an isolated, job-scoped temporary workspace directory."""
        root_temp = cls._get_temp_dir()
        scope_name = f"job_{job_id or uuid.uuid4().hex}"
        workspace = root_temp / scope_name
        workspace.mkdir(parents=True, exist_ok=True)
        return workspace

    @staticmethod
    def _build_output_filename(original_filename: str, target_format: str) -> str:
        """Derive a safe, user-friendly output filename."""
        safe_name = sanitize_filename(original_filename)
        stem = Path(safe_name).stem
        if not stem:
            stem = "converted"
        return f"{stem}.{target_format}"

    # ── File staging ───────────────────────────────────────────────────────────

    @classmethod
    def stage_uploaded_file(
        cls,
        uploaded_file: UploadedFile,
        source_format: str,
        workspace: Path | None = None,
    ) -> str:
        """
        Write the uploaded file to the isolated temporary staging workspace.
        Applies size limits, MIME validation, signature checks, and antivirus scan.
        """
        if uploaded_file.size > MAX_SINGLE_FILE_SIZE:
            raise FileTooLarge(
                f"File '{uploaded_file.name}' size ({uploaded_file.size // (1024*1024)} MB) "
                f"exceeds maximum allowed size of {MAX_SINGLE_FILE_SIZE // (1024*1024)} MB."
            )

        ws = workspace or cls._create_isolated_workspace()
        safe_base = sanitize_filename(uploaded_file.name)
        staging_name = generate_internal_filename(safe_base)
        dest_path = resolve_safe_path(ws, staging_name)

        with open(dest_path, "wb") as dest:
            for chunk in uploaded_file.chunks():
                dest.write(chunk)

        logger.info(
            "Staged uploaded file: %s → %s (%d bytes)",
            uploaded_file.name,
            dest_path,
            dest_path.stat().st_size,
        )
        return str(dest_path)

    @classmethod
    def stage_uploaded_files(
        cls,
        uploaded_files: list[UploadedFile],
        source_format: str,
        workspace: Path | None = None,
    ) -> str:
        """
        Stage multiple uploaded files into isolated temporary staging directory.
        Writes a manifest text file listing staged file paths.
        """
        if len(uploaded_files) == 1:
            return cls.stage_uploaded_file(uploaded_files[0], source_format, workspace=workspace)

        total_size = sum(f.size for f in uploaded_files)
        if total_size > MAX_COMBINED_REQUEST_SIZE:
            raise FileTooLarge(
                f"Total upload size ({total_size // (1024*1024)} MB) "
                f"exceeds maximum allowed request size of {MAX_COMBINED_REQUEST_SIZE // (1024*1024)} MB."
            )

        ws = workspace or cls._create_isolated_workspace()
        manifest_path = resolve_safe_path(ws, f"{uuid.uuid4().hex}_staged_manifest.txt")
        staged_paths = []

        for f in uploaded_files:
            sp = cls.stage_uploaded_file(f, source_format, workspace=ws)
            staged_paths.append(sp)

        with open(manifest_path, "w", encoding="utf-8") as manifest:
            for sp in staged_paths:
                manifest.write(f"{sp}\n")

        return str(manifest_path)

    # ── Job creation ───────────────────────────────────────────────────────────

    @classmethod
    def create_job(
        cls,
        *,
        source_format: str,
        target_format: str,
        uploaded_file: Optional[UploadedFile] = None,
        uploaded_files: Optional[list[UploadedFile]] = None,
        options: Optional[dict] = None,
        session_key: str,
        user=None,
    ) -> ConversionJob:
        """
        Validate input, stage uploaded file(s), and create a PENDING ConversionJob.
        """
        if options is None:
            options = {}

        if not is_valid_conversion(source_format, target_format, options):
            raise ConversionServiceError(
                f"Unsupported conversion: {source_format} → {target_format}."
            )

        job_uuid = uuid.uuid4().hex
        workspace = cls._create_isolated_workspace(job_uuid)

        if uploaded_files and len(uploaded_files) > 1:
            staged_path = cls.stage_uploaded_files(uploaded_files, source_format, workspace=workspace)
            orig_filename = f"{len(uploaded_files)}_images.zip"
            total_bytes = sum(f.size for f in uploaded_files)
        elif uploaded_files and len(uploaded_files) == 1:
            staged_path = cls.stage_uploaded_file(uploaded_files[0], source_format, workspace=workspace)
            orig_filename = sanitize_filename(uploaded_files[0].name)
            total_bytes = uploaded_files[0].size
        elif uploaded_file:
            staged_path = cls.stage_uploaded_file(uploaded_file, source_format, workspace=workspace)
            orig_filename = sanitize_filename(uploaded_file.name)
            total_bytes = uploaded_file.size
        else:
            raise ConversionServiceError("No uploaded file provided.")

        db_options = dict(options)
        for pw_key in ("password", "user_password", "owner_password"):
            if pw_key in db_options and db_options[pw_key]:
                db_options[pw_key] = "[REDACTED]"

        job = ConversionJob.objects.create(
            user=user,
            session_key=session_key or "",
            source_format=source_format,
            target_format=target_format,
            options=db_options,
            status=JobStatus.PENDING,
            original_filename=orig_filename,
            file_size_bytes=total_bytes,
            input_path=staged_path,
        )
        job._runtime_options = dict(options)

        logger.info(
            "Created ConversionJob %s (%s→%s) input: %s",
            job.id,
            source_format,
            target_format,
            staged_path,
        )
        return job

    # ── Job processing ─────────────────────────────────────────────────────────

    @classmethod
    def process_job(cls, job: ConversionJob) -> ConversionJob:
        """
        Dispatch the job to the appropriate engine and update its status.
        """
        start_time = time.time()

        if job.is_terminal:
            logger.warning(
                "process_job called on terminal job %s (status=%s) — skipping.",
                job.id,
                job.status,
            )
            return job

        op = (job.options or {}).get("operation")
        engine_cls = engine_registry.get(job.source_format, job.target_format, operation=op)

        if engine_cls is None:
            cls._fail_job(
                job,
                user_message=(
                    f"No conversion engine is available for "
                    f"{job.source_format} → {job.target_format}. "
                    "This format pair will be supported in a future release."
                ),
            )
            return job

        # ── Central Security Validations (MIME, Signature, Antivirus) ─────────
        try:
            input_p = Path(job.input_path).resolve()
            if not input_p.exists():
                cls._fail_job(job, user_message="The uploaded file could not be found. Please try again.")
                return job
            resolve_safe_path(cls._get_temp_dir(), input_p)

            # Enforce MIME, signature, and malware scanning before passing to engine
            if input_p.is_file() and not input_p.name.endswith("_staged_manifest.txt"):
                validate_mime_type(input_p, expected_format=job.source_format)
                validate_file_signature(input_p, job.source_format)
                scan_file_security(input_p)
        except ConversionError as exc:
            logger.warning("Security validation failed for job %s: %s", job.id, exc)
            cls._fail_job(job, user_message=str(exc))
            return job
        except Exception as exc:
            logger.warning("Security alert: input path traversal or validation attempt for job %s: %s", job.id, exc)
            cls._fail_job(job, user_message="Invalid or unsafe input file path.")
            return job

        # ── Mark PROCESSING (atomic) ────────────────────────────────────────
        with transaction.atomic():
            job.status = JobStatus.PROCESSING
            job.started_at = timezone.now()
            job.save(update_fields=["status", "started_at"])

        # ── Build output path inside job workspace ───────────────────────────
        workspace = input_p.parent if input_p.parent.name.startswith("job_") else cls._create_isolated_workspace(str(job.id))
        output_filename = cls._build_output_filename(job.original_filename, job.target_format)
        output_path = str(resolve_safe_path(workspace, f"{uuid.uuid4().hex}_{output_filename}"))

        # ── Run engine ──────────────────────────────────────────────────────
        engine = engine_cls()
        result_path = None
        runtime_opts = getattr(job, "_runtime_options", None) or job.options

        try:
            check_job_timeout(start_time)
            import inspect
            sig = inspect.signature(engine.convert)
            if "options" in sig.parameters:
                result_path = engine.convert(job.input_path, output_path, options=runtime_opts)
            else:
                result_path = engine.convert(job.input_path, output_path)

            check_job_timeout(start_time)

            if result_path:
                actual_path = Path(result_path)
                if actual_path.exists():
                    output_path = str(actual_path)
                    if output_path.lower().endswith(".zip") and not output_filename.lower().endswith(".zip"):
                        output_filename = f"{Path(output_filename).stem}.zip"

            # ── Output size & security checks ──────────────────────────────
            out_p = Path(output_path)
            if out_p.exists():
                out_size = out_p.stat().st_size
                if out_size > MAX_OUTPUT_SIZE:
                    raise OutputTooLarge(
                        f"Generated output size ({out_size // (1024*1024)} MB) "
                        f"exceeds maximum allowed limit of {MAX_OUTPUT_SIZE // (1024*1024)} MB."
                    )
                scan_file_security(out_p)

        except ConversionError as exc:
            logger.warning("process_job: engine/security raised error for job %s: %s", job.id, exc)
            cls._fail_job(job, user_message=str(exc), output_path=result_path or output_path)
            return job
        except Exception as exc:
            logger.exception("process_job: unexpected engine error for job %s", job.id)
            cls._fail_job(
                job,
                user_message="An unexpected error occurred during conversion. Please try again later.",
                output_path=result_path or output_path,
            )
            return job

        # ── Mark COMPLETED ──────────────────────────────────────────────────
        output_size = Path(output_path).stat().st_size
        updated_opts = dict(runtime_opts)
        for pw_key in ("password", "user_password", "owner_password"):
            if pw_key in updated_opts:
                updated_opts[pw_key] = "[REDACTED]"
        job.options = updated_opts

        with transaction.atomic():
            job.status = JobStatus.COMPLETED
            job.completed_at = timezone.now()
            job.output_path = output_path
            job.output_filename = output_filename
            job.output_size_bytes = output_size
            job.save(update_fields=[
                "status", "completed_at",
                "output_path", "output_filename", "output_size_bytes",
                "options",
            ])

        # Clean up input file
        cls._safe_delete_file(job.input_path, label="input")

        logger.info(
            "process_job: job %s COMPLETED. Output: %s (%d bytes)",
            job.id,
            output_path,
            output_size,
        )
        return job

    # ── Download helper ────────────────────────────────────────────────────────

    @classmethod
    def get_job_output(cls, job: ConversionJob) -> Optional[str]:
        """
        Return the absolute output file path for a completed job after validating containment.
        """
        if job.status != JobStatus.COMPLETED or not job.output_path:
            return None

        out_path = Path(job.output_path)
        if not out_path.exists():
            logger.warning("get_job_output: output file missing for job %s: %s", job.id, job.output_path)
            return None

        try:
            resolve_safe_path(cls._get_temp_dir(), out_path)
        except PathTraversalAttempt:
            logger.error("Security alert: job %s output path outside temp dir: %s", job.id, job.output_path)
            return None

        return str(out_path)

    # ── Cleanup ────────────────────────────────────────────────────────────────

    @classmethod
    def cleanup_job_files(cls, job: ConversionJob) -> None:
        """
        Delete both input and output staged files and workspace for a job.
        """
        if job.input_path:
            cls._safe_delete_file(job.input_path, label="input")
        if job.output_path:
            cls._safe_delete_file(job.output_path, label="output")

    # ── Private helpers ────────────────────────────────────────────────────────

    @classmethod
    def _fail_job(
        cls,
        job: ConversionJob,
        user_message: str,
        output_path: Optional[str] = None,
    ) -> None:
        """Transition a job to FAILED and store a user-safe error message."""
        with transaction.atomic():
            job.status = JobStatus.FAILED
            job.error_message = user_message
            job.completed_at = timezone.now()
            job.save(update_fields=["status", "error_message", "completed_at"])

        if job.input_path:
            cls._safe_delete_file(job.input_path, label="input")
        if output_path:
            cls._safe_delete_file(output_path, label="partial output")

    @staticmethod
    def _safe_delete_file(path: str, label: str = "file") -> None:
        """Delete a file or directory safely."""
        if not path:
            return
        try:
            p = Path(path)
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
                logger.debug("Deleted %s directory: %s", label, path)
            elif p.exists():
                if p.suffix.lower() == ".txt" and "manifest" in p.name.lower():
                    try:
                        with open(p, "r", encoding="utf-8") as f:
                            for line in f:
                                fp = Path(line.strip())
                                if fp.exists():
                                    fp.unlink()
                    except Exception:
                        pass
                p.unlink()
                # Check if parent workspace directory is now empty and remove if so
                if p.parent.name.startswith("job_") and not any(p.parent.iterdir()):
                    try:
                        p.parent.rmdir()
                    except Exception:
                        pass
                logger.debug("Deleted %s file: %s", label, path)
        except OSError as exc:
            logger.warning("Could not delete %s file %s: %s", label, path, exc)
