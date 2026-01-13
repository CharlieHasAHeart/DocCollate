from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any

from ..proposal.chunking import chunk_text
from ..render.docx_fill import fill_docx
from ..render.docx_render import render_with_docxtpl
from ..llm.api import build_prompt, call_llm, translate_to_english
from ..proposal.mapping import build_context, build_placeholder_map
from ..proposal.retrieval import retrieve_all_fields
from ..proposal.spec_loader import load_spec_text
from ..proposal.utils import ensure_dir, read_json
from ..proposal.validate import auto_fix, validate_schema
from ..config import AppConfig
from ..llm.client import LLMRuntime
from ..core.date_utils import default_assess_dates
from ..core.form_pipeline import apply_app_metadata, build_form_data
from ..core.input_flow import prompt_text


def add_proposal_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--spec", required=False, help="Spec file path (.md/.docx/.pdf)")
    parser.add_argument("--manual", required=False, help="Manual input JSON path")
    parser.add_argument("--out", required=False, help="Output directory path")
    parser.add_argument("--topk", type=int, default=None, help="BM25 Top-K (default 8)")
    parser.add_argument("--debug", action="store_true", help="Write debug output")
    parser.add_argument("--dry-run", action="store_true", help="Do not write docx")
    parser.add_argument("--strict", action="store_true", help="Fail if validation errors")


def _exit(code: int, message: str) -> int:
    print(f"[Error] {message}", file=sys.stderr)
    return code


def _prompt_cover(runtime: LLMRuntime) -> dict[str, str]:
    company_name = prompt_text("Company name").strip()
    project_name = prompt_text("Project name").strip()
    if not project_name:
        project_name = prompt_text("Project name (required)").strip()
    try:
        english_name = translate_to_english(project_name, runtime)
    except Exception:
        english_name = ""
    if not english_name or re.search(r"[\u4e00-\u9fff]", english_name):
        english_name = prompt_text("Project English name (for document title)").strip()
    document_title = f"{english_name} Project Proposal".strip()
    return {
        "company_name": company_name,
        "project_name": project_name,
        "project_id": "",
        "document_title": document_title,
        "document_version": "V1.0",
        "drafted_by": "",
        "draft_date": "",
        "approved_by": "",
        "approval_date": "",
    }


def _build_cover_from_inputs(
    runtime: LLMRuntime,
    company_name: str,
    project_name: str,
) -> dict[str, str] | None:
    if not company_name or not project_name:
        return None
    try:
        english_name = translate_to_english(project_name, runtime)
    except Exception:
        english_name = ""
    if not english_name or re.search(r"[\u4e00-\u9fff]", english_name):
        english_name = project_name
    document_title = f"{english_name} Project Proposal".strip()
    return {
        "company_name": company_name,
        "project_name": project_name,
        "project_id": "",
        "document_title": document_title,
        "document_version": "V1.0",
        "drafted_by": "",
        "draft_date": "",
        "approved_by": "",
        "approval_date": "",
    }


def _prompt_revision_history() -> list[dict[str, str]]:
    print("[Info] Revision history (1 row)")
    return [
        {
            "version": "V1.0",
            "date": "",
            "status": "C",
            "author": "",
            "summary": "",
        }
    ]


def _prompt_signoff_records() -> list[dict[str, str]]:
    print("[Info] Sign-off records (4 rows)")
    records: list[dict[str, str]] = []
    for _ in range(4):
        records.append(
            {
                "role": "",
                "name": "",
                "date": "",
                "comment": "",
            }
        )
    return records


def generate_proposal(
    args: argparse.Namespace,
    app_config: AppConfig,
    runtime: LLMRuntime,
    cover_overrides: dict[str, str] | None = None,
) -> int:
    template_path = app_config.templates.proposal
    if not template_path:
        return _exit(2, "templates.proposal missing in pyproject.toml")

    if not args.out:
        return _exit(2, "missing output directory")
    out_dir = args.out
    os.makedirs(out_dir, exist_ok=True)

    if not args.spec:
        return _exit(2, "missing spec path")

    try:
        spec_text = load_spec_text(args.spec)
    except FileNotFoundError:
        return _exit(2, f"spec file not found: {args.spec}")
    except Exception as exc:
        return _exit(2, f"failed to read spec: {exc}")

    data = build_form_data(spec_text, runtime, dates_config=app_config.dates)
    apply_app_metadata(data, args.applicant_type, args.app_name, args.app_version)

    manual_inputs: dict[str, Any]
    if args.manual:
        try:
            manual_inputs = read_json(args.manual)
        except FileNotFoundError:
            return _exit(2, f"manual file not found: {args.manual}")
        except json.JSONDecodeError:
            return _exit(2, f"manual file invalid JSON: {args.manual}")
    else:
        cover = None
        if cover_overrides:
            cover = _build_cover_from_inputs(
                runtime,
                str(cover_overrides.get("company_name", "")).strip(),
                str(cover_overrides.get("project_name", "")).strip(),
            )
        manual_inputs = {
            "cover": cover or _prompt_cover(runtime),
            "revision_history": _prompt_revision_history(),
            "signoff_records": _prompt_signoff_records(),
        }

    completion_date, dev_date = default_assess_dates(
        completion_days_ago=app_config.dates.assess_completion_days_ago,
        dev_months_ago=app_config.dates.assess_dev_months_ago,
    )
    manual_inputs["schedule"] = {
        "start_date": dev_date,
        "end_date": completion_date,
    }

    topk = args.topk if args.topk is not None else app_config.proposal.topk_default
    chunks = chunk_text(spec_text)
    evidence = retrieve_all_fields(chunks, topk_default=topk)

    prompt = build_prompt(manual_inputs, evidence)
    try:
        llm_output = call_llm(prompt, runtime)
    except Exception as exc:
        return _exit(3, f"LLM call failed: {exc}")

    errors = validate_schema(llm_output)
    if errors:
        if args.strict:
            return _exit(3, "schema validation failed: " + "; ".join(errors))
        llm_output = auto_fix(llm_output, runtime, field_evidence=evidence)
        errors = validate_schema(llm_output)
        if errors:
            return _exit(3, "schema validation failed after auto-fix: " + "; ".join(errors))

    context = build_context(manual_inputs, llm_output)
    placeholder_map = build_placeholder_map(manual_inputs, llm_output)
    project_name = placeholder_map.get("{{ project_name }}", "").strip()
    if not project_name:
        project_name = prompt_text("Project name (required for file name)").strip()
        placeholder_map["{{ project_name }}"] = project_name
    out_path = os.path.join(out_dir, f"{project_name}立项建议书.docx")
    tmp_rendered_path = os.path.join(out_dir, "_tmp_rendered.docx")

    if args.debug:
        ensure_dir("debug")
        with open("debug/evidence.json", "w", encoding="utf-8") as f:
            json.dump(evidence, f, ensure_ascii=False, indent=2)
        with open("debug/llm_output.json", "w", encoding="utf-8") as f:
            json.dump(llm_output, f, ensure_ascii=False, indent=2)
        with open("debug/placeholder_map.json", "w", encoding="utf-8") as f:
            json.dump(placeholder_map, f, ensure_ascii=False, indent=2)

    if args.dry_run:
        print(json.dumps(placeholder_map, ensure_ascii=False, indent=2))
        return 0

    try:
        render_with_docxtpl(str(template_path), context, tmp_rendered_path)
    except Exception as exc:
        return _exit(4, f"docxtpl render failed: {exc}")

    try:
        fill_docx(tmp_rendered_path, placeholder_map, out_path)
    except Exception as exc:
        return _exit(4, f"fill_docx failed: {exc}")

    try:
        os.remove(tmp_rendered_path)
    except OSError:
        pass

    print(f"[Output] Generated file: {out_path}")
    return 0
