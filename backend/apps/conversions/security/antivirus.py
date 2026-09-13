"""
Antivirus and malware scanning provider abstraction for VELTO Conversion.

Supports configurable modes:
- disabled: bypass scanning (default for local development)
- optional: attempt scan if provider available, log warning if offline
- required: fail closed if scanner unavailable or malware detected
"""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from django.conf import settings
from apps.conversions.security.exceptions import AntivirusUnavailable, MalwareDetected

logger = logging.getLogger(__name__)


@dataclass
class ScanResult:
    """Dataclass holding antivirus scan status details."""
    clean: bool
    infected: bool
    scanner_name: str
    message: str
    metadata: dict = field(default_factory=dict)


class BaseAntivirusProvider:
    """Abstract base class for antivirus scanner implementations."""

    name: str = "base_provider"

    def is_available(self) -> bool:
        """Check if the antivirus scanner service or binary is reachable."""
        raise NotImplementedError

    def scan_path(self, path: str | Path) -> ScanResult:
        """Perform scan on file at path."""
        raise NotImplementedError


class MockAntivirusProvider(BaseAntivirusProvider):
    """
    Deterministic mock antivirus scanner for unit tests and local verification.

    Detects synthetic test virus signatures (e.g. EICAR or MALWARE_TEST payload string).
    """

    name = "MockAntivirusProvider"

    def __init__(self, available: bool = True):
        self._available = available

    def is_available(self) -> bool:
        return self._available

    def scan_path(self, path: str | Path) -> ScanResult:
        p = Path(path)
        if not p.exists():
            return ScanResult(clean=True, infected=False, scanner_name=self.name, message="File does not exist.")

        try:
            with open(p, "rb") as f:
                content = f.read(4096)
            if b"EICAR" in content or b"MALWARE_TEST" in content:
                return ScanResult(
                    clean=False,
                    infected=True,
                    scanner_name=self.name,
                    message="Malware signature EICAR/MALWARE_TEST detected.",
                )
        except Exception as exc:
            logger.warning("MockAntivirusProvider read error: %s", exc)

        return ScanResult(clean=True, infected=False, scanner_name=self.name, message="Scan clean.")


class ClamAVProvider(BaseAntivirusProvider):
    """
    ClamAV antivirus provider using socket daemon or clamscan CLI.
    """

    name = "ClamAV"

    def is_available(self) -> bool:
        # Check clamd socket or clamscan executable in system PATH
        import shutil
        return shutil.which("clamscan") is not None or shutil.which("clamdscan") is not None

    def scan_path(self, path: str | Path) -> ScanResult:
        import subprocess
        p = Path(path)
        cmd = ["clamscan", "--no-summary", str(p)]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if res.returncode == 0:
                return ScanResult(clean=True, infected=False, scanner_name=self.name, message="Clean")
            elif res.returncode == 1:
                return ScanResult(clean=False, infected=True, scanner_name=self.name, message="Threat detected by ClamAV")
            else:
                return ScanResult(clean=False, infected=False, scanner_name=self.name, message=f"ClamAV scan error: {res.stderr}")
        except Exception as exc:
            return ScanResult(clean=False, infected=False, scanner_name=self.name, message=f"Scanner error: {exc}")


def get_antivirus_provider() -> BaseAntivirusProvider:
    """Return configured antivirus scanner provider instance."""
    provider_type = getattr(settings, "ANTIVIRUS_PROVIDER", os.environ.get("ANTIVIRUS_PROVIDER", "mock")).lower()
    if provider_type == "clamav":
        return ClamAVProvider()
    return MockAntivirusProvider()


def scan_file_security(path: str | Path) -> ScanResult:
    """
    Scan file at path according to configured ANTIVIRUS_MODE (disabled, optional, required).

    Raises
    ------
    MalwareDetected
        If malware/infected payload is found.
    AntivirusUnavailable
        If mode is required but scanner is offline.
    """
    mode = getattr(settings, "ANTIVIRUS_MODE", os.environ.get("ANTIVIRUS_MODE", "disabled")).lower()

    if mode == "disabled":
        return ScanResult(
            clean=True,
            infected=False,
            scanner_name="none",
            message="Antivirus scanning disabled.",
            metadata={"status": "skipped"},
        )

    provider = get_antivirus_provider()
    if not provider.is_available():
        if mode == "required":
            raise AntivirusUnavailable("Antivirus scanning is required but scanner service is offline.")
        logger.warning("Antivirus scanner unavailable in optional mode — proceeding with scan skipped.")
        return ScanResult(
            clean=True,
            infected=False,
            scanner_name=provider.name,
            message="Scanner unavailable (optional mode).",
            metadata={"status": "unavailable"},
        )

    res = provider.scan_path(path)
    if res.infected:
        logger.error("Security alert: Malware detected in file %s by %s", path, res.scanner_name)
        raise MalwareDetected("Security check failed: File contains potentially harmful content or malware.")

    return res
