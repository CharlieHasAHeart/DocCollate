from __future__ import annotations

from ..extract.data_normalize import (
    derive_fields,
    normalize_assessment_data,
    sanitize_data,
)
from ..extract.text_sections import (
    build_section_chunks,
    build_section_map,
    split_into_chunks,
)
from ..extract.text_extractors import (
    extract_fields_by_prompt,
    extract_func_items,
    summarize_spec,
)
from .constants import FIELD_PROMPTS
from ..llm.client import LLMRuntime
from ..config import DatesConfig


def build_form_data(
    text: str,
    runtime: LLMRuntime,
    dates_config: DatesConfig | None = None,
    required_fields: set[str] | None = None,
) -> dict[str, object]:
    data: dict[str, object] = {}
    required = set(required_fields) if required_fields is not None else None
    if required is not None and not required:
        return data

    prompt_fields = FIELD_PROMPTS if required is None else {k: v for k, v in FIELD_PROMPTS.items() if k in required}
    needs_func_list = required is None or "product__func_list" in required
    needs_extraction = needs_func_list or bool(prompt_fields)

    summary = ""
    section_chunks = []
    full_chunks = []
    if needs_extraction:
        summary = summarize_spec(text, runtime)
        section_map = build_section_map(text)
        section_chunks = build_section_chunks(section_map)
        full_chunks = split_into_chunks(text)

    if needs_func_list:
        func_items = extract_func_items(section_chunks, runtime, summary=summary)
        if func_items:
            data["product__func_list"] = func_items
    if prompt_fields:
        field_data = extract_fields_by_prompt(runtime, summary, text, section_chunks, full_chunks, prompt_fields)
        data.update(field_data)

    data = sanitize_data(data)
    data = normalize_assessment_data(data, dates_config=dates_config, required_fields=required)
    data = derive_fields(data, required_fields=required)
    return data


def apply_app_metadata(
    data: dict[str, object],
    applicant_type: str | None,
    app_name: str | None,
    app_version: str | None,
) -> None:
    if applicant_type:
        data["applicant__type"] = applicant_type
    if app_name:
        data["app__name"] = app_name
    if app_version:
        data["app__version"] = app_version
