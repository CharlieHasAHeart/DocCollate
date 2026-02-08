from __future__ import annotations

import logging
import re

from ..core.date_utils import parse_date
from ..core.input_flow import prompt_date, prompt_text
from ..llm.api import translate_to_english
from ..llm.client import LLMRuntime


def prompt_cover(
    runtime: LLMRuntime,
    company_name_default: str = "",
    project_name_default: str = "",
) -> dict[str, str]:
    company_name = company_name_default.strip()
    project_name = project_name_default.strip()
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


logger = logging.getLogger(__name__)


def prompt_schedule_dates() -> tuple[str, str]:
    while True:
        dev_date = prompt_date("Development date")
        completion_date = prompt_date("Completion date")
        dev = parse_date(dev_date)
        completion = parse_date(completion_date)
        if dev and completion and completion >= dev:
            return dev_date, completion_date
        logger.error("[Error] Completion date must be the same as or after development date.")
