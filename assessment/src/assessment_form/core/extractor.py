from __future__ import annotations

import re


def extract_main_functions(source_text: str) -> str:
    lines = [x.strip() for x in (source_text or "").splitlines() if x.strip()]
    picks: list[str] = []
    for line in lines:
        m = re.match(r"^###\s*\d+\.\d+\.\d+\s*模块[:：]\s*(.+)$", line)
        if m:
            picks.append(m.group(1).strip())
    if not picks:
        return "计划排程、订单管理、网络管理、任务管理、冲突处理、路线推荐"
    return "、".join(dict.fromkeys(picks))


def detect_language(source_text: str) -> str:
    text = (source_text or "").lower()
    langs = []
    if "typescript" in text or "javascript" in text:
        langs.append("TypeScript/JavaScript")
    if "python" in text:
        langs.append("Python")
    if "java" in text:
        langs.append("Java")
    return "、".join(langs) if langs else "Python"
