from __future__ import annotations

from datetime import datetime
from typing import Any


def _parse_date(s: str) -> datetime | None:
    s = (s or "").strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def format_date_range(start_date: str, end_date: str) -> str:
    s = (start_date or "").strip()
    e = (end_date or "").strip()
    if not s and not e:
        return ""
    ds = _parse_date(s)
    de = _parse_date(e)
    if ds:
        s = ds.strftime("%Y-%m-%d")
    if de:
        e = de.strftime("%Y-%m-%d")
    if ds and de:
        days = (de - ds).days + 1
        if days >= 1:
            return f"{s} ~ {e}（{days}天）"
    if s and e:
        return f"{s} ~ {e}"
    return s or e


def build_context(manual_inputs: dict[str, Any], llm_output: dict[str, Any]) -> dict[str, Any]:
    context: dict[str, Any] = {}
    cover = manual_inputs.get("cover", {}) if isinstance(manual_inputs, dict) else {}
    context.update(
        {
            "company_name": cover.get("company_name", ""),
            "project_name": cover.get("project_name", ""),
            "project_id": cover.get("project_id", ""),
            "document_title": cover.get("document_title", ""),
            "document_version": cover.get("document_version", ""),
            "drafted_by": cover.get("drafted_by", ""),
            "draft_date": cover.get("draft_date", ""),
            "approved_by": cover.get("approved_by", ""),
            "approval_date": cover.get("approval_date", ""),
        }
    )

    revision_history = manual_inputs.get("revision_history", []) if isinstance(manual_inputs, dict) else []
    context["revision_history"] = revision_history
    for idx in range(4):
        rev = revision_history[idx] if idx < len(revision_history) else {}
        num = idx + 1
        context[f"revision_{num:02d}_version"] = rev.get("version", "")
        context[f"revision_{num:02d}_date"] = rev.get("date", "")
        context[f"revision_{num:02d}_status"] = rev.get("status", "")
        context[f"revision_{num:02d}_author"] = rev.get("author", "")
        context[f"revision_{num:02d}_summary"] = rev.get("summary", "")

    signoffs = manual_inputs.get("signoff_records", []) if isinstance(manual_inputs, dict) else []
    context["signoff_records"] = signoffs
    for idx in range(4):
        record = signoffs[idx] if idx < len(signoffs) else {}
        num = idx + 1
        context[f"signoff_{num:02d}_role"] = record.get("role", "")
        context[f"signoff_{num:02d}_name"] = record.get("name", "")
        context[f"signoff_{num:02d}_date"] = record.get("date", "")
        context[f"signoff_{num:02d}_comment"] = record.get("comment", "")

    placeholders = llm_output.get("placeholders", {}) if isinstance(llm_output, dict) else {}
    for key, value in placeholders.items():
        if key.startswith("{{") and key.endswith("}}"):
            clean_key = key.strip("{} ").strip()
            context[clean_key] = value

    tables = llm_output.get("tables", {}) if isinstance(llm_output, dict) else {}
    context["terms"] = tables.get("terms", [])
    context["resources"] = tables.get("resources", [])
    context["costs"] = tables.get("costs", [])
    context["milestones"] = tables.get("milestones", [])
    milestones = tables.get("milestones", [])
    for idx in range(5):
        row = milestones[idx] if idx < len(milestones) else {}
        num = idx + 1
        context[f"milestone_{num:02d}_phase"] = row.get("phase", "")
        context[f"milestone_{num:02d}_tasks"] = row.get("tasks", "")
        start_date = row.get("start_date", "")
        end_date = row.get("end_date", "")
        context[f"milestone_{num:02d}_time"] = format_date_range(start_date, end_date)
        context[f"milestone_{num:02d}_start_date"] = start_date
        context[f"milestone_{num:02d}_end_date"] = end_date
        context[f"milestone_{num:02d}_deliverables"] = row.get("deliverables", "")
    return context


def build_placeholder_map(manual_inputs: dict[str, Any], llm_output: dict[str, Any]) -> dict[str, str]:
    placeholder_map: dict[str, str] = {}

    cover = manual_inputs.get("cover", {}) if isinstance(manual_inputs, dict) else {}
    cover_map = {
        "{{ company_name }}": cover.get("company_name", ""),
        "{{ project_name }}": cover.get("project_name", ""),
        "{{ project_id }}": cover.get("project_id", ""),
        "{{ document_title }}": cover.get("document_title", ""),
        "{{ document_version }}": cover.get("document_version", ""),
        "{{ drafted_by }}": cover.get("drafted_by", ""),
        "{{ draft_date }}": cover.get("draft_date", ""),
        "{{ approved_by }}": cover.get("approved_by", ""),
        "{{ approval_date }}": cover.get("approval_date", ""),
    }
    placeholder_map.update({k: str(v) for k, v in cover_map.items()})

    revision_history = manual_inputs.get("revision_history", []) if isinstance(manual_inputs, dict) else []
    for idx in range(4):
        rev = revision_history[idx] if idx < len(revision_history) else {}
        num = idx + 1
        placeholder_map[f"{{{{ revision_{num:02d}_version }}}}"] = str(rev.get("version", ""))
        placeholder_map[f"{{{{ revision_{num:02d}_date }}}}"] = str(rev.get("date", ""))
        placeholder_map[f"{{{{ revision_{num:02d}_status }}}}"] = str(rev.get("status", ""))
        placeholder_map[f"{{{{ revision_{num:02d}_author }}}}"] = str(rev.get("author", ""))
        placeholder_map[f"{{{{ revision_{num:02d}_summary }}}}"] = str(rev.get("summary", ""))

    signoffs = manual_inputs.get("signoff_records", []) if isinstance(manual_inputs, dict) else []
    for idx in range(4):
        record = signoffs[idx] if idx < len(signoffs) else {}
        num = idx + 1
        placeholder_map[f"{{{{ signoff_{num:02d}_role }}}}"] = str(record.get("role", ""))
        placeholder_map[f"{{{{ signoff_{num:02d}_name }}}}"] = str(record.get("name", ""))
        placeholder_map[f"{{{{ signoff_{num:02d}_date }}}}"] = str(record.get("date", ""))
        placeholder_map[f"{{{{ signoff_{num:02d}_comment }}}}"] = str(record.get("comment", ""))

    placeholders = llm_output.get("placeholders", {}) if isinstance(llm_output, dict) else {}
    for key, value in placeholders.items():
        placeholder_map[key] = str(value)

    tables = llm_output.get("tables", {}) if isinstance(llm_output, dict) else {}

    milestones = tables.get("milestones", [])
    for idx in range(5):
        row = milestones[idx] if idx < len(milestones) else {}
        num = idx + 1
        placeholder_map[f"{{{{ milestone_{num:02d}_phase }}}}"] = str(row.get("phase", ""))
        placeholder_map[f"{{{{ milestone_{num:02d}_tasks }}}}"] = str(row.get("tasks", ""))
        start_date = str(row.get("start_date", ""))
        end_date = str(row.get("end_date", ""))
        placeholder_map[f"{{{{ milestone_{num:02d}_time }}}}"] = format_date_range(start_date, end_date)
        placeholder_map[f"{{{{ milestone_{num:02d}_start_date }}}}"] = start_date
        placeholder_map[f"{{{{ milestone_{num:02d}_end_date }}}}"] = end_date
        placeholder_map[f"{{{{ milestone_{num:02d}_deliverables }}}}"] = str(row.get("deliverables", ""))

    return placeholder_map
