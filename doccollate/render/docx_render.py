from __future__ import annotations

from typing import Any


def render_with_docxtpl(template_path: str, context: dict[str, Any], out_path: str) -> None:
    try:
        from docxtpl import DocxTemplate
    except Exception as exc:  # pragma: no cover
        raise ImportError("Missing dependency: docxtpl") from exc

    doc = DocxTemplate(template_path)
    doc.render(context)
    doc.save(out_path)
