from __future__ import annotations

import os
import platform
import re
from pathlib import Path

WINDOWS_DRIVE_RE = re.compile(r"^([A-Za-z]):[\\/](.*)$")


def _is_wsl() -> bool:
    if os.name != "posix":
        return False
    rel = platform.release().lower()
    if "microsoft" in rel:
        return True
    try:
        return "microsoft" in Path("/proc/version").read_text(encoding="utf-8", errors="ignore").lower()
    except Exception:
        return False


def normalize_path_string(value: str) -> str:
    raw = (value or "").strip().strip('"').strip("'")
    if not raw:
        return raw
    if os.name == "nt":
        return raw

    m = WINDOWS_DRIVE_RE.match(raw)
    if m:
        drive = m.group(1).lower()
        rest = m.group(2).replace("\\", "/").lstrip("/")
        wsl_path = f"/mnt/{drive}/{rest}"
        if _is_wsl() or Path(f"/mnt/{drive}").exists():
            return wsl_path
    return raw


def normalize_path(path_or_str: str | Path) -> Path:
    return Path(normalize_path_string(str(path_or_str))).expanduser()
