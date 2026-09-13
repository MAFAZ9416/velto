"""
ConversionService — orchestrates job creation, engine dispatch, download, and cleanup.

Phase 2 changes:
  - create_job() now saves the staged input_path to the DB.
  - process_job() is fully implemented: finds engine, runs conversion,
    verifies output, updates job to completed or failed.
  - get_job_output() returns the output path for the download view.
  - cleanup_job_files() removes staged temp files safely.

Design principles:
  - Views delegate ALL lifecycle to this service.
  - Engines contain NO Django or database code.
  - No fake conversions; no fake success.
  - Errors are logged in full for developers; only safe messages reach the API.
"""

import logging
import os
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

logger = logging.getLogger(__name__)


class ConversionServiceError(Exception):
    """Raised for business-logic errors in ConversionService (e.g. invalid format pair)."""


class JobNotFoundError(ConversionServiceError):
    """Raised when a job cannot be found or does not belong to the requester."""


class ConversionService:
    """
    Stateless service class — all methods are class methods or static methods.

    This design makes it easy to call from views without instantiation and
    straightforward to mock in tests.
    """

    # ── Directory helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _get_temp_dir() -> Path:
        """Return and ensure the staging directory exists."""
        temp_dir = Path(settings.TEMP_UPLOAD_DIR)
        temp_dir.mkdir(parents=True, exist_ok=True)
        return temp_dir

    @staticmethod
    def _build_output_filename(original_filename: str, target_format: str) -> str:
        """
        Derive a safe, user-friendly output filename.

        Strips the original extension and appends the target format extension.
        Example: "my report.pdf" + "docx" → "my report.docx"
        """
        stem = Path(original_filename).stem
        # Sanitise: keep only printable ASCII, replace risky chars
        safe_stem = "".join(c if c.isalnum() or c in " _-" else "_" for c in stem).strip()
        if not safe_stem:
            safe_stem = "converted"
        return f"{safe_stem}.{target_format}"

    # ── File staging ───────────────────────────────────────────────────────────

    @classmethod
    def stage_uploaded_file(cls, uploaded_file: UploadedFile, source_format: str) -> str:
        """
        Write the uploaded file to the temporary staging directory.

        Uses a UUID-prefixed name to:
          - Prevent filename collisions.
          - Prevent path traversal (client-controlled filenames are never used as paths).

        Returns the absolute path to the staged file.
        """
        temp_dir = cls._get_temp_dir()
        # uuid4 prefix + safe basename — the client filename never becomes a path component
        staging_name = f"{uuid.uuid4().hex}_{Path(uploaded_file.name).name}"
        dest_path = temp_dir / staging_name

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

    # ── Job creation ───────────────────────────────────────────────────────────

    @classmethod
    def stage_uploaded_files(cls, uploaded_files: list[UploadedFile], source_format: str) -> str:
        """
        Stage multiple uploaded files into temporary staging directory.
        Writes a manifest text file listing staged file paths.
        """
        if len(uploaded_files) == 1:
            return cls.stage_uploaded_file(uploaded_files[0], source_format)

        temp_dir = cls._get_temp_dir()
        manifest_path = temp_dir / f"{uuid.uuid4().hex}_staged_manifest.txt"
        staged_paths = []

        for f in uploaded_files:
            staging_name = f"{uuid.uuid4().hex}_{Path(f.name).name}"
            dest_path = temp_dir / staging_name
            with open(dest_path, "wb") as dest:
                for chunk in f.chunks():
                    dest.write(chunk)
            staged_paths.append(str(dest_path))

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

        if uploaded_files and len(uploaded_files) > 1:
            staged_path = cls.stage_uploaded_files(uploaded_files, source_format)
            orig_filename = f"{len(uploaded_files)}_images.zip"
            total_bytes = sum(f.size for f in uploaded_files)
        elif uploaded_files and len(uploaded_files) == 1:
            staged_path = cls.stage_uploaded_file(uploaded_files[0], source_format)
            orig_filename = uploaded_files[0].name
            total_bytes = uploaded_files[0].size
        elif uploaded_file:
            staged_path = cls.stage_uploaded_file(uploaded_file, source_format)
            orig_filename = uploaded_file.name
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
            input_path=staged_path,       # saved so process_job() can find it
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
        # ── Guard: never re-process a terminal job ──────────────────────────
        if job.is_terminal:
            logger.warning(
                "process_job called on terminal job %s (status=%s) — skipping.",
                job.id,
                job.status,
            )
            return job

        # ── Resolve engine ──────────────────────────────────────────────────
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


        # ── Confirm input file exists ───────────────────────────────────────
        if not job.input_path or not Path(job.input_path).exists():
            cls._fail_job(
                job,
                user_message="The uploaded file could not be found. Please try again.",
            )
            logger.error(
                "process_job: input file missing for job %s (expected: %s)",
                job.id,
                job.input_path,
            )
            return job

        # ── Mark PROCESSING (atomic) ────────────────────────────────────────
        with transaction.atomic():
            job.status = JobStatus.PROCESSING
            job.started_at = timezone.now()
            job.save(update_fields=["status", "started_at"])

        # ── Build output path ───────────────────────────────────────────────
        temp_dir = cls._get_temp_dir()
        output_filename = cls._build_output_filename(
            job.original_filename, job.target_format
        )
        # UUID prefix prevents collisions and makes the path unguessable
        output_path = str(temp_dir / f"{uuid.uuid4().hex}_{output_filename}")

        # ── Run engine ──────────────────────────────────────────────────────
        engine = engine_cls()
        result_path = None
        runtime_opts = getattr(job, "_runtime_options", None) or job.options
        try:
            import inspect
            sig = inspect.signature(engine.convert)
            if "options" in sig.parameters:
                result_path = engine.convert(job.input_path, output_path, options=runtime_opts)
            else:
                result_path = engine.convert(job.input_path, output_path)

            if result_path:
                actual_path = Path(result_path)
                if actual_path.exists():
                    output_path = str(actual_path)
                    if output_path.lower().endswith(".zip") and not output_filename.lower().endswith(".zip"):
                        output_filename = f"{Path(output_filename).stem}.zip"
        except ConversionError as exc:
            # Known, recoverable error from the engine (bad PDF, encrypted, etc.)
            logger.warning(
                "process_job: engine raised ConversionError for job %s: %s",
                job.id,
                exc,
            )
            cls._fail_job(job, user_message=str(exc), output_path=result_path or output_path)
            return job
        except Exception as exc:
            # Unexpected engine error — log full trace, store safe message
            logger.exception(
                "process_job: unexpected engine error for job %s", job.id
            )
            cls._fail_job(
                job,
                user_message=(
                    "An unexpected error occurred during conversion. "
                    "Our team has been notified. Please try again later."
                ),
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

        # ── Clean up input file after successful conversion ─────────────────
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
        Return the absolute output file path for a completed job, or None.
        """
        if job.status != JobStatus.COMPLETED:
            return None
        if not job.output_path:
            return None
        if not Path(job.output_path).exists():
            logger.warning(
                "get_job_output: output file missing for completed job %s: %s",
                job.id,
                job.output_path,
            )
            return None
        return job.output_path

    # ── Cleanup ────────────────────────────────────────────────────────────────

    @classmethod
    def cleanup_job_files(cls, job: ConversionJob) -> None:
        """
        Delete both input and output staged files for a job.
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
        """
        Transition a job to FAILED and store a user-safe error message.
        """
        with transaction.atomic():
            job.status = JobStatus.FAILED
            job.error_message = user_message
            job.completed_at = timezone.now()
            job.save(update_fields=["status", "error_message", "completed_at"])

        # Clean up input file and any partial output file
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
                import shutil
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
                logger.debug("Deleted %s file: %s", label, path)
        except OSError as exc:
            logger.warning("Could not delete %s file %s: %s", label, path, exc)

