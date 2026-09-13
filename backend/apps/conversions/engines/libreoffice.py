"""
LibreOffice conversion utilities & shared subprocess orchestration.

Provides:
  - find_libreoffice_executable(): Discovers soffice via LIBREOFFICE_PATH, PATH, and standard Windows paths.
  - run_libreoffice_pdf_conversion(): Core subprocess execution with isolated working directory,
    isolated user profile (-env:UserInstallation), timeout enforcement, exit code validation,
    missing output check, PyMuPDF output validation, and output copy.
"""

import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from apps.conversions.engines.base import ConversionError
from apps.conversions.engines.validators import validate_pdf_output

logger = logging.getLogger(__name__)


def find_libreoffice_executable() -> str | None:
    """
    Locate the LibreOffice executable (`soffice`).

    Discovery order:
    1. `LIBREOFFICE_PATH` environment variable, if provided and valid.
    2. `soffice` available through PATH.
    3. Windows default installation path:
       `C:\\Program Files\\LibreOffice\\program\\soffice.exe`
    4. Windows alternative path:
       `C:\\Program Files (x86)\\LibreOffice\\program\\soffice.exe`

    Returns
    -------
    str | None
        Absolute path to soffice executable, or None if not found.
    """
    # 1. LIBREOFFICE_PATH env var
    env_path = os.environ.get("LIBREOFFICE_PATH")
    if env_path and Path(env_path).is_file():
        return env_path

    # 2. soffice available on PATH
    path_exe = shutil.which("soffice") or shutil.which("soffice.exe")
    if path_exe and Path(path_exe).is_file():
        return path_exe

    # 3. Standard Windows 64-bit install path
    win_path1 = Path(r"C:\Program Files\LibreOffice\program\soffice.exe")
    if win_path1.is_file():
        return str(win_path1)

    # 4. Standard Windows 32-bit install path
    win_path2 = Path(r"C:\Program Files (x86)\LibreOffice\program\soffice.exe")
    if win_path2.is_file():
        return str(win_path2)

    return None


def run_libreoffice_pdf_conversion(
    input_path: str, output_path: str, format_label: str = "DOCX"
) -> None:
    """
    Convert an Office document (DOCX, PPTX, etc.) to PDF using LibreOffice headless mode.

    Parameters
    ----------
    input_path : str
        Absolute path to input Office document.
    output_path : str
        Absolute destination path for converted PDF.
    format_label : str
        Label used in error logging and exception messages (e.g. "DOCX", "PPTX").

    Raises
    ------
    ConversionError
        On missing executable, timeout, non-zero exit code, missing PDF output, or invalid PDF.
    """
    # 1. Discover LibreOffice executable
    exe_path = find_libreoffice_executable()
    if not exe_path:
        raise ConversionError(
            f"LibreOffice is not installed or could not be found. "
            f"Please install LibreOffice to convert {format_label} files to PDF."
        )

    # 2. Confirm input existence
    in_p = Path(input_path)
    if not in_p.exists():
        raise ConversionError(f"The uploaded {format_label} file does not exist.")

    # 3. Read timeout setting
    try:
        timeout = int(os.environ.get("LIBREOFFICE_TIMEOUT", "60"))
    except ValueError:
        timeout = 60

    # 4. Perform conversion inside isolated temp directory & user profile
    prefix = f"velto_{format_label.lower()}2pdf_"
    with tempfile.TemporaryDirectory(prefix=prefix, ignore_cleanup_errors=True) as tmp_dir_str:

        tmp_dir = Path(tmp_dir_str)
        out_dir = tmp_dir / "out"
        out_dir.mkdir(parents=True, exist_ok=True)
        profile_dir = tmp_dir / "profile"
        profile_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            exe_path,
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(out_dir.resolve()),
            f"-env:UserInstallation={profile_dir.resolve().as_uri()}",
            str(in_p.resolve()),
        ]

        logger.info("Running LibreOffice conversion command: %s", " ".join(cmd))

        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            logger.error("LibreOffice conversion timed out after %d seconds.", timeout)
            raise ConversionError("LibreOffice conversion timed out.") from exc
        except Exception as exc:
            logger.exception("Subprocess execution error running LibreOffice")
            raise ConversionError(
                f"LibreOffice failed to convert the {format_label} file to PDF: {exc}"
            ) from exc

        if res.returncode != 0:
            logger.error(
                "LibreOffice returned non-zero exit code %d for %s: stdout=%s stderr=%s",
                res.returncode,
                input_path,
                res.stdout,
                res.stderr,
            )
            raise ConversionError(f"LibreOffice failed to convert the {format_label} file to PDF.")

        expected_pdf_name = f"{in_p.stem}.pdf"
        gen_pdf = out_dir / expected_pdf_name
        if not gen_pdf.exists():
            logger.error("LibreOffice finished but output file missing: %s", gen_pdf)
            raise ConversionError("LibreOffice did not produce a PDF output file.")

        # 5. Validate generated PDF
        validate_pdf_output(str(gen_pdf))

        # 6. Copy output to destination
        out_dest = Path(output_path)
        out_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(gen_pdf, out_dest)
