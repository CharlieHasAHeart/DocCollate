from __future__ import annotations

from typing import Any


def _norm_placeholder_key(key: str) -> str:
    s = key.strip()
    if s.startswith("placeholders."):
        s = s[len("placeholders.") :].strip()
    if not (s.startswith("{{") and s.endswith("}}")):
        return s
    inner = s[2:-2].strip()
    if not inner:
        return s
    return "{{ " + inner + " }}"


def _canonicalize_placeholders(placeholders: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for k, v in placeholders.items():
        if not isinstance(k, str):
            continue
        nk = _norm_placeholder_key(k)
        sv = "" if v is None else (v if isinstance(v, str) else str(v))
        if nk in out:
            # Prefer the non-empty value when duplicates normalize to the same key.
            if (not out[nk].strip()) and sv.strip():
                out[nk] = sv
            continue
        out[nk] = sv
    return out


def apply_doc_rewrite(llm_output: dict[str, Any], fixes: dict[str, Any]) -> dict[str, Any]:
    """
    Apply targeted placeholder rewrites to llm_output.
    Expected fixes format: {"placeholders": {"{{ key }}": "new text"}}.
    """
    if not isinstance(llm_output, dict):
        return llm_output
    placeholders = llm_output.get("placeholders")
    if not isinstance(placeholders, dict):
        return llm_output
    placeholders = _canonicalize_placeholders(placeholders)
    patch = fixes.get("placeholders") if isinstance(fixes, dict) else None
    if isinstance(patch, dict):
        for key, value in patch.items():
            if not isinstance(key, str) or not isinstance(value, str):
                continue
            nk = _norm_placeholder_key(key)
            if nk in placeholders:
                placeholders[nk] = value

    paragraph_fixes = fixes.get("paragraph_fixes") if isinstance(fixes, dict) else None
    if isinstance(paragraph_fixes, list):
        for item in paragraph_fixes:
            if not isinstance(item, dict):
                continue
            key = item.get("key")
            index = item.get("index")
            text = item.get("text")
            if not isinstance(key, str) or not isinstance(index, int) or not isinstance(text, str):
                continue
            nk = _norm_placeholder_key(key)
            current = placeholders.get(nk)
            if not isinstance(current, str):
                continue
            parts = current.split("\n\n")
            if not (0 <= index < len(parts)):
                continue
            parts[index] = text
            placeholders[nk] = "\n\n".join(parts)
    llm_output["placeholders"] = placeholders
    return llm_output


def apply_output_patch(llm_output: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(llm_output, dict) or not isinstance(patch, dict):
        return llm_output

    placeholders = llm_output.get("placeholders")
    if not isinstance(placeholders, dict):
        placeholders = {}
    placeholders = _canonicalize_placeholders(placeholders)
    p_patch = patch.get("placeholders")
    if isinstance(p_patch, dict):
        for k, v in p_patch.items():
            if isinstance(k, str) and isinstance(v, str):
                placeholders[_norm_placeholder_key(k)] = v
    llm_output["placeholders"] = placeholders

    tables = llm_output.get("tables")
    if not isinstance(tables, dict):
        tables = {}
    t_patch = patch.get("tables")
    if isinstance(t_patch, dict):
        for name, rows in t_patch.items():
            if not isinstance(name, str) or not isinstance(rows, list):
                continue
            table_name = name.strip()
            if table_name.startswith("tables."):
                table_name = table_name[len("tables.") :].strip()
            if table_name:
                tables[table_name] = rows
    llm_output["tables"] = tables
    return llm_output
