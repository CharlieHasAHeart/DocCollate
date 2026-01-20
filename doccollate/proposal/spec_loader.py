from __future__ import annotations

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
    return convert_docx_to_md(path)


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
            return content[:max_chars]
    except Exception:
        return ""


def _write_md(path: str, content: str) -> None:
    try:
        out_path = Path(path).with_suffix(".md")
        out_path.write_text(content, encoding="utf-8")
    except Exception:
        pass


def convert_docx_to_md(path: str, max_chars: int = 40000) -> str:
    text = _read_docx_via_pandoc(path, max_chars=max_chars)
    if text:
        _write_md(path, text)
        return text
    try:
        from docx import Document
    except Exception:  # pragma: no cover - import error path
        _require("python-docx")()
    doc = Document(path)
    parts = [p.text for p in doc.paragraphs if p.text]
    content = "\n".join(parts)
    if content:
        _write_md(path, content)
    return content


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
