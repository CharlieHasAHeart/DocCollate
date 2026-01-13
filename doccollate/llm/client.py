from __future__ import annotations

import json
from dataclasses import dataclass

from openai import OpenAI

from ..config import LLMConfig


@dataclass(frozen=True)
class LLMRuntime:
    client: OpenAI
    model: str


def init_llm(llm_config: LLMConfig, api_key: str | None = None, base_url: str | None = None, model: str | None = None) -> LLMRuntime:
    resolved_key = (api_key or llm_config.api_key).strip()
    if not resolved_key:
        raise ValueError("Missing LLM api_key in config or CLI override")
    resolved_base_url = (base_url or llm_config.base_url).strip() or None
    resolved_model = (model or llm_config.model).strip() or "gpt-4o-mini"
    if resolved_base_url:
        client = OpenAI(api_key=resolved_key, base_url=resolved_base_url)
    else:
        client = OpenAI(api_key=resolved_key)
    return LLMRuntime(client=client, model=resolved_model)


def chat_json(runtime: LLMRuntime, system_prompt: str, user_prompt: str, temperature: float = 0.1) -> dict:
    response = runtime.client.chat.completions.create(
        model=runtime.model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=temperature,
    )
    content = response.choices[0].message.content or "{}"
    return json.loads(content)


def chat_text(runtime: LLMRuntime, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
    response = runtime.client.chat.completions.create(
        model=runtime.model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
    )
    return (response.choices[0].message.content or "").strip()
