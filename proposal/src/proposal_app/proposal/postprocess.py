from __future__ import annotations

import re
from typing import Any


_STRONG_TRADE_TRIGGERS = (
    "撮合",
    "清结算",
    "结算",
    "对接交易所",
    "挂牌",
    "撮合成交",
    "订单撮合",
    "资金结算",
    "对外交易平台",
)
_TRADE_CONFUSION_PATTERNS = (
    "覆盖交易全链条",
    "交易全链条",
    "交易全链路",
    "支撑碳资产交易",
    "首笔交易",
    "交易平台",
    "交易模块",
    "交易撮合",
    "交易与溯源",
    "交易看板",
)

_LEDGER_REF_RE = re.compile(r"\bledger\.[a-zA-Z0-9_.]+\b")
_INTERNAL_REF_REWRITE = (
    (re.compile(r"遵循依据本项目计划"), "遵循本项目计划"),
    (re.compile(r"基于依据本项目计划"), "基于本项目计划"),
    (re.compile(r"依据本项目计划口径"), "本项目计划口径"),
    (re.compile(r"依据本项目计划定义"), "本项目计划定义"),
    (re.compile(r"依据本项目计划规定"), "本项目计划规定"),
)


def _split_sentences(text: str) -> list[str]:
    parts = re.findall(r"[^。]*。|[^。]+$", text)
    out: list[str] = []
    for s in parts:
        ss = s.strip()
        if ss:
            out.append(ss)
    return out


def _is_boundary_sentence(sentence: str) -> bool:
    s = sentence.replace(" ", "")
    if ("撮合" in s or "清结算" in s) and ("不" in s) and ("交易平台" in s or "交易所" in s or "外部交易" in s):
        return True
    if "不提供撮合清结算" in s:
        return True
    if "不做撮合" in s or "不做清结算" in s:
        return True
    if "非撮合" in s or "非清结算" in s:
        return True
    return False


def postprocess_llm_output(llm_output: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(llm_output, dict):
        return llm_output
    placeholders = llm_output.get("placeholders")
    if not isinstance(placeholders, dict):
        return llm_output

    def _normalize_internal_refs(text: str) -> str:
        if not text:
            return text
        text = _LEDGER_REF_RE.sub("依据本项目计划", text)
        for pattern, replacement in _INTERNAL_REF_REWRITE:
            text = pattern.sub(replacement, text)
        return text

    global_kept: str | None = None
    removed_candidate: str | None = None

    for key, value in list(placeholders.items()):
        if not isinstance(value, str) or not value.strip():
            continue
        value = _normalize_internal_refs(value)
        paragraphs = value.split("\n\n")
        new_paragraphs: list[str] = []
        for p in paragraphs:
            if not p.strip():
                continue
            strong_hit = any(t in p for t in _STRONG_TRADE_TRIGGERS) or any(t in p for t in _TRADE_CONFUSION_PATTERNS)
            sentences = _split_sentences(p)
            boundary_sentences = [s for s in sentences if _is_boundary_sentence(s)]
            if not boundary_sentences:
                new_paragraphs.append(p.strip())
                continue

            keep_local = strong_hit
            kept_here: str | None = None
            if global_kept is None:
                kept_here = boundary_sentences[0]
                global_kept = kept_here
                keep_local = True

            rebuilt: list[str] = []
            for s in sentences:
                if not _is_boundary_sentence(s):
                    rebuilt.append(s)
                    continue
                if keep_local:
                    if kept_here is None:
                        kept_here = s
                        rebuilt.append(s)
                    else:
                        if s == kept_here:
                            continue
                        continue
                else:
                    if removed_candidate is None:
                        removed_candidate = s
                    continue
            new_paragraphs.append("".join(rebuilt).strip())
        placeholders[key] = "\n\n".join([p for p in new_paragraphs if p])

    tables = llm_output.get("tables")
    if isinstance(tables, dict):
        for table_name, rows in tables.items():
            if not isinstance(rows, list):
                continue
            for row in rows:
                if not isinstance(row, dict):
                    continue
                for k, v in list(row.items()):
                    if isinstance(v, str):
                        row[k] = _normalize_internal_refs(v)
        llm_output["tables"] = tables

    if global_kept is None and removed_candidate is not None:
        target_key = next(iter(placeholders.keys()), None)
        if target_key is not None:
            base = placeholders.get(target_key)
            if isinstance(base, str) and base.strip():
                placeholders[target_key] = base.strip() + "\n\n" + removed_candidate
            else:
                placeholders[target_key] = removed_candidate

    llm_output["placeholders"] = placeholders
    return llm_output
