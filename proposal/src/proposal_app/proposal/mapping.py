from __future__ import annotations

from typing import Any


def format_date_range(start_date: str, end_date: str) -> str:
    s = (start_date or "").strip()
    e = (end_date or "").strip()
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
    context["start_date"] = str(manual_inputs.get("start_date", "")).strip()
    context["end_date"] = str(manual_inputs.get("end_date", "")).strip()


    placeholders = llm_output.get("placeholders", {}) if isinstance(llm_output, dict) else {}
    for key, value in placeholders.items():
        if key.startswith("{{") and key.endswith("}}"):
            clean_key = key.strip("{} ").strip()
            context[clean_key] = value

    tables = llm_output.get("tables", {}) if isinstance(llm_output, dict) else {}
    context["terms"] = tables.get("terms", [])
    context["resources"] = tables.get("resources", [])
    context["milestones"] = tables.get("milestones", [])
    context["references_list"] = tables.get("references_list", [])
    context["risk_register"] = tables.get("risk_register", [])
    milestones = tables.get("milestones", [])
    for idx in range(5):
        row = milestones[idx] if idx < len(milestones) else {}
        num = idx + 1
        context[f"milestone_{num:02d}_phase"] = row.get("phase", "")
        context[f"milestone_{num:02d}_tasks"] = row.get("tasks", "")
        start_date = row.get("start_date", "")
        end_date = row.get("end_date", "")
        time_range = format_date_range(start_date, end_date)
        context[f"milestone_{num:02d}_time"] = time_range
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
    placeholder_map["{{ start_date }}"] = str(manual_inputs.get("start_date", "")).strip()
    placeholder_map["{{ end_date }}"] = str(manual_inputs.get("end_date", "")).strip()


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
        time_range = format_date_range(start_date, end_date)
        placeholder_map[f"{{{{ milestone_{num:02d}_time }}}}"] = time_range
        placeholder_map[f"{{{{ milestone_{num:02d}_start_date }}}}"] = start_date
        placeholder_map[f"{{{{ milestone_{num:02d}_end_date }}}}"] = end_date
        placeholder_map[f"{{{{ milestone_{num:02d}_deliverables }}}}"] = str(row.get("deliverables", ""))

    return placeholder_map
