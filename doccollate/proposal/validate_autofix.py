from __future__ import annotations

import json
import re
import textwrap
from typing import Any

from ..llm.api import call_llm
from ..llm.client import LLMRuntime
from .validate_schema import MILESTONE_KEYS, MILESTONE_LEN, PLACEHOLDER_FIELDS, TABLE_MIN_SPECS


def _fix_product_features(text: str) -> str:
    raw = (text or "").strip()
    if not raw:
        return ""

    parts = [p.strip() for p in raw.splitlines() if p.strip()]
    if len(parts) <= 1:
        tmp = re.split(r"[；;]\s*", raw)
        parts = [p.strip() for p in tmp if p.strip()] or parts

    cleaned: list[str] = []
    seen: set[str] = set()
    for p in parts:
        p = re.sub(r"^\s*(?:[-*•]|\d+[\.)]|\(?\d+\)?|（\d+）)\s*", "", p).strip()
        if not p:
            continue
        p = p.replace(":", "：")
        p = re.sub(r"\s+", " ", p).strip()
        if p in seen:
            continue
        seen.add(p)
        cleaned.append(p)

    if len(cleaned) > 6:
        cleaned = cleaned[:6]
    formatted: list[str] = []
    for line in cleaned:
        if "：" in line:
            title, desc = line.split("：", 1)
            title = title.strip()
            desc = desc.strip()
            if title and desc:
                out = f"• {title}：{desc}"
            elif title and not desc:
                out = f"• {title}："
            else:
                out = f"• {line}"
        else:
            out = f"• {line}"
        formatted.append(out)

    return "\n".join(formatted)


def _normalize_table(items: list[dict[str, str]], min_len: int, keys: list[str]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for item in items:
        row = {k: str(item.get(k, "")) for k in keys}
        normalized.append(row)
    while len(normalized) < min_len:
        row = {k: "" for k in keys}
        normalized.append(row)
    return normalized


def _format_evidence(chunks: list[dict[str, Any]] | None, max_chars: int = 2500) -> str:
    if not chunks:
        return ""
    lines: list[str] = []
    used = 0
    for c in chunks:
        cid = str(c.get("id", ""))
        text = str(c.get("text", ""))
        line = f"- {cid}: {text}"
        used += len(line)
        if used > max_chars:
            break
        lines.append(line)
    return "\n".join(lines)


def _format_currency(value: str) -> str:
    digits = "".join(ch for ch in value if ch.isdigit())
    if not digits:
        return ""
    number = int(digits)
    return f"¥{number:,}"


def _normalize_currency_fields(rows: list[dict[str, str]], key: str) -> list[dict[str, str]]:
    for row in rows:
        raw = str(row.get(key, "")).strip()
        if not raw:
            continue
        row[key] = _format_currency(raw)
    return rows


def _llm_fill_resources_costs(
    rows: list[dict[str, str]],
    min_len: int,
    evidence_chunks: list[dict[str, Any]] | None,
    runtime: LLMRuntime,
) -> list[dict[str, str]]:
    prompt = textwrap.dedent(
        f"""
        你是一个严谨的成本评估助手。请补全 resources 表格，并保证可直接用于立项建议书。

        约束：
        - 只输出 JSON，禁止输出任何额外文本
        - 输出格式必须为：{{"resources":[{{"name":"","level":"","spec":"","source":"","cost":""}}]}}
        - 保留输入中已有行的 name/level/spec/source（不要改写这些字段）
        - 对于 cost 为空的行：必须给出人民币估算，格式统一为 "¥50,000"
        - 禁止输出“待评估”或区间/周期描述
        - 若行数少于 {min_len}：在末尾新增合理资源行补齐到 {min_len} 行，并同样给出 cost

        可参考的证据（来自说明书检索，可能包含环境规模、部署方式、资源要求等）：
        {_format_evidence(evidence_chunks)}

        输入：
        {json.dumps({"resources": rows}, ensure_ascii=False)}
        """
    ).strip()

    def _call_once() -> list[dict[str, str]] | None:
        out = call_llm(prompt, runtime)
        items = out.get("resources")
        if not isinstance(items, list):
            return None
        normalized: list[dict[str, str]] = []
        for it in items:
            if not isinstance(it, dict):
                continue
            normalized.append(
                {
                    "name": str(it.get("name", "")),
                    "level": str(it.get("level", "")),
                    "spec": str(it.get("spec", "")),
                    "source": str(it.get("source", "")),
                    "cost": str(it.get("cost", "")),
                }
            )
        while len(normalized) < min_len:
            normalized.append({"name": "", "level": "", "spec": "", "source": "", "cost": ""})
            return _normalize_currency_fields(normalized, "cost")

    try:
        first = _call_once()
        if first is None:
            return rows
        if any("待评估" in str(r.get("cost", "")) for r in first):
            for r in first:
                if "待评估" in str(r.get("cost", "")):
                    r["cost"] = ""
            second = _call_once()
            return _normalize_currency_fields(second or first, "cost")
        return _normalize_currency_fields(first, "cost")
    except Exception:
        pass

    return rows


def _llm_fill_costs_amount(
    rows: list[dict[str, str]],
    min_len: int,
    evidence_chunks: list[dict[str, Any]] | None,
    runtime: LLMRuntime,
) -> list[dict[str, str]]:
    prompt = textwrap.dedent(
        f"""
        你是一个严谨的预算评估助手。请补全 costs 表格，并保证可直接用于立项建议书。

        约束：
        - 只输出 JSON，禁止输出任何额外文本
        - 输出格式必须为：{{"costs":[{{"item":"","amount":"","note":""}}]}}
        - 保留输入中已有行的 item/note（不要改写这些字段）
        - 对于 amount 为空的行：必须给出人民币估算，格式统一为 "¥50,000"
        - 禁止输出“待评估”或区间/周期描述
        - 若行数少于 {min_len}：在末尾新增合理费用项补齐到 {min_len} 行，并给出 amount

        可参考的证据（来自说明书检索，可能包含预算、采购、人力、云资源等）：
        {_format_evidence(evidence_chunks)}

        输入：
        {json.dumps({"costs": rows}, ensure_ascii=False)}
        """
    ).strip()

    def _call_once() -> list[dict[str, str]] | None:
        out = call_llm(prompt, runtime)
        items = out.get("costs")
        if not isinstance(items, list):
            return None
        normalized: list[dict[str, str]] = []
        for it in items:
            if not isinstance(it, dict):
                continue
            normalized.append(
                {
                    "item": str(it.get("item", "")),
                    "amount": str(it.get("amount", "")),
                    "note": str(it.get("note", "")),
                }
            )
        while len(normalized) < min_len:
            normalized.append({"item": "", "amount": "", "note": ""})
            return _normalize_currency_fields(normalized, "amount")

    try:
        first = _call_once()
        if first is None:
            return rows
        if any("待评估" in str(r.get("amount", "")) for r in first):
            for r in first:
                if "待评估" in str(r.get("amount", "")):
                    r["amount"] = ""
            second = _call_once()
            return _normalize_currency_fields(second or first, "amount")
        return _normalize_currency_fields(first, "amount")
    except Exception:
        pass

    return rows


def _normalize_milestones(items: list[dict[str, str]]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for item in items[:MILESTONE_LEN]:
        row = {k: str(item.get(k, "")) for k in MILESTONE_KEYS}
        normalized.append(row)
    while len(normalized) < MILESTONE_LEN:
        normalized.append({k: "" for k in MILESTONE_KEYS})
    return normalized


def auto_fix(
    output: dict[str, Any],
    runtime: LLMRuntime,
    field_evidence: dict[str, list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    fixed = dict(output)
    placeholders = fixed.get("placeholders")
    if not isinstance(placeholders, dict):
        placeholders = {}
    for key in PLACEHOLDER_FIELDS:
        if key not in placeholders or placeholders[key] is None:
            placeholders[key] = ""
        else:
            placeholders[key] = str(placeholders[key])
    placeholders["{{ product_features }}"] = _fix_product_features(
        placeholders.get("{{ product_features }}", "")
    )
    fixed["placeholders"] = placeholders

    tables = fixed.get("tables")
    if not isinstance(tables, dict):
        tables = {}
    normalized_tables: dict[str, list[dict[str, str]]] = {}
    for table_name, (min_len, keys) in TABLE_MIN_SPECS.items():
        items = tables.get(table_name)
        if not isinstance(items, list):
            items = []
        normalized_tables[table_name] = _normalize_table(items, min_len, keys)
    items = tables.get("milestones")
    if not isinstance(items, list):
        items = []
    normalized_tables["milestones"] = _normalize_milestones(items)

    fe = field_evidence or {}
    resources_min_len, _ = TABLE_MIN_SPECS["resources"]
    costs_min_len, _ = TABLE_MIN_SPECS["costs"]

    resources_rows = normalized_tables.get("resources", [])
    costs_rows = normalized_tables.get("costs", [])

    need_res = (len(resources_rows) < resources_min_len) or any(
        not str(r.get("cost", "")).strip() for r in resources_rows
    )
    need_costs = (len(costs_rows) < costs_min_len) or any(
        not str(r.get("amount", "")).strip() for r in costs_rows
    )

    if need_res:
        normalized_tables["resources"] = _llm_fill_resources_costs(
            rows=resources_rows,
            min_len=resources_min_len,
            evidence_chunks=fe.get("resources"),
            runtime=runtime,
        )

    if need_costs:
        normalized_tables["costs"] = _llm_fill_costs_amount(
            rows=costs_rows,
            min_len=costs_min_len,
            evidence_chunks=fe.get("costs"),
            runtime=runtime,
        )
    fixed["tables"] = normalized_tables

    evidence = fixed.get("evidence")
    if evidence is not None and not isinstance(evidence, list):
        fixed["evidence"] = []

    return fixed
