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


def build_form_data(text: str, runtime: LLMRuntime, dates_config: DatesConfig | None = None) -> dict[str, object]:
    data: dict[str, object] = {}
    summary = summarize_spec(text, runtime)
    section_map = build_section_map(text)
    section_chunks = build_section_chunks(section_map)
    full_chunks = split_into_chunks(text)

    func_items = extract_func_items(section_chunks, runtime, summary=summary)
    if func_items:
        data["product__func_list"] = func_items
    field_data = extract_fields_by_prompt(runtime, summary, text, section_chunks, full_chunks, FIELD_PROMPTS)

    data.update(field_data)

    data = sanitize_data(data)
    data = normalize_assessment_data(data, dates_config=dates_config)
    data = derive_fields(data)
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
