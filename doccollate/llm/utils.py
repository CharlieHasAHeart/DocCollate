from __future__ import annotations

import json
import logging

from .client import LLMRuntime, chat_json


def call_llm_json(
    runtime: LLMRuntime,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.1,
) -> dict:
    try:
        return chat_json(runtime, system_prompt, user_prompt, temperature=temperature)
    except Exception as exc:
        logging.error("LLM request failed: %s", exc)
        return {}
