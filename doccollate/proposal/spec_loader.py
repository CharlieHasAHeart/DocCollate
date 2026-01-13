from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Callable


from .utils import read_text


def load_spec_text(path: str) -> str:
    lower = path.lower()
    if lower.endswith(".md") or lower.endswith(".txt"):
        return parse_md(path)
    if lower.endswith(".docx"):
        return parse_docx(path)
    if lower.endswith(".pdf"):
        return parse_pdf(path)
    raise ValueError(f"Unsupported spec format: {path}")


def parse_md(path: str) -> str:
    return read_text(path)


def _require(module_name: str) -> Callable:
    def _raise() -> None:
        raise ImportError(f"Missing dependency: {module_name}")

    return _raise


def parse_docx(path: str) -> str:
    text = _read_docx_via_pandoc(path)
    if text:
        return text
    try:
        from docx import Document
    except Exception:  # pragma: no cover - import error path
        _require("python-docx")()
    doc = Document(path)
    parts = [p.text for p in doc.paragraphs if p.text]
    return "\n".join(parts)


def _read_docx_via_pandoc(path: str, max_chars: int = 40000) -> str:
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            md_path = Path(tmp_dir) / "spec.md"
            result = subprocess.run(
                ["pandoc", path, "-t", "gfm", "-o", str(md_path)],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                return ""
            content = md_path.read_text(encoding="utf-8")
            save_path = _pandoc_save_path(path)
            if save_path:
                try:
                    save_path.parent.mkdir(parents=True, exist_ok=True)
                    save_path.write_text(content, encoding="utf-8")
                except Exception:
                    pass
            return content[:max_chars]
    except Exception:
        return ""


def _pandoc_save_path(path: str) -> Path | None:
    flag = os.getenv("DOCCOLLATE_PANDOC_SAVE_MD", "").strip().lower()
    if flag not in {"1", "true", "yes", "y"}:
        return None
    output_dir = os.getenv("DOCCOLLATE_PANDOC_SAVE_DIR", "").strip()
    source = Path(path)
    if output_dir:
        return (Path(output_dir).expanduser() / f"{source.stem}.md").resolve()
    return source.with_suffix(".md")


def parse_pdf(path: str) -> str:
    try:
        import pdfplumber
    except Exception:  # pragma: no cover - import error path
        _require("pdfplumber")()
    parts: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            if text:
                parts.append(text)
    return "\n".join(parts)
