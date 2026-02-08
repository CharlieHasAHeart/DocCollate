from __future__ import annotations


def sanitize_filename(value: str) -> str:
    unsafe = '<>:"/\\|?*'
    cleaned = "".join(ch for ch in value if ch not in unsafe).strip()
    return cleaned.replace(" ", "")


def build_filename(prefix: str, app_name: str, version: str, suffix: str = ".docx") -> str:
    base = f"{prefix}-{app_name}-{version}"
    return sanitize_filename(base) + suffix
