from __future__ import annotations

import json
import logging
from urllib import error, request

from ..core.config import LLMConfig
from .profile_pool import allowed_app_types, normalize_app_type

logger = logging.getLogger(__name__)

def _build_prompt(source_text: str) -> str:
    app_types = allowed_app_types()
    if not app_types:
        return source_text[:12000]
    allowed = "、".join(app_types)
    return (
        "你是软件系统类型判定助手。"
        "根据提供的说明书内容，在给定候选类型中选择最匹配的一项。"
        "必须只输出JSON对象，不要输出其它文本。"
        "输出格式: {\"app_type\":\"...\",\"reason\":\"...\"}。"
        f"app_type 只能是：{allowed}。\n\n"
        "说明书内容：\n"
        f"{source_text[:12000]}"
    )


def infer_app_type_via_llm(llm: LLMConfig, source_text: str) -> str:
    app_types = allowed_app_types()
    if not app_types:
        raise ValueError("No app types loaded from profile pool")
    if not source_text.strip():
        raise ValueError("Empty source_text for app_type inference")
    if not llm.base_url or not llm.model:
        raise ValueError("Missing DOCCOLLATE_LLM_BASE_URL or DOCCOLLATE_LLM_MODEL")
    if not llm.api_key:
        raise ValueError("Missing DOCCOLLATE_LLM_API_KEY")

    url = llm.base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": llm.model,
        "messages": [
            {"role": "system", "content": "只返回JSON。"},
            {"role": "user", "content": _build_prompt(source_text)},
        ],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
    }
    if llm.api_key:
        headers["Authorization"] = f"Bearer {llm.api_key}"

    req = request.Request(url=url, data=body, headers=headers, method="POST")
    try:
        with request.urlopen(req, timeout=llm.timeout_seconds) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore") if hasattr(exc, "read") else str(exc)
        raise RuntimeError(f"LLM app_type inference HTTP error: {exc.code} {detail[:300]}") from exc
    except Exception as exc:
        raise RuntimeError(f"LLM app_type inference failed: {exc}") from exc

    try:
        data = json.loads(raw)
        content = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        obj = json.loads(content) if isinstance(content, str) else content
        app_type = normalize_app_type(str((obj or {}).get("app_type", "")).strip())
        if app_type in app_types:
            logger.info("LLM inferred app_type=%s", app_type)
            return app_type
        raise RuntimeError(f"LLM returned unsupported app_type: {app_type}")
    except Exception as exc:
        raise RuntimeError(f"Failed to parse LLM app_type response: {exc}") from exc
