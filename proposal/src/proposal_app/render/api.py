from __future__ import annotations

from pathlib import Path
from typing import Any


def render_docx_from_maps(
    *,
    template_path: str,
    out_path: str,
    context: dict[str, Any],
    placeholder_map: dict[str, str],
) -> None:
    """
    Stable, single entrypoint for rendering:
    1) docxtpl render (layout/loops/blocks)
    2) placeholder fill (run-safe replacement)
    """
    from .docx_render import render_with_docxtpl
    from .docx_fill import fill_docx

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    tmp_path = out.with_suffix(out.suffix + ".tmp")
    render_with_docxtpl(template_path, context, str(tmp_path))
    fill_docx(str(tmp_path), placeholder_map, out_path)

    try:
        tmp_path.unlink(missing_ok=True)  # py>=3.8
    except Exception:
        pass


def render_docx_from_output(
    *,
    template_path: str,
    out_path: str,
    llm_output: dict[str, Any],
    manual_inputs: dict[str, Any] | None = None,
) -> None:
    """
    High-level stable entrypoint used by pipeline/CLI:
    - Builds context + placeholder_map using current mapping logic
    - Renders docx using render_docx_from_maps()
    """
    # Local imports to avoid import cycles and keep render layer stable.
    from ..proposal.mapping import build_context, build_placeholder_map

    inputs = manual_inputs or {}
    context = build_context(inputs, llm_output)
    placeholder_map = build_placeholder_map(inputs, llm_output)

    render_docx_from_maps(
        template_path=template_path,
        out_path=out_path,
        context=context,
        placeholder_map=placeholder_map,
    )
