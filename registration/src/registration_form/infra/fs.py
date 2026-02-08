from __future__ import annotations

import logging
import re
from pathlib import Path

import yaml

from .path_utils import normalize_path

logger = logging.getLogger(__name__)


def load_yaml_config(path: Path) -> dict:
    p = normalize_path(path)
    if not p.exists():
        logger.warning("YAML config not found: %s", p)
        return {}
    try:
        return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        logger.error("Failed to load YAML %s: %s", p, exc)
        return {}


def read_text_content(path: Path, max_chars: int = 40000) -> str:
    p = normalize_path(path)
    if not p.exists() or not p.is_file():
        return ""
    ext = p.suffix.lower()
    try:
        if ext == ".md":
            return p.read_text(encoding="utf-8")[:max_chars]
        if ext == ".docx":
            from docx import Document

            doc = Document(p)
            parts = [para.text.strip() for para in doc.paragraphs if para.text.strip()]
            return "\n".join(parts)[:max_chars]
    except Exception as exc:
        logger.warning("Failed to read spec text from %s: %s", p, exc)
    return ""


def detect_dev_lang(source_text: str) -> str:
    text = (source_text or "").lower()
    langs: list[str] = []
    mapping = [
        (r"typescript|\bts\b", "TypeScript"),
        (r"javascript|\bjs\b", "JavaScript"),
        (r"python", "Python"),
        (r"java", "Java"),
        (r"c\+\+", "C++"),
        (r"c#|\.net", "C#/.NET"),
        (r"golang|\bgo\b", "Go"),
        (r"rust", "Rust"),
    ]
    for pattern, name in mapping:
        if re.search(pattern, text):
            langs.append(name)
    return "/".join(dict.fromkeys(langs)) if langs else "待补充"


def detect_platform(source_text: str) -> str:
    text = (source_text or "").lower()
    parts: list[str] = []
    if "windows" in text:
        parts.append("Windows 10/11")
    if "linux" in text or "ubuntu" in text or "centos" in text:
        parts.append("Linux")
    if "macos" in text or "mac os" in text:
        parts.append("macOS")
    if "android" in text:
        parts.append("Android")
    if "ios" in text:
        parts.append("iOS")
    return "、".join(dict.fromkeys(parts)) if parts else "待补充"
