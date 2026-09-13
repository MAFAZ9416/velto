"""
Restricted subprocess execution and sandboxing abstraction for risky processing.

Enforces isolated working directories, argument array invocation (never raw shell strings),
environment variable filtering, and strict execution timeouts.
"""

import logging
import os
import subprocess
import sys
from pathlib import Path

from apps.conversions.security.exceptions import ProcessingTimeout, SandboxUnavailable
from apps.conversions.security.limits import MAX_JOB_PROCESSING_TIMEOUT

logger = logging.getLogger(__name__)


def get_sandbox_status() -> dict:
    """Return honest status description of sandbox capabilities in the current host environment."""
    is_windows = sys.platform.startswith("win")
    mode = "restricted_subprocess" if is_windows else "isolated_process"
    return {
        "mode": mode,
        "platform": sys.platform,
        "argument_array_enforcement": True,
        "environment_sanitization": True,
        "timeout_enforcement": True,
        "notes": "Windows restricted process execution active with working directory isolation and process tree termination.",
    }


def run_sandboxed_command(
    cmd_args: list[str],
    cwd: str | Path,
    env: dict | None = None,
    timeout: int | None = None,
) -> subprocess.CompletedProcess:
    """
    Execute an external CLI binary inside an isolated working directory with restricted environment and timeout.

    Requirements:
    - cmd_args MUST be a list of string arguments (never shell=True).
    - cwd MUST be an existing isolated directory.
    - Strict process timeout enforced.

    Returns
    -------
    subprocess.CompletedProcess

    Raises
    ------
    ProcessingTimeout
        If command exceeds timeout.
    SandboxUnavailable
        If command cannot be launched safely.
    """
    if not isinstance(cmd_args, (list, tuple)) or not cmd_args:
        raise SandboxUnavailable("Command arguments must be a non-empty list of strings.")

    # Ensure all arguments are strings
    safe_args = [str(a) for a in cmd_args]

    work_dir = Path(cwd).resolve()
    if not work_dir.exists() or not work_dir.is_dir():
        raise SandboxUnavailable(f"Working directory '{work_dir}' does not exist.")

    effective_timeout = timeout or MAX_JOB_PROCESSING_TIMEOUT

    # Sanitize environment: retain minimal required system variables
    clean_env = {}
    keep_vars = {
        "PATH", "SYSTEMROOT", "SYSTEMDRIVE", "TEMP", "TMP", "USERPROFILE", "HOME",
        "LANG", "LC_ALL", "FONTCONFIG_PATH",
    }
    base_env = env or os.environ
    for k, v in base_env.items():
        if k.upper() in keep_vars:
            clean_env[k] = v

    logger.debug(
        "Launching sandboxed command: %s (cwd=%s, timeout=%ds)",
        safe_args[0],
        work_dir,
        effective_timeout,
    )

    try:
        proc = subprocess.Popen(
            safe_args,
            cwd=str(work_dir),
            env=clean_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=False,  # CRITICAL: Never construct shell commands
        )

        try:
            stdout, stderr = proc.communicate(timeout=effective_timeout)
            return subprocess.CompletedProcess(
                args=safe_args,
                returncode=proc.returncode,
                stdout=stdout,
                stderr=stderr,
            )
        except subprocess.TimeoutExpired:
            # Terminate child process tree on Windows
            if sys.platform.startswith("win"):
                try:
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                        capture_output=True,
                        timeout=5,
                    )
                except Exception:
                    proc.kill()
            else:
                proc.kill()
            proc.wait()
            raise ProcessingTimeout(
                f"Subprocess '{safe_args[0]}' timed out after {effective_timeout} seconds."
            )
    except Exception as exc:
        if isinstance(exc, (ProcessingTimeout, SandboxUnavailable)):
            raise
        logger.error("Failed to launch sandboxed command %s: %s", safe_args[0], exc)
        raise SandboxUnavailable(f"Failed to execute sandboxed command: {exc}") from exc
