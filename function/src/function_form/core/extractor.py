from __future__ import annotations

import re

from .models import FunctionItem

MODULE_HEADING_RE = re.compile(r"^###\s*\d+\.\d+\.\d+\s*模块[:：]\s*(.+?)\s*$")
SUBSECTION_RE = re.compile(r"^###\s*\d+\.\d+\.\d+")
HEADING_RE = re.compile(r"^#{1,6}\s+")


def _clean_line(line: str) -> str:
    return re.sub(r"\s+", " ", line.strip())


def _normalize_name(raw: str) -> str:
    text = _clean_line(raw)
    text = re.sub(r"^[\-\*•\d\.、\)\(]+", "", text).strip()
    text = re.sub(r"[：:;；。,.，]+$", "", text).strip()
    return text


def _build_desc(name: str) -> str:
    core = re.sub(r"(模块|功能|菜单)$", "", name).strip() or name
    return f"可以进行{core}相关管理"


def _extract_module_blocks(lines: list[str]) -> list[tuple[str, list[str]]]:
    blocks: list[tuple[str, list[str]]] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = MODULE_HEADING_RE.match(line)
        if not m:
            i += 1
            continue
        name = _normalize_name(m.group(1))
        i += 1
        body: list[str] = []
        while i < len(lines):
            cur = lines[i]
            if SUBSECTION_RE.match(cur):
                break
            if HEADING_RE.match(cur):
                i += 1
                continue
            if cur.startswith("!["):
                i += 1
                continue
            if cur:
                body.append(cur)
            i += 1
        if name:
            blocks.append((name, body))
    return blocks


def _summarize_desc(body: list[str], name: str) -> str:
    core = re.sub(r"(模块|功能|菜单)$", "", name).strip() or name
    return f"可以进行{core}管理"


def extract_function_list(source_text: str, limit: int = 30) -> list[FunctionItem]:
    lines = [_clean_line(x) for x in (source_text or "").splitlines() if _clean_line(x)]

    blocks = _extract_module_blocks(lines)
    if blocks:
        out: list[FunctionItem] = []
        seen: set[str] = set()
        for name, body in blocks:
            if name in seen:
                continue
            seen.add(name)
            out.append(FunctionItem(name=name, desc=_summarize_desc(body, name)))
            if len(out) >= limit:
                break
        if out:
            return out

    defaults = ["系统管理", "用户管理", "业务管理", "统计分析", "报表管理", "配置管理"]
    return [FunctionItem(name=n, desc=_build_desc(n)) for n in defaults]
