from __future__ import annotations

import logging
from pathlib import Path

from .path_utils import normalize_path

logger = logging.getLogger(__name__)


def read_text_content(path: Path, max_chars: int = 40000) -> str:
    p = normalize_path(path)
    if not p.exists() or not p.is_file():
        logger.warning("Spec file not found: %s", p)
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
