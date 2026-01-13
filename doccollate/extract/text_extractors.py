from __future__ import annotations

import json
import re

from ..core.constants import FALLBACK_MIN_MODULES, MODULE_TEXT_HINTS, MODULE_TITLE_WORDS
from ..llm.client import LLMRuntime
from ..llm.utils import call_llm_json
from ..llm.client import chat_text
from .text_retrieval import BM25Retriever, get_context_for_field, retrieve_evidence_for_module
from .text_sections import Chunk


def is_module_candidate(chunk_title: str | None, chunk_text: str) -> bool:
    title = (chunk_title or "").strip()
    content = (chunk_text or "").strip()
    if any(word in title for word in MODULE_TITLE_WORDS):
        return True
    if any(word in content for word in MODULE_TEXT_HINTS):
        return True
    return False


def clean_module_title(title: str) -> str:
    if not title:
        return ""
    cleaned = re.sub(r"^\d+(\.\d+)*\s*", "", title)
    cleaned = re.sub(r"^第[一二三四五六七八九十]+章\s*", "", cleaned)
    cleaned = cleaned.replace("：", " ").replace(":", " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def collect_module_candidates_from_chunks(chunks: list[Chunk]) -> list[str]:
    titles: list[str] = []
    for chunk in chunks:
        title = clean_module_title(chunk.section_title or "")
        if title and is_module_candidate(title, chunk.text):
            if title not in titles:
                titles.append(title)
    return titles


def build_module_evidences(chunks: list[Chunk], retriever: BM25Retriever) -> list[dict[str, str]]:
    titles = collect_module_candidates_from_chunks(chunks)
    evidences: list[dict[str, str]] = []
    for title in titles:
        evidence = retrieve_evidence_for_module(title, retriever, top_k=2)
        if len(evidence) < 80:
            continue
        evidences.append({"module_title": title, "evidence": evidence})
    return evidences


def normalize_llm_func_items(items: list[dict[str, str]]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for item in items:
        title = clean_module_title(str(item.get("一级功能") or "").strip())
        desc = str(item.get("功能描述") or "").strip()
        if not title:
            continue
        desc = re.sub(r"\s+", "", desc)
        desc = re.sub(r"^[\d\.\u3001]+", "", desc)
        desc = desc.replace("：", "，").replace(":", "，")
        desc = desc.replace("“", "").replace("”", "").replace('"', "")
        if not desc.startswith("可以"):
            desc = "可以" + desc
        if not desc.endswith("。"):
            desc += "。"
        normalized.append(
            {
                "name": title,
                "desc": desc,
                "一级功能": title,
                "功能描述": desc,
            }
        )
    return normalized


def normalize_llm_func_items_from_response(response: dict) -> list[dict[str, str]]:
    items = response.get("items") if isinstance(response, dict) else None
    if not isinstance(items, list):
        return []
    return normalize_llm_func_items(items)


def summarize_spec(text: str, runtime: LLMRuntime, max_chars: int = 6000) -> str:
    snippet = text[:max_chars].strip()
    if not snippet:
        return ""
    system_prompt = (
        "你是严谨的说明书摘要助手。请输出摘要与关键信息列表，尽量覆盖软件用途、主要功能、"
        "开发/运行环境、编程语言、数据库、操作系统、软件类别/应用领域。"
        "输出为纯文本多行，使用“字段: 内容”的格式，不要编号。"
    )
    user_prompt = f"说明书内容如下：\n{snippet}"
    return chat_text(runtime, system_prompt, user_prompt, temperature=0.2)


def extract_func_items(
    section_chunks: list[Chunk],
    runtime: LLMRuntime,
    summary: str = "",
) -> list[dict[str, str]]:
    if not section_chunks:
        return []
    retriever = BM25Retriever(section_chunks)
    evidences = build_module_evidences(section_chunks, retriever)
    if len(evidences) < FALLBACK_MIN_MODULES:
        if not summary:
            return []
        system_prompt = (
            "你是软件测评文档编写助手。根据说明书摘要输出“产品测试功能表”所需内容。"
            "输出为 JSON 对象，包含 items 数组。"
            "每个元素包含字段：一级功能、功能描述。"
            "一级功能为清晰模块名，功能描述必须以“可以”开头，仅一句话，25~60个中文字符。"
            "不要出现编号、引号、冒号，不要出现“本模块/该模块/它”等代词。"
            "只输出 JSON，不要解释。"
        )
        user_prompt = json.dumps({"summary": summary}, ensure_ascii=False)
        response = call_llm_json(runtime, system_prompt, user_prompt, temperature=0.2)
        return normalize_llm_func_items_from_response(response)
    system_prompt = (
        "你是软件测评文档编写助手。请根据每个模块的证据文本，输出“产品测试功能表”所需内容。"
        "输出为 JSON 对象，包含 items 数组。"
        "每个元素包含字段：一级功能、功能描述。"
        "一级功能使用给定 module_title（可清理但不要新增模块）。"
        "功能描述必须以“可以”开头，仅一句话，25~60个中文字符。"
        "不要出现编号、引号、冒号，不要出现“本模块/该模块/它”等代词。"
        "只输出 JSON，不要解释。"
    )
    user_prompt = json.dumps(evidences, ensure_ascii=False)
    response = call_llm_json(runtime, system_prompt, user_prompt, temperature=0.2)
    return normalize_llm_func_items_from_response(response)


def extract_fields_by_prompt(
    runtime: LLMRuntime,
    summary: str,
    full_text: str,
    section_chunks: list[Chunk],
    full_chunks: list[Chunk],
    field_prompts: dict[str, str],
    min_context_chars: int = 400,
    max_excerpt_chars: int = 4000,
) -> dict:
    results: dict[str, object] = {}
    for field, prompt in field_prompts.items():
        system_prompt = (
            "你只需输出JSON对象，且只包含一个字段。字段名必须严格等于要求的字段名，"
            f"字段名为 {field}。{prompt}"
            "先基于证据片段生成；如证据不足，再结合说明书摘要推断补全。"
            "除非摘要也完全缺失相关信息，否则不要输出“待确认”，可输出简短合理概括。"
        )
        context = get_context_for_field(field, section_chunks, full_chunks)
        if len(context) < min_context_chars:
            excerpt = full_text[:max_excerpt_chars].strip()
            evidence_block = (context + "\n\n---\n\n" + excerpt).strip() if excerpt else context
        else:
            evidence_block = context
        user_prompt = (
            f"证据片段：\n{evidence_block}\n\n"
            f"说明书摘要：\n{summary}"
        )
        data = call_llm_json(runtime, system_prompt, user_prompt, temperature=0.2)
        if isinstance(data, dict) and field in data:
            results[field] = data[field]
    return results
