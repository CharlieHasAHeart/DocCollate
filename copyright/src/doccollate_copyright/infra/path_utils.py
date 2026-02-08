from __future__ import annotations

import os
import platform
import re
from pathlib import Path

WINDOWS_DRIVE_RE = re.compile(r"^([A-Za-z]):[\\/](.*)$")
WINDOWS_UNC_RE = re.compile(r"^\\\\([^\\]+)\\(.+)$")


def _is_wsl() -> bool:
    if os.name != "posix":
        return False
    release = platform.release().lower()
    if "microsoft" in release:
        return True
    try:
        text = Path("/proc/version").read_text(encoding="utf-8", errors="ignore").lower()
    except Exception:
        return False
    return "microsoft" in text


def normalize_path_string(value: str) -> str:
    raw = (value or "").strip().strip('"').strip("'")
    if not raw:
        return raw

    # On native Windows, keep Windows paths as-is.
    if os.name == "nt":
        return raw

    # Convert C:\foo or C:/foo style paths to WSL mount when available.
    drive_match = WINDOWS_DRIVE_RE.match(raw)
    if drive_match:
        drive = drive_match.group(1).lower()
        rest = re.sub(r"/+", "/", drive_match.group(2).replace("\\", "/")).lstrip("/")
        wsl_path = f"/mnt/{drive}/{rest}"
        if _is_wsl() or Path(f"/mnt/{drive}").exists():
            return wsl_path
        return raw

    # Convert UNC path to POSIX-like network path for non-Windows systems.
    unc_match = WINDOWS_UNC_RE.match(raw)
    if unc_match and os.name != "nt":
        host = unc_match.group(1)
        share = unc_match.group(2).replace("\\", "/")
        return f"//{host}/{share}"

    return raw


def normalize_path(path_or_str: str | Path) -> Path:
    if isinstance(path_or_str, Path):
        return Path(normalize_path_string(str(path_or_str))).expanduser()
    return Path(normalize_path_string(path_or_str)).expanduser()
