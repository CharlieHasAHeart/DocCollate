from __future__ import annotations


def sanitize_filename(value: str) -> str:
    unsafe = '<>:"/\\|?*'
    cleaned = "".join(ch for ch in value if ch not in unsafe).strip()
    return cleaned.replace(" ", "")


def ensure_short_name(name: str) -> str:
    cleaned = sanitize_filename(name)
    if len(cleaned) > 64:
        return cleaned[:64]
    return cleaned


def build_copyright_filename(software_name: str, version: str) -> str:
    base = f"软件著作权登记申请表-{software_name}-{version}"
    return ensure_short_name(base) + ".docx"
