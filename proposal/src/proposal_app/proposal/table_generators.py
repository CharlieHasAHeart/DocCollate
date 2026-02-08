from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from ..core.date_utils import format_date, parse_date


def build_milestones_table(ledger: dict[str, Any]) -> list[dict[str, str]]:
    if not isinstance(ledger, dict):
        return []
    tables = ledger.get("tables") if isinstance(ledger.get("tables"), dict) else None
    if isinstance(tables, dict):
        milestones = tables.get("milestones")
        if isinstance(milestones, list) and milestones:
            rows: list[dict[str, str]] = []
            for item in milestones:
                if not isinstance(item, dict):
                    continue
                row = {
                    "phase": str(item.get("phase", "")).strip(),
                    "tasks": str(item.get("tasks", "")).strip(),
                    "start_date": str(item.get("start_date", "")).strip(),
                    "end_date": str(item.get("end_date", "")).strip(),
                    "deliverables": str(item.get("deliverables", "")).strip(),
                }
                if all(v for v in row.values()):
                    rows.append(row)
            if rows:
                return rows
    window = ledger.get("delivery_window")
    if not isinstance(window, dict):
        return []
    start_raw = str(window.get("start", "")).strip()
    end_raw = str(window.get("end", "")).strip()
    start = parse_date(start_raw)
    end = parse_date(end_raw)
    if not start or not end or end < start:
        return []

    phases = [
        ("项目启动与PoC验证", "完成需求澄清、环境准备与PoC验证", "PoC报告、需求基线、数据接入清单"),
        ("方案设计与开发实现", "完成总体设计、核心功能开发与联调", "总体设计文档、核心功能版本、联调记录"),
        ("测试与性能验证", "完成系统测试、性能压测与安全测试", "测试报告、性能报告、安全整改清单"),
        ("试点上线与验收准备", "完成试点上线、用户培训与验收资料准备", "上线清单、培训材料、验收用例"),
        ("正式验收与移交运维", "完成正式验收、移交运维与持续支持启动", "验收证书、运维手册、支持SLA确认"),
    ]

    total_days = max((end - start).days, 1)
    step = max(total_days // len(phases), 1)
    dates: list[tuple[date, date]] = []
    cur = start
    for i in range(len(phases)):
        if i == len(phases) - 1:
            seg_end = end
        else:
            seg_end = min(cur + timedelta(days=step), end)
        dates.append((cur, seg_end))
        cur = min(seg_end + timedelta(days=1), end)

    rows: list[dict[str, str]] = []
    for (phase, tasks, deliverables), (s, e) in zip(phases, dates, strict=False):
        rows.append(
            {
                "phase": phase,
                "tasks": tasks,
                "start_date": format_date(s),
                "end_date": format_date(e),
                "deliverables": deliverables,
            }
        )
    return rows


def build_risk_register_table(ledger: dict[str, Any]) -> list[dict[str, str]]:
    if not isinstance(ledger, dict):
        return []
    tables = ledger.get("tables") if isinstance(ledger.get("tables"), dict) else None
    reg = None
    if isinstance(tables, dict):
        reg = tables.get("risk_register")
    if not isinstance(reg, list) or not reg:
        scope_boundary = ledger.get("scope_boundary") if isinstance(ledger.get("scope_boundary"), dict) else None
        if not isinstance(scope_boundary, dict):
            return []
        reg = scope_boundary.get("risk_register")
    if not isinstance(reg, list) or not reg:
        return []
    out: list[dict[str, str]] = []
    for item in reg:
        if not isinstance(item, dict):
            continue
        row = {
            "id": str(item.get("id", "")).strip(),
            "description": str(item.get("description", "")).strip(),
            "probability": str(item.get("probability", "")).strip(),
            "impact": str(item.get("impact", "")).strip(),
            "level": str(item.get("level", "")).strip(),
            "trigger": str(item.get("trigger", "")).strip(),
            "mitigation": str(item.get("mitigation", "")).strip(),
        }
        if all(v for v in row.values()):
            out.append(row)
    return out
