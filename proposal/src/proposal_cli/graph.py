from __future__ import annotations

from typing import Any, Callable, TypedDict, Annotated
import logging
import copy
import re
import operator
from datetime import datetime


from langgraph.graph import END, StateGraph

from proposal_app.llm.api import (
    build_doc_rewrite_combined_prompt,
    build_full_prompt,
    build_ledger_fix_prompt,
    build_ledger_prompt,
    build_missing_patch_prompt,
    build_section_prompt,
    call_llm,
    call_llm_ledger,
    call_llm_doc_rewrite_combined,
    call_llm_missing_patch,
)
from proposal_app.llm.client import LLMRuntime
from proposal_app.proposal.cluster_defs import (
    build_empty_output,
    PLACEHOLDER_FIELDS,
    TABLE_MIN_SPECS,
)
from proposal_app.proposal.doc_rewrite import apply_doc_rewrite, apply_output_patch
from proposal_app.proposal.ledger_mapping import build_ledger_scope
from proposal_app.proposal.postprocess import postprocess_llm_output
from proposal_app.proposal.table_generators import build_milestones_table, build_risk_register_table
from proposal_app.proposal.rules_engine import (
    PipelineContext,
    RULES,
    Stage,
    compute_soft_metrics,
    run_rules,
)

logger = logging.getLogger(__name__)


class ProposalState(TypedDict, total=False):
    spec_text: str
    manual_inputs: dict[str, Any]
    ledger: dict[str, Any]
    llm_output: dict[str, Any]
    section_outputs: Annotated[list[dict[str, Any]], operator.add]
    metrics: dict[str, Any]
    required_placeholders: list[str]
    required_tables: list[str]
    locked_placeholders: dict[str, str]
    locked_tables: dict[str, list[dict[str, str]]]
    missing_fields: list[str]
    needs_patch: bool
    patch_rounds: int


_LEDGER_EXTRA_PATHS = (
    ("references",),
)

MAX_GATE_REPAIR = 2
MAX_REWRITE = 2


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


def _is_empty_rows(rows: Any) -> bool:
    if not isinstance(rows, list) or not rows:
        return True
    for row in rows:
        if not isinstance(row, dict):
            continue
        if any(str(v).strip() for v in row.values() if isinstance(v, str)):
            return False
    return True


def _update_locked_output(
    *,
    llm_output: dict[str, Any],
    required_placeholders: list[str],
    required_tables: list[str],
    locked_placeholders: dict[str, str],
    locked_tables: dict[str, list[dict[str, str]]],
) -> tuple[dict[str, str], dict[str, list[dict[str, str]]]]:
    placeholders = llm_output.get("placeholders", {})
    if isinstance(placeholders, dict):
        for key in required_placeholders:
            nk = _norm_placeholder_key(key)
            if nk in locked_placeholders:
                continue
            val = placeholders.get(nk)
            if isinstance(val, str) and val.strip():
                locked_placeholders[nk] = val

    tables = llm_output.get("tables", {})
    if isinstance(tables, dict):
        for name in required_tables:
            if name in locked_tables:
                continue
            rows = tables.get(name)
            if isinstance(rows, list) and not _is_empty_rows(rows):
                locked_tables[name] = copy.deepcopy(rows)
    return locked_placeholders, locked_tables


def _apply_locked_output(
    llm_output: dict[str, Any],
    locked_placeholders: dict[str, str],
    locked_tables: dict[str, list[dict[str, str]]],
) -> dict[str, Any]:
    if not isinstance(llm_output, dict):
        return llm_output
    placeholders = llm_output.get("placeholders")
    if not isinstance(placeholders, dict):
        placeholders = {}
    for key, value in locked_placeholders.items():
        placeholders[key] = value
    llm_output["placeholders"] = placeholders

    tables = llm_output.get("tables")
    if not isinstance(tables, dict):
        tables = {}
    for name, rows in locked_tables.items():
        tables[name] = copy.deepcopy(rows)
    llm_output["tables"] = tables
    return llm_output


def _apply_ledger_overrides(ledger: dict[str, Any], llm_output: dict[str, Any]) -> dict[str, Any]:
    # Placeholder for future ledger-to-doc overrides; kept as no-op for now.
    return llm_output


def _extract_first_int(text: str) -> int | None:
    if not text:
        return None
    match = re.search(r"(\d+)", text)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def _extract_percent(text: str) -> float | None:
    if not text:
        return None
    match = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
    if not match:
        return None
    try:
        return float(match.group(1)) / 100.0
    except ValueError:
        return None


def _format_wan(value_yuan: float) -> str:
    if value_yuan <= 0:
        return ""
    return f"{int(round(value_yuan / 10000.0))}万"


def _next_year_jan_1(date_text: str) -> str:
    if not date_text:
        return ""
    try:
        dt = datetime.strptime(date_text, "%Y-%m-%d")
    except ValueError:
        return ""
    return f"{dt.year + 1}-01-01"


def _normalize_org_structure(ledger: dict[str, Any]) -> dict[str, Any]:
    return ledger


def _apply_schedule_overrides(ledger: dict[str, Any], manual_inputs: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(ledger, dict) or not isinstance(manual_inputs, dict):
        return ledger
    start_date = str(manual_inputs.get("start_date", "")).strip()
    end_date = str(manual_inputs.get("end_date", "")).strip()
    if not start_date and not end_date:
        return ledger
    delivery_window = ledger.get("delivery_window")
    if not isinstance(delivery_window, dict):
        delivery_window = {}
    if start_date:
        delivery_window["start"] = start_date
    if end_date:
        delivery_window["end"] = end_date
    ledger["delivery_window"] = delivery_window
    return ledger


def _unlock_from_issues(
    issues: list[dict[str, Any]],
    locked_placeholders: dict[str, str],
    locked_tables: dict[str, list[dict[str, str]]],
) -> None:
    for it in issues:
        if not isinstance(it, dict):
            continue
        location = str(it.get("location") or "")
        if not location:
            continue
        if location.startswith("placeholders."):
            key = location[len("placeholders.") :].split("#", 1)[0]
            key = _norm_placeholder_key(key)
            locked_placeholders.pop(key, None)
        elif location.startswith("tables."):
            table = location[len("tables.") :].split("[", 1)[0].split(".", 1)[0]
            if table:
                locked_tables.pop(table, None)


def _ledger_node(ledger_runtime: LLMRuntime) -> Callable[[ProposalState], dict[str, Any]]:
    def _node(state: ProposalState) -> dict[str, Any]:
        logger.info("[Step] Ledger generation")
        spec_text = str(state.get("spec_text", ""))
        manual_inputs = state.get("manual_inputs", {})
        prompt = build_ledger_prompt(spec_text, manual_inputs)
        ledger = call_llm_ledger(prompt, ledger_runtime)
        if isinstance(ledger, dict):
            ledger = _normalize_org_structure(ledger)
            ledger = _apply_schedule_overrides(ledger, manual_inputs)
        return {
            "ledger": ledger,
            "metrics": {
                "llm_calls": 1,
                "gate_rounds": 0,
                "gate_repair_count": 0,
                "rewrite_rounds": 0,
                "rewrite_repair_count": 0,
                "patch_rounds": 0,
                "gate_first_pass": False,
                "post_first_pass": False,
                "rewrite_success_first_try": False,
                "issues_by_rule_first_gate": {},
                "issues_by_rule_first_post": {},
            },
            "missing_fields": [],
            "needs_patch": False,
            "patch_rounds": 0,
        }

    return _node


def _filter_section_output(
    llm_output: dict[str, Any],
    focus_placeholders: list[str],
    focus_tables: list[str],
) -> dict[str, Any]:
    out: dict[str, Any] = {"placeholders": {}, "tables": {}}
    placeholders = llm_output.get("placeholders", {}) if isinstance(llm_output, dict) else {}
    if isinstance(placeholders, dict):
        for key in focus_placeholders:
            nk = _norm_placeholder_key(key)
            val = placeholders.get(nk, "")
            if isinstance(val, str) and val.strip():
                out["placeholders"][nk] = val
    tables = llm_output.get("tables", {}) if isinstance(llm_output, dict) else {}
    if isinstance(tables, dict):
        for name in focus_tables:
            rows = tables.get(name)
            if isinstance(rows, list) and not _is_empty_rows(rows):
                out["tables"][name] = copy.deepcopy(rows)
    return out


def _generate_section_node(
    final_runtime: LLMRuntime,
    focus_placeholders: list[str],
    focus_tables: list[str],
) -> Callable[[ProposalState], dict[str, Any]]:
    def _node(state: ProposalState) -> dict[str, Any]:
        ledger = state.get("ledger", {})
        manual_inputs = state.get("manual_inputs", {})
        spec_text = str(state.get("spec_text", ""))
        full_schema = build_empty_output()
        prompt = build_section_prompt(
            manual_inputs,
            spec_text=spec_text,
            ledger=ledger,
            full_schema=full_schema,
            focus_placeholders=focus_placeholders,
            focus_tables=focus_tables,
        )
        llm_output = call_llm(prompt, final_runtime)
        partial = _filter_section_output(
            llm_output if isinstance(llm_output, dict) else {},
            focus_placeholders=focus_placeholders,
            focus_tables=focus_tables,
        )
        return {"section_outputs": [partial]}

    return _node


def _merge_sections_node() -> Callable[[ProposalState], dict[str, Any]]:
    def _node(state: ProposalState) -> dict[str, Any]:
        logger.info("[Step] Merge section outputs")
        metrics = state.get("metrics", {}).copy()
        required_placeholders = state.get("required_placeholders", [])
        required_tables = state.get("required_tables", [])
        locked_placeholders = state.get("locked_placeholders", {})
        locked_tables = state.get("locked_tables", {})
        if not isinstance(locked_placeholders, dict):
            locked_placeholders = {}
        if not isinstance(locked_tables, dict):
            locked_tables = {}

        outputs = state.get("section_outputs", [])
        merged = build_empty_output()
        placeholders = merged.get("placeholders", {})
        tables = merged.get("tables", {})
        if not isinstance(placeholders, dict):
            placeholders = {}
        if not isinstance(tables, dict):
            tables = {}

        if isinstance(outputs, list):
            for part in outputs:
                if not isinstance(part, dict):
                    continue
                part_placeholders = part.get("placeholders", {})
                if isinstance(part_placeholders, dict):
                    for k, v in part_placeholders.items():
                        nk = _norm_placeholder_key(k)
                        if nk in placeholders and placeholders[nk].strip():
                            continue
                        if isinstance(v, str) and v.strip():
                            placeholders[nk] = v
                part_tables = part.get("tables", {})
                if isinstance(part_tables, dict):
                    for name, rows in part_tables.items():
                        if name in tables and not _is_empty_rows(tables.get(name)):
                            continue
                        if isinstance(rows, list) and not _is_empty_rows(rows):
                            tables[name] = copy.deepcopy(rows)

        merged["placeholders"] = placeholders
        merged["tables"] = tables
        locked_placeholders, locked_tables = _update_locked_output(
            llm_output=merged,
            required_placeholders=required_placeholders if isinstance(required_placeholders, list) else [],
            required_tables=required_tables if isinstance(required_tables, list) else [],
            locked_placeholders=locked_placeholders,
            locked_tables=locked_tables,
        )
        merged = _apply_locked_output(merged, locked_placeholders, locked_tables)

        metrics["llm_calls"] = metrics.get("llm_calls", 0) + (len(outputs) if isinstance(outputs, list) else 0)
        return {
            "llm_output": merged,
            "metrics": metrics,
            "locked_placeholders": locked_placeholders,
            "locked_tables": locked_tables,
        }

    return _node


def _generate_node(final_runtime: LLMRuntime) -> Callable[[ProposalState], dict[str, Any]]:
    def _node(state: ProposalState) -> dict[str, Any]:
        logger.info("[Step] Document generation")
        ledger = state.get("ledger", {})
        manual_inputs = state.get("manual_inputs", {})
        metrics = state.get("metrics", {}).copy()
        spec_text = str(state.get("spec_text", ""))
        full_schema = build_empty_output()
        prompt = build_full_prompt(
            manual_inputs,
            spec_text=spec_text,
            ledger=ledger,
            full_schema=full_schema,
        )
        llm_output = call_llm(prompt, final_runtime)
        metrics["llm_calls"] = metrics.get("llm_calls", 0) + 1
        required_placeholders = state.get("required_placeholders", [])
        required_tables = state.get("required_tables", [])
        locked_placeholders = state.get("locked_placeholders", {})
        locked_tables = state.get("locked_tables", {})
        if not isinstance(locked_placeholders, dict):
            locked_placeholders = {}
        if not isinstance(locked_tables, dict):
            locked_tables = {}
        locked_placeholders, locked_tables = _update_locked_output(
            llm_output=llm_output if isinstance(llm_output, dict) else {},
            required_placeholders=required_placeholders if isinstance(required_placeholders, list) else [],
            required_tables=required_tables if isinstance(required_tables, list) else [],
            locked_placeholders=locked_placeholders,
            locked_tables=locked_tables,
        )
        if isinstance(llm_output, dict):
            llm_output = _apply_locked_output(llm_output, locked_placeholders, locked_tables)
        return {
            "llm_output": llm_output,
            "metrics": metrics,
            "locked_placeholders": locked_placeholders,
            "locked_tables": locked_tables,
        }

    return _node


def _gate_node(ledger_runtime: LLMRuntime) -> Callable[[ProposalState], dict[str, Any]]:
    def _node(state: ProposalState) -> dict[str, Any]:
        logger.info("[Step] Ledger gate")
        ledger = state.get("ledger", {})
        metrics = state.get("metrics", {}).copy()
        manual_inputs = state.get("manual_inputs", {}) if isinstance(state.get("manual_inputs", {}), dict) else {}
        
        rounds = 0
        first_pass_checked = False
        
        while rounds <= MAX_GATE_REPAIR:
            rounds += 1
            metrics["gate_rounds"] = rounds
            
            if isinstance(ledger, dict):
                ledger = _normalize_org_structure(ledger)
                ledger = _apply_schedule_overrides(ledger, manual_inputs)
            ctx = PipelineContext(
                ledger=ledger if isinstance(ledger, dict) else {},
                metadata={"manual_inputs": manual_inputs} if isinstance(manual_inputs, dict) else {},
            )
            issues = run_rules(ctx, RULES, Stage.LEDGER)
            logger.info("[Gate] round=%s issues=%s", rounds, len(issues))
            
            if not first_pass_checked:
                metrics["gate_first_pass"] = (len(issues) == 0)
                metrics["issues_by_rule_first_gate"] = {}
                for it in issues:
                    metrics["issues_by_rule_first_gate"][it.rule_id] = metrics["issues_by_rule_first_gate"].get(it.rule_id, 0) + 1
                first_pass_checked = True
            
            if not issues:
                break
            
            if rounds > MAX_GATE_REPAIR:
                break
                
            metrics["gate_repair_count"] = metrics.get("gate_repair_count", 0) + 1
            
            spec_text = str(state.get("spec_text", ""))
            issue_payload = [
                {
                    "rule_id": it.rule_id,
                    "message": it.message,
                    "location": it.location,
                    "repair_hint": it.repair_hint,
                }
                for it in issues
            ]
            prompt = build_ledger_fix_prompt(spec_text, manual_inputs, ledger, issue_payload)
            ledger = call_llm_ledger(prompt, ledger_runtime)
            metrics["llm_calls"] = metrics.get("llm_calls", 0) + 1
            
        return {"ledger": ledger, "metrics": metrics}

    return _node


def _post_lint_node(final_runtime: LLMRuntime) -> Callable[[ProposalState], dict[str, Any]]:
    def _node(state: ProposalState) -> dict[str, Any]:
        logger.info("[Step] Post lint & rewrite")
        ledger = state.get("ledger", {})
        llm_output = state.get("llm_output", {})
        metrics = state.get("metrics", {}).copy()
        locked_placeholders = state.get("locked_placeholders", {})
        locked_tables = state.get("locked_tables", {})
        if not isinstance(locked_placeholders, dict):
            locked_placeholders = {}
        if not isinstance(locked_tables, dict):
            locked_tables = {}

        rounds = 0
        first_pass_checked = False

        while rounds <= MAX_REWRITE:
            rounds += 1
            metrics["rewrite_rounds"] = rounds

            ctx = PipelineContext(ledger=ledger if isinstance(ledger, dict) else {}, llm_output=llm_output)
            issues = run_rules(ctx, RULES, Stage.DOC_POST)
            logger.info("[Rewrite] round=%s issues=%s", rounds, len(issues))
            
            if not first_pass_checked:
                metrics["post_first_pass"] = (len(issues) == 0)
                metrics["issues_by_rule_first_post"] = {}
                for it in issues:
                    metrics["issues_by_rule_first_post"][it.rule_id] = metrics["issues_by_rule_first_post"].get(it.rule_id, 0) + 1
                first_pass_checked = True
            
            if not issues:
                if rounds == 1:
                    metrics["rewrite_success_first_try"] = True
                break
                
            if rounds > MAX_REWRITE:
                break
            
            metrics["rewrite_repair_count"] = metrics.get("rewrite_repair_count", 0) + 1
            
            ledger_scope = build_ledger_scope(
                ledger if isinstance(ledger, dict) else {},
                build_empty_output().get("placeholders", {}).keys(),
                extra_paths=_LEDGER_EXTRA_PATHS,
            )
            issues_payload = [
                {
                    "rule_id": it.rule_id,
                    "location": it.location,
                    "message": it.message,
                    "repair_hint": it.repair_hint,
                }
                for it in issues
            ]
            _unlock_from_issues(issues_payload, locked_placeholders, locked_tables)
            prompt = build_doc_rewrite_combined_prompt(
                ledger_scope=ledger_scope,
                llm_output=llm_output if isinstance(llm_output, dict) else {},
                issues=issues_payload,
            )
            fixes = call_llm_doc_rewrite_combined(prompt, final_runtime)
            metrics["llm_calls"] = metrics.get("llm_calls", 0) + 1
            llm_output = apply_doc_rewrite(llm_output, fixes)
            llm_output = _apply_ledger_overrides(ledger if isinstance(ledger, dict) else {}, llm_output if isinstance(llm_output, dict) else {})

        required_placeholders = state.get("required_placeholders", [])
        required_tables = state.get("required_tables", [])
        locked_placeholders = state.get("locked_placeholders", {})
        locked_tables = state.get("locked_tables", {})
        if not isinstance(locked_placeholders, dict):
            locked_placeholders = {}
        if not isinstance(locked_tables, dict):
            locked_tables = {}
        locked_placeholders, locked_tables = _update_locked_output(
            llm_output=llm_output if isinstance(llm_output, dict) else {},
            required_placeholders=required_placeholders if isinstance(required_placeholders, list) else [],
            required_tables=required_tables if isinstance(required_tables, list) else [],
            locked_placeholders=locked_placeholders,
            locked_tables=locked_tables,
        )
        if isinstance(llm_output, dict):
            llm_output = _apply_locked_output(llm_output, locked_placeholders, locked_tables)

        return {
            "llm_output": llm_output,
            "metrics": metrics,
            "locked_placeholders": locked_placeholders,
            "locked_tables": locked_tables,
        }

    return _node


def _complete_node(final_runtime: LLMRuntime) -> Callable[[ProposalState], dict[str, Any]]:
    def _node(state: ProposalState) -> dict[str, Any]:
        logger.info("[Step] Completeness check")
        ledger = state.get("ledger", {})
        llm_output = state.get("llm_output", {})
        metrics = state.get("metrics", {}).copy()
        locked_placeholders = state.get("locked_placeholders", {})
        locked_tables = state.get("locked_tables", {})
        if not isinstance(locked_placeholders, dict):
            locked_placeholders = {}
        if not isinstance(locked_tables, dict):
            locked_tables = {}

        if isinstance(llm_output, dict):
            llm_output = postprocess_llm_output(llm_output)
            llm_output = _apply_ledger_overrides(ledger if isinstance(ledger, dict) else {}, llm_output)
            tables = llm_output.get("tables")
            if not isinstance(tables, dict):
                tables = {}
            if _is_empty_rows(tables.get("milestones")):
                tables["milestones"] = build_milestones_table(ledger if isinstance(ledger, dict) else {})
            if _is_empty_rows(tables.get("risk_register")):
                from_ledger = build_risk_register_table(ledger if isinstance(ledger, dict) else {})
                if from_ledger:
                    tables["risk_register"] = from_ledger
            llm_output["tables"] = tables
            required_placeholders = state.get("required_placeholders", [])
            required_tables = state.get("required_tables", [])
            locked_placeholders, locked_tables = _update_locked_output(
                llm_output=llm_output,
                required_placeholders=required_placeholders if isinstance(required_placeholders, list) else [],
                required_tables=required_tables if isinstance(required_tables, list) else [],
                locked_placeholders=locked_placeholders,
                locked_tables=locked_tables,
            )
            llm_output = _apply_locked_output(llm_output, locked_placeholders, locked_tables)

        missing: list[str] = []
        if isinstance(llm_output, dict):
            placeholders = llm_output.get("placeholders", {})
            if not isinstance(placeholders, dict):
                placeholders = {}
            norm_placeholders: dict[str, str] = {}
            for k, v in placeholders.items():
                if not isinstance(k, str):
                    continue
                nk = _norm_placeholder_key(k)
                sv = v if isinstance(v, str) else ("" if v is None else str(v))
                if nk in norm_placeholders and norm_placeholders[nk].strip():
                    continue
                norm_placeholders[nk] = sv
            placeholders = norm_placeholders
            llm_output["placeholders"] = placeholders
            allow_empty: set[str] = set()
            required_placeholders = state.get("required_placeholders")
            if not isinstance(required_placeholders, list) or not required_placeholders:
                required_placeholders = list(PLACEHOLDER_FIELDS)
            for key in required_placeholders:
                if key in allow_empty:
                    continue
                val = placeholders.get(key, "")
                if not isinstance(val, str) or not val.strip():
                    missing.append(f"placeholders.{key}")

            tables = llm_output.get("tables", {})
            if not isinstance(tables, dict):
                tables = {}
            for table_name, (min_len, keys) in TABLE_MIN_SPECS.items():
                rows = tables.get(table_name)
                if not isinstance(rows, list):
                    missing.append(f"tables.{table_name}")
                    continue
                for i in range(min_len):
                    row = rows[i] if i < len(rows) else {}
                    if not isinstance(row, dict):
                        missing.append(f"tables.{table_name}[{i}]")
                        continue
                    for k in keys:
                        v = row.get(k, "")
                        if not isinstance(v, str) or not v.strip():
                            missing.append(f"tables.{table_name}[{i}].{k}")

        needs_patch = len(missing) > 0
        logger.info("[Complete] missing=%s", len(missing))
        state_rounds = state.get("patch_rounds", 0)
        return {
            "llm_output": llm_output,
            "metrics": metrics,
            "missing_fields": missing[:200],
            "needs_patch": needs_patch,
            "patch_rounds": state_rounds,
            "locked_placeholders": locked_placeholders,
            "locked_tables": locked_tables,
        }

    return _node


def _missing_patch_node(final_runtime: LLMRuntime) -> Callable[[ProposalState], dict[str, Any]]:
    def _node(state: ProposalState) -> dict[str, Any]:
        logger.info("[Step] Missing-fields patch")
        ledger = state.get("ledger", {})
        llm_output = state.get("llm_output", {})
        metrics = state.get("metrics", {}).copy()
        missing_fields = state.get("missing_fields", [])

        ledger_scope = build_ledger_scope(
            ledger if isinstance(ledger, dict) else {},
            build_empty_output().get("placeholders", {}).keys(),
            extra_paths=_LEDGER_EXTRA_PATHS,
        )
        prompt = build_missing_patch_prompt(
            ledger_scope=ledger_scope,
            llm_output=llm_output if isinstance(llm_output, dict) else {},
            missing_fields=missing_fields if isinstance(missing_fields, list) else [],
        )
        patch = call_llm_missing_patch(prompt, final_runtime)
        metrics["llm_calls"] = metrics.get("llm_calls", 0) + 1
        rounds = int(state.get("patch_rounds", 0) or 0) + 1
        metrics["patch_rounds"] = rounds
        allowed_placeholders: set[str] = set()
        allowed_tables: set[str] = set()
        if isinstance(missing_fields, list):
            for mf in missing_fields:
                if not isinstance(mf, str):
                    continue
                if mf.startswith("placeholders."):
                    allowed_placeholders.add(_norm_placeholder_key(mf[len("placeholders.") :]))
                if mf.startswith("tables."):
                    rest = mf[len("tables.") :]
                    table_name = rest.split("[", 1)[0].split(".", 1)[0]
                    if table_name:
                        allowed_tables.add(table_name)
        if isinstance(patch, dict):
            p_patch = patch.get("placeholders")
            if isinstance(p_patch, dict):
                norm_patch: dict[str, str] = {}
                for k, v in p_patch.items():
                    if not isinstance(k, str) or not isinstance(v, str):
                        continue
                    nk = _norm_placeholder_key(k)
                    if nk in norm_patch and norm_patch[nk].strip():
                        continue
                    norm_patch[nk] = v
                patch["placeholders"] = {k: v for k, v in norm_patch.items() if k in allowed_placeholders}
            t_patch = patch.get("tables")
            if isinstance(t_patch, dict):
                norm_tables: dict[str, list[dict[str, str]]] = {}
                for k, v in t_patch.items():
                    if not isinstance(k, str) or not isinstance(v, list):
                        continue
                    name = k.strip()
                    if name.startswith("tables."):
                        name = name[len("tables.") :].strip()
                    if not name:
                        continue
                    norm_tables[name] = v
                patch["tables"] = {k: v for k, v in norm_tables.items() if k in allowed_tables}
        llm_output = apply_output_patch(llm_output, patch)
        llm_output = _apply_ledger_overrides(ledger if isinstance(ledger, dict) else {}, llm_output if isinstance(llm_output, dict) else {})
        required_placeholders = state.get("required_placeholders", [])
        required_tables = state.get("required_tables", [])
        locked_placeholders = state.get("locked_placeholders", {})
        locked_tables = state.get("locked_tables", {})
        if not isinstance(locked_placeholders, dict):
            locked_placeholders = {}
        if not isinstance(locked_tables, dict):
            locked_tables = {}
        locked_placeholders, locked_tables = _update_locked_output(
            llm_output=llm_output if isinstance(llm_output, dict) else {},
            required_placeholders=required_placeholders if isinstance(required_placeholders, list) else [],
            required_tables=required_tables if isinstance(required_tables, list) else [],
            locked_placeholders=locked_placeholders,
            locked_tables=locked_tables,
        )
        if isinstance(llm_output, dict):
            llm_output = _apply_locked_output(llm_output, locked_placeholders, locked_tables)
        return {
            "llm_output": llm_output,
            "metrics": metrics,
            "needs_patch": False,
            "patch_rounds": rounds,
            "locked_placeholders": locked_placeholders,
            "locked_tables": locked_tables,
        }

    return _node


def _metrics_node() -> Callable[[ProposalState], dict[str, Any]]:
    def _node(state: ProposalState) -> dict[str, Any]:
        ledger = state.get("ledger", {})
        llm_output = state.get("llm_output", {})
        metrics = state.get("metrics", {}).copy()
        
        ctx = PipelineContext(ledger=ledger, llm_output=llm_output)
        soft = compute_soft_metrics(ctx)
        metrics.update(soft)
        
        # Final issues check for Hard Gate (L0)
        final_issues = run_rules(ctx, RULES, Stage.DOC_POST)
        metrics["final_issues_by_rule"] = {}
        for it in final_issues:
            metrics["final_issues_by_rule"][it.rule_id] = metrics["final_issues_by_rule"].get(it.rule_id, 0) + 1
            
        return {"metrics": metrics}
    return _node


def build_graph(
    *,
    ledger_runtime: LLMRuntime,
    final_runtime: LLMRuntime,
    section_chunks: list[list[str]] | None = None,
    table_chunks: list[list[str]] | None = None,
) -> StateGraph:
    graph = StateGraph(ProposalState)

    graph.add_node("ledger", _ledger_node(ledger_runtime))
    graph.add_node("gate", _gate_node(ledger_runtime))
    section_chunks = section_chunks or []
    table_chunks = table_chunks or []
    section_nodes: list[str] = []
    table_nodes: list[str] = []
    if section_chunks or table_chunks:
        for idx, chunk in enumerate(section_chunks):
            name = f"generate_section_{idx:02d}"
            graph.add_node(name, _generate_section_node(final_runtime, chunk, []))
            section_nodes.append(name)
        for idx, chunk in enumerate(table_chunks):
            name = f"generate_table_{idx:02d}"
            graph.add_node(name, _generate_section_node(final_runtime, [], chunk))
            table_nodes.append(name)
        graph.add_node("merge_sections", _merge_sections_node())
    else:
        graph.add_node("generate", _generate_node(final_runtime))
    graph.add_node("post_lint", _post_lint_node(final_runtime))
    graph.add_node("complete", _complete_node(final_runtime))
    graph.add_node("missing_patch", _missing_patch_node(final_runtime))
    graph.add_node("metrics", _metrics_node())
    
    graph.add_edge("ledger", "gate")
    if section_nodes or table_nodes:
        for node in section_nodes + table_nodes:
            graph.add_edge("gate", node)
            graph.add_edge(node, "merge_sections")
        graph.add_edge("merge_sections", "post_lint")
    else:
        graph.add_edge("gate", "generate")
        graph.add_edge("generate", "post_lint")
    graph.add_edge("post_lint", "complete")
    graph.add_edge("missing_patch", "post_lint")

    def _route_complete(state: ProposalState) -> str:
        if bool(state.get("needs_patch", False)) and int(state.get("patch_rounds", 0) or 0) < 2:
            return "missing_patch"
        return "metrics"

    graph.add_conditional_edges("complete", _route_complete, {"missing_patch": "missing_patch", "metrics": "metrics"})
    graph.add_edge("metrics", END)
    
    graph.set_entry_point("ledger")
    return graph
