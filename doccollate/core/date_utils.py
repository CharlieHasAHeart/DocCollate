from __future__ import annotations

import re
from datetime import date, datetime, timedelta


def _to_workday(value: date) -> date:
    while value.weekday() >= 5:
        value = value - timedelta(days=1)
    return value


def _subtract_months(value: date, months: int) -> date:
    year = value.year
    month = value.month - months
    while month <= 0:
        year -= 1
        month += 12
    last_day = _month_last_day(year, month)
    day = min(value.day, last_day)
    return value.replace(year=year, month=month, day=day)


def _month_last_day(year: int, month: int) -> int:
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    return (next_month - timedelta(days=1)).day


def parse_date(value: str) -> date | None:
    value = (value or "").strip()
    if not value:
        return None
    if re.match(r"^\d{4}年\d{1,2}月\d{1,2}日$", value):
        value = value.replace("年", "-").replace("月", "-").replace("日", "")
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def format_date(value: date | None) -> str:
    if not value:
        return ""
    return value.strftime("%Y/%m/%d")


def normalize_date_str(value: str) -> str:
    parsed = parse_date(value)
    return format_date(parsed) if parsed else value.strip()


def default_assess_dates(
    today: date | None = None,
    completion_days_ago: int = 14,
    dev_months_ago: int = 5,
) -> tuple[str, str]:
    if today is None:
        today = date.today()
    completion = _to_workday(today - timedelta(days=completion_days_ago))
    dev_date = _to_workday(_subtract_months(completion, dev_months_ago))
    return format_date(completion), format_date(dev_date)
