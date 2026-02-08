from __future__ import annotations

import json
from urllib import error, request

from ..core.config import LLMConfig

DEV_LANG_OPTIONS = [
    "Java",
    "Python",
    "JavaScript/TypeScript",
    "C/C++",
    "C#",
    "Go",
    "Rust",
    "多语言混合",
]


def _build_prompt(source_text: str) -> str:
    langs = "、".join(DEV_LANG_OPTIONS)
    return (
        "你是软件登记信息抽取助手。"
        "请根据说明书给出：应用领域(product__app_domain)、开发语言(env__dev_lang)。"
        "只输出JSON对象，格式为："
        "{\"product__app_domain\":\"\",\"env__dev_lang\":\"\"}。"
        f"其中 env__dev_lang 只能是：{langs}。"
        "product__app_domain 请给出简洁领域词（如：金融、医疗卫生、教育、互联网服务等）。\n\n"
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

    product_app_domain = str((obj or {}).get("product__app_domain", "")).strip()
    if not product_app_domain:
        raise RuntimeError("Registration LLM returned empty product__app_domain")
    env_dev_lang = str((obj or {}).get("env__dev_lang", "")).strip()
    if env_dev_lang not in DEV_LANG_OPTIONS:
        raise RuntimeError(f"Registration LLM returned unsupported env__dev_lang: {env_dev_lang}")

    out = {
        "product__app_domain": product_app_domain,
        "env__dev_lang": env_dev_lang,
    }
    return out
