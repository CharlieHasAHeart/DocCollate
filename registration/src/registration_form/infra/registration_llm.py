from __future__ import annotations

import json
from urllib import error, request

from ..core.config import LLMConfig
from .platform_pool import allowed_app_types, normalize_app_type


def _build_prompt(source_text: str) -> str:
    app_types = allowed_app_types()
    allowed = "、".join(app_types)
    return (
        "你是软件登记信息抽取助手。"
        "请根据说明书抽取：软件类型(app_type)、开发语言(env__dev_lang)、"
        "开发平台(env__dev_platform)、运行平台(env__run_platform)、应用领域(product__app_domain)。"
        "只输出JSON对象，格式为："
        "{\"app_type\":\"\",\"env__dev_lang\":\"\",\"env__dev_platform\":\"\",\"env__run_platform\":\"\",\"product__app_domain\":\"\"}。"
        f"其中 app_type 只能是：{allowed}。\n\n"
        f"说明书内容：\n{source_text[:12000]}"
    )


def infer_registration_fields_with_llm(llm: LLMConfig, source_text: str) -> dict[str, str]:
    if not source_text.strip():
        raise ValueError("Empty source_text for registration LLM inference")
    if not llm.base_url or not llm.model:
        raise ValueError("Missing DOCCOLLATE_LLM_BASE_URL or DOCCOLLATE_LLM_MODEL")
    if not llm.api_key:
        raise ValueError("Missing DOCCOLLATE_LLM_API_KEY")

    url = llm.base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": llm.model,
        "messages": [
            {"role": "system", "content": "只返回JSON对象。"},
            {"role": "user", "content": _build_prompt(source_text)},
        ],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {llm.api_key}"}

    req = request.Request(url=url, data=body, headers=headers, method="POST")
    try:
        with request.urlopen(req, timeout=llm.timeout_seconds) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore") if hasattr(exc, "read") else str(exc)
        raise RuntimeError(f"Registration LLM HTTP error: {exc.code} {detail[:300]}") from exc
    except Exception as exc:
        raise RuntimeError(f"Registration LLM call failed: {exc}") from exc

    try:
        data = json.loads(raw)
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        obj = json.loads(content) if isinstance(content, str) else content
    except Exception as exc:
        raise RuntimeError(f"Registration LLM parse failed: {exc}") from exc

    app_type = normalize_app_type(str((obj or {}).get("app_type", "")).strip())
    if app_type not in allowed_app_types():
        raise RuntimeError(f"Registration LLM returned unsupported app_type: {app_type}")

    out = {
        "app_type": app_type,
        "env__dev_lang": str((obj or {}).get("env__dev_lang", "")).strip(),
        "env__dev_platform": str((obj or {}).get("env__dev_platform", "")).strip(),
        "env__run_platform": str((obj or {}).get("env__run_platform", "")).strip(),
        "product__app_domain": str((obj or {}).get("product__app_domain", "")).strip(),
    }
    return out

