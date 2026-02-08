from __future__ import annotations

import json
import logging
from urllib import error, request

from ..core.config import LLMConfig
from ..core.models import LLMFunctionSchema
from .retrieval import TextChunk

logger = logging.getLogger(__name__)


def _build_prompt(chunks: list[TextChunk]) -> str:
    payload = [
        {"title": c.title, "content": c.content[:1200]}
        for c in chunks
    ]
    return (
        "你是软件功能结构抽取助手。"
        "请基于提供的说明书检索片段，输出'一级功能+二级功能+二级功能描述'。"
        "要求：\n"
        "1) 一级功能是模块级名称（如计划排程工作台）。\n"
        "2) 每个一级功能至少给出1个二级功能。\n"
        "3) 二级功能描述用简短中文，以'可以'开头，不超过30字。\n"
        "4) 只输出JSON对象，严格遵循 schema:"
        "{\"primary_functions\":[{\"name\":\"\",\"secondary\":[{\"name\":\"\",\"desc\":\"\"}]}]}。\n\n"
        f"检索片段: {json.dumps(payload, ensure_ascii=False)}"
    )


def infer_functions_with_llm(llm: LLMConfig, chunks: list[TextChunk]) -> LLMFunctionSchema:
    if not chunks:
        raise ValueError("LLM inference requires non-empty retrieved chunks")
    if not llm.base_url or not llm.model:
        raise ValueError("Missing DOCCOLLATE_LLM_BASE_URL or DOCCOLLATE_LLM_MODEL")
    if not llm.api_key:
        raise ValueError("Missing DOCCOLLATE_LLM_API_KEY")

    url = llm.base_url.rstrip("/") + "/chat/completions"
    req_payload = {
        "model": llm.model,
        "messages": [
            {"role": "system", "content": "只返回JSON对象。"},
            {"role": "user", "content": _build_prompt(chunks)},
        ],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }
    body = json.dumps(req_payload, ensure_ascii=False).encode("utf-8")

    headers = {"Content-Type": "application/json"}
    if llm.api_key:
        headers["Authorization"] = f"Bearer {llm.api_key}"

    req = request.Request(url=url, data=body, headers=headers, method="POST")
    try:
        with request.urlopen(req, timeout=llm.timeout_seconds) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore") if hasattr(exc, "read") else str(exc)
        raise RuntimeError(f"Function LLM HTTP error: {exc.code} {detail[:300]}") from exc
    except Exception as exc:
        raise RuntimeError(f"Function LLM call failed: {exc}") from exc

    try:
        data = json.loads(raw)
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        obj = json.loads(content) if isinstance(content, str) else content
        return LLMFunctionSchema.model_validate(obj)
    except Exception as exc:
        raise RuntimeError(f"Function LLM parse/validate failed: {exc}") from exc
