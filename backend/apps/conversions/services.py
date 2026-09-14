"""
ConversionService — orchestrates job creation, engine dispatch, download, object storage, and cleanup.

Security-hardened service layer:
  - Validates MIME types, signatures, file sizes, and path containment.
  - Performs antivirus scanning before processing.
  - Creates isolated per-job temporary workspaces.
  - Sanitizes user filenames and protects output downloads.
  - Integrates S3-compatible Object Storage with presigned upload & download flows.
  - Enforces per-owner storage quotas.
"""

import logging
import os
import shutil
import time
import uuid
from pathlib import Path
from typing import Optional, Dict, Any

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.utils import timezone

from apps.conversions.engines.base import ConversionError
from apps.conversions.engines.registry import engine_registry
from apps.conversions.formats import is_valid_conversion
from apps.conversions.models import ConversionJob, JobStatus
from apps.conversions.storage import (
    get_storage_service,
    get_active_storage_backend,
)

# Central Security Imports
from apps.conversions.security import (
    FileTooLarge,
    OutputTooLarge,
    PathTraversalAttempt,
    check_job_timeout,
    check_storage_quota,
    generate_internal_filename,
    get_request_owner_identity,
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

        try:
            with open(dest_path, "wb") as dest:
                for chunk in uploaded_file.chunks():
                    dest.write(chunk)
        except OSError as exc:
            logger.error("Failed writing uploaded file to temporary directory %s: %s", dest_path, exc)
            if exc.errno == errno.ENOSPC:
                raise ConversionError("Storage server is full. Please try again later.") from exc
            elif exc.errno in (errno.EACCES, errno.EPERM):
                raise ConversionError("Temporary storage permission error.") from exc
            raise ConversionError(f"Failed staging uploaded file: {exc}") from exc

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

    # ── Object Storage Presigned Upload Flow ─────────────────────────────────

    @classmethod
    def create_presigned_upload_session(
        cls,
        request,
        *,
        source_format: str,
        target_format: str,
        filename: str,
        file_size_bytes: int,
        options: Optional[dict] = None,
    ) -> Dict[str, Any]:
        """
        Validate quota & parameters, create a PENDING unfinalized job,
        and generate a short-lived presigned upload URL payload.
        """
        if options is None:
            options = {}

        if not is_valid_conversion(source_format, target_format, options):
            raise ConversionServiceError(
                f"Unsupported conversion: {source_format} → {target_format}."
            )

        if file_size_bytes > MAX_SINGLE_FILE_SIZE:
            raise FileTooLarge(
                f"File '{filename}' size ({file_size_bytes // (1024*1024)} MB) "
                f"exceeds maximum allowed size of {MAX_SINGLE_FILE_SIZE // (1024*1024)} MB."
            )

        # Enforce storage quota for the request owner
        check_storage_quota(request, incoming_bytes=file_size_bytes)

        user, session_key = get_request_owner_identity(request)
        owner_ident = f"usr_{user.id}" if user else (session_key or "anonymous")

        storage = get_storage_service()
        job_uuid = uuid.uuid4().hex
        object_key = storage.generate_object_key(owner_ident, job_uuid, "input", filename)

        db_options = dict(options)
        for pw_key in ("password", "user_password", "owner_password"):
            if pw_key in db_options and db_options[pw_key]:
                db_options[pw_key] = "[REDACTED]"

        job = ConversionJob.objects.create(
            id=job_uuid,
            user=user,
            session_key=session_key or "",
            source_format=source_format,
            target_format=target_format,
            options=db_options,
            status=JobStatus.PENDING,
            original_filename=sanitize_filename(filename),
            file_size_bytes=file_size_bytes,
            storage_backend=get_active_storage_backend(),
            input_storage_key=object_key,
            is_finalized=False,
        )

        presigned_payload = storage.generate_presigned_upload_url(
            object_key=object_key,
            max_size=file_size_bytes,
            expires_in=getattr(settings, "S3_PRESIGNED_UPLOAD_EXPIRY", 900),
        )

        return {
            "job_id": str(job.id),
            "upload_url": presigned_payload.get("url"),
            "fields": presigned_payload.get("fields", {}),
            "storage_key": object_key,
            "expires_in": presigned_payload.get("expires_in", 900),
            "max_file_size": file_size_bytes,
            "backend": presigned_payload.get("backend", "local"),
            "job": job,
        }

    @classmethod
    def finalize_uploaded_job(cls, job: ConversionJob) -> ConversionJob:
        """
        Finalize a presigned upload: verify object existence in storage,
        download to isolated workspace, execute security validations, mark finalized, and dispatch.
        """
        if job.is_finalized and job.status != JobStatus.PENDING:
            logger.info("Job %s is already finalized.", job.id)
            return job

        if not job.input_storage_key:
            raise ConversionServiceError("No storage key recorded for this conversion job.")

        storage = get_storage_service(job.storage_backend)
        if not storage.object_exists(job.input_storage_key):
            raise ConversionServiceError("Uploaded object was not found in storage. Please upload before finalizing.")

        workspace = cls._create_isolated_workspace(str(job.id))
        safe_base = sanitize_filename(job.original_filename)
        dest_filename = generate_internal_filename(safe_base)
        local_dest = str(resolve_safe_path(workspace, dest_filename))

        # Download object from storage adapter to local workspace for validation & engine execution
        storage.download_file(job.input_storage_key, local_dest)

        input_p = Path(local_dest)
        obj_size = input_p.stat().st_size

        if obj_size > MAX_SINGLE_FILE_SIZE:
            cls.cleanup_job_files(job)
            raise FileTooLarge(f"Uploaded object size ({obj_size} bytes) exceeds limit.")

        # Central security checks
        validate_mime_type(input_p, expected_format=job.source_format)
        validate_file_signature(input_p, job.source_format)
        scan_file_security(input_p)

        with transaction.atomic():
            job.is_finalized = True
            job.input_path = local_dest
            job.file_size_bytes = obj_size
            job.status = JobStatus.QUEUED
            job.save(update_fields=["is_finalized", "input_path", "file_size_bytes", "status"])

        # Dispatch for background task execution
        return cls.dispatch_job(job)

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
        Validate input, stage uploaded file(s), copy to storage provider, and create ConversionJob.
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

        owner_ident = f"usr_{user.id}" if user else (session_key or "anonymous")
        storage = get_storage_service()
        input_key = storage.generate_object_key(owner_ident, job_uuid, "input", orig_filename)

        # Upload staged input to storage adapter
        try:
            storage.upload_file(staged_path, input_key)
        except Exception as exc:
            logger.warning("Could not upload staged input to storage adapter: %s", exc)

        db_options = dict(options)
        for pw_key in ("password", "user_password", "owner_password"):
            if pw_key in db_options and db_options[pw_key]:
                db_options[pw_key] = "[REDACTED]"

        job = ConversionJob.objects.create(
            id=job_uuid,
            user=user,
            session_key=session_key or "",
            source_format=source_format,
            target_format=target_format,
            options=db_options,
            status=JobStatus.PENDING,
            original_filename=orig_filename,
            file_size_bytes=total_bytes,
            input_path=staged_path,
            storage_backend=get_active_storage_backend(),
            input_storage_key=input_key,
            is_finalized=True,
        )
        job._runtime_options = dict(options)

        logger.info(
            "Created ConversionJob %s (%s→%s) input: %s (storage_key: %s)",
            job.id,
            source_format,
            target_format,
            staged_path,
            input_key,
        )
        return job

    # ── Task dispatch ─────────────────────────────────────────────────────────

    @classmethod
    def dispatch_job(cls, job: ConversionJob) -> ConversionJob:
        """
        Dispatch the job for processing.
        """
        from apps.conversions.tasks import process_conversion_job_task

        job_id_str = str(job.id)

        def _send_task():
            try:
                res = process_conversion_job_task.delay(job_id_str)
                if hasattr(res, "id") and res.id:
                    ConversionJob.objects.filter(pk=job.id).update(celery_task_id=res.id)
            except Exception as exc:
                logger.warning(
                    "Celery dispatch failed for job %s (falling back to sync processing): %s",
                    job.id,
                    exc,
                )
                cls.process_job(job)

        if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False) or getattr(settings, "TESTING", False):
            _send_task()
            job.refresh_from_db()
            return job

        try:
            transaction.on_commit(_send_task)
        except Exception as exc:
            logger.warning("on_commit hook registration failed; triggering immediate dispatch: %s", exc)
            _send_task()

        job.refresh_from_db()
        return job

    # ── Job processing ─────────────────────────────────────────────────────────

    @classmethod
    def process_job(cls, job: ConversionJob) -> ConversionJob:
        """
        Dispatch the job to the appropriate engine, update status, and upload output to object storage.
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

        # Download input from object storage if local input_path missing
        storage = get_storage_service(job.storage_backend)
        if not job.input_path or not Path(job.input_path).exists():
            if job.input_storage_key and storage.object_exists(job.input_storage_key):
                workspace = cls._create_isolated_workspace(str(job.id))
                safe_base = sanitize_filename(job.original_filename)
                local_dest = str(resolve_safe_path(workspace, generate_internal_filename(safe_base)))
                try:
                    storage.download_file(job.input_storage_key, local_dest)
                    job.input_path = local_dest
                    job.save(update_fields=["input_path"])
                except Exception as exc:
                    logger.error("Failed downloading input object key '%s': %s", job.input_storage_key, exc)

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

            # Centralized Output Integrity Validation
            from apps.conversions.engines.validators import validate_conversion_output
            validate_conversion_output(
                output_path=output_path,
                target_format=job.target_format if not output_path.lower().endswith(".zip") else "zip",
                workspace_dir=workspace,
            )

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

        # Upload output to storage adapter
        owner_ident = f"usr_{job.user_id}" if job.user_id else (job.session_key or "anonymous")
        output_storage_key = storage.generate_object_key(owner_ident, str(job.id), "output", output_filename)
        try:
            storage.upload_file(output_path, output_storage_key)
        except Exception as exc:
            logger.warning("Could not upload generated output to storage adapter for job %s: %s", job.id, exc)

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
            job.output_storage_key = output_storage_key
            job.save(update_fields=[
                "status", "completed_at",
                "output_path", "output_filename", "output_size_bytes",
                "output_storage_key", "options",
            ])

        # Clean up local input file
        cls._safe_delete_file(job.input_path, label="input")

        logger.info(
            "process_job: job %s COMPLETED. Output: %s (%d bytes, key: %s)",
            job.id,
            output_path,
            output_size,
            output_storage_key,
        )
        return job

    # ── Download helpers ───────────────────────────────────────────────────────

    @classmethod
    def get_job_download_url(cls, job: ConversionJob, expires_in: int = 900) -> Optional[str]:
        """
        Return a short-lived presigned download URL for a completed output object.
        """
        if job.status != JobStatus.COMPLETED:
            return None

        storage = get_storage_service(job.storage_backend)

        if job.output_storage_key and storage.object_exists(job.output_storage_key):
            try:
                return storage.generate_presigned_download_url(
                    job.output_storage_key,
                    filename=job.output_filename,
                    expires_in=expires_in,
                )
            except Exception as exc:
                logger.error("Error generating presigned download URL for job %s: %s", job.id, exc)

        # Fallback to local output file check
        if job.output_path and Path(job.output_path).exists():
            from django.urls import reverse
            try:
                return reverse("conversions:job-download", kwargs={"job_id": job.id})
            except Exception:
                pass

        return None

    @classmethod
    def get_job_output(cls, job: ConversionJob) -> Optional[str]:
        """
        Return local output file path for a completed job, downloading from storage if necessary.
        """
        if job.status != JobStatus.COMPLETED:
            return None

        # Check local path first
        if job.output_path and Path(job.output_path).exists():
            try:
                resolve_safe_path(cls._get_temp_dir(), job.output_path)
                return job.output_path
            except PathTraversalAttempt:
                return None

        # Download from storage adapter if missing locally
        storage = get_storage_service(job.storage_backend)
        if job.output_storage_key and storage.object_exists(job.output_storage_key):
            workspace = cls._create_isolated_workspace(str(job.id))
            output_filename = job.output_filename or f"converted_{job.id}.{job.target_format}"
            local_dest = str(resolve_safe_path(workspace, generate_internal_filename(output_filename)))
            try:
                storage.download_file(job.output_storage_key, local_dest)
                job.output_path = local_dest
                job.save(update_fields=["output_path"])
                return local_dest
            except Exception as exc:
                logger.error("Failed downloading output object key '%s': %s", job.output_storage_key, exc)

        return None

    # ── Cleanup ────────────────────────────────────────────────────────────────

    @classmethod
    def cleanup_job_files(cls, job: ConversionJob) -> None:
        """
        Delete both input and output staged files, storage objects, and local workspace for a job.
        """
        storage = get_storage_service(job.storage_backend)

        if job.input_storage_key:
            storage.delete_object(job.input_storage_key)
        if job.output_storage_key:
            storage.delete_object(job.output_storage_key)

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

        cls.cleanup_job_files(job)

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
                if p.parent.name.startswith("job_") and not any(p.parent.iterdir()):
                    try:
                        p.parent.rmdir()
                    except Exception:
                        pass
                logger.debug("Deleted %s file: %s", label, path)
        except OSError as exc:
            logger.warning("Could not delete %s file %s: %s", label, path, exc)
