from __future__ import annotations

from typing import Any

from .rules_engine import _parse_ymd


def _is_window_valid(window: Any) -> bool:
    if not isinstance(window, dict):
        return False
    start = str(window.get("start", "")).strip()
    end = str(window.get("end", "")).strip()
    if not start or not end:
        return False
    start_date = _parse_ymd(start)
    end_date = _parse_ymd(end)
    return bool(start_date and end_date and end_date >= start_date)


def check_ledger(ledger: dict[str, Any]) -> list[str]:
    if not isinstance(ledger, dict):
        return ["ledger:not_dict"]

    issues: list[str] = []
    if not _is_window_valid(ledger.get("delivery_window")):
        issues.append("ledger:delivery_window_invalid")
    if not _is_window_valid(ledger.get("poc_window")):
        issues.append("ledger:poc_window_invalid")

    return issues
