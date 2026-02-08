from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

try:
    from openai import OpenAI
except ModuleNotFoundError:
    OpenAI = Any

from ..config import LLMConfig


@dataclass(frozen=True)
class LLMRuntime:
    client: OpenAI
    model: str
    api_key: str
    base_url: str | None


def _escape_control_chars_in_strings(text: str) -> str:
    out: list[str] = []
    in_string = False
    escaped = False
    for ch in text:
        if in_string:
            if escaped:
                out.append(ch)
                escaped = False
                continue
            if ch == "\\":
                out.append(ch)
                escaped = True
                continue
            if ch == "\"":
                out.append(ch)
                in_string = False
                continue
            if ch == "\n":
                out.append("\\n")
                continue
            if ch == "\r":
                out.append("\\r")
                continue
            if ch == "\t":
                out.append("\\t")
                continue
            code = ord(ch)
            if code < 0x20:
                out.append(f"\\u{code:04x}")
                continue
            out.append(ch)
        else:
            if ch == "\"":
                in_string = True
            out.append(ch)
    return "".join(out)


def _sanitize_json_text(text: str) -> str:
    s = text.strip()
    if not s:
        return "{}"
    start = s.find("{")
    end = s.rfind("}")
    if start != -1 and end != -1 and end > start:
        s = s[start : end + 1]

    s = s.lstrip("\ufeff")
    s = re.sub(r"\n[ \t]*\.[ \t]*(?=\n)", "\n", s)
    s = re.sub(r"(\{\s*)\.(\s*\")", r"\1\2", s)
    s = re.sub(r",\s*(\}|\])", r"\1", s)
    s = re.sub(r"\bNone\b", "null", s)
    s = re.sub(r"\bTrue\b", "true", s)
    s = re.sub(r"\bFalse\b", "false", s)
    return s


def _raw_decode_first(text: str) -> dict | None:
    try:
        obj, _ = json.JSONDecoder().raw_decode(text)
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


def _loads_json_best_effort(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        first = _raw_decode_first(text)
        if isinstance(first, dict):
            return first
        try:
            escaped = _escape_control_chars_in_strings(text)
            return json.loads(escaped)
        except json.JSONDecodeError:
            first = _raw_decode_first(escaped)
            if isinstance(first, dict):
                return first
            sanitized = _sanitize_json_text(escaped)
            try:
                return json.loads(sanitized)
            except json.JSONDecodeError:
                first = _raw_decode_first(sanitized)
                if isinstance(first, dict):
                    return first
                raise


def init_llm(llm_config: LLMConfig, api_key: str | None = None, base_url: str | None = None, model: str | None = None) -> LLMRuntime:
    if OpenAI is Any:
        raise ModuleNotFoundError("Missing dependency: openai")
    resolved_key = (api_key or llm_config.api_key).strip()
    if not resolved_key:
        raise ValueError("Missing LLM api_key in config or CLI override")
    resolved_base_url = (base_url or llm_config.base_url).strip() or None
    resolved_model = (model or llm_config.model).strip() or "gpt-4o-mini"
    if resolved_base_url:
        client = OpenAI(api_key=resolved_key, base_url=resolved_base_url)
    else:
        client = OpenAI(api_key=resolved_key)
    return LLMRuntime(client=client, model=resolved_model, api_key=resolved_key, base_url=resolved_base_url)


def chat_json(
    runtime: LLMRuntime,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.1,
    max_tokens: int | None = 64000,
) -> dict:
    response = runtime.client.chat.completions.create(
        model=runtime.model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=temperature,
        max_tokens=max_tokens,
    )
    choice = response.choices[0]
    content = choice.message.content or "{}"
    finish_reason = getattr(choice, "finish_reason", None)
    if finish_reason == "length":
        usage = getattr(response, "usage", None)
        prompt_tokens = getattr(usage, "prompt_tokens", None) if usage else None
        completion_tokens = getattr(usage, "completion_tokens", None) if usage else None
        total_tokens = getattr(usage, "total_tokens", None) if usage else None
        content_len_chars = len(content)
        content_len_bytes = len(content.encode("utf-8"))
        snippet = content[:200].replace("\n", "\\n")
        raise ValueError(
            "LLM JSON response truncated (finish_reason=length). "
            f"len_chars={content_len_chars} len_bytes={content_len_bytes} "
            f"prompt_tokens={prompt_tokens} completion_tokens={completion_tokens} total_tokens={total_tokens} "
            f"max_tokens={max_tokens}. Snippet: {snippet}..."
        )
    try:
        return _loads_json_best_effort(content)
    except Exception as exc:
        snippet = content[:200].replace("\n", "\\n")
        if isinstance(exc, json.JSONDecodeError):
            ctx_left = max(0, exc.pos - 120)
            ctx_right = min(len(content), exc.pos + 120)
            context = content[ctx_left:ctx_right].replace("\n", "\\n")
            raise ValueError(
                "LLM output is not valid JSON. "
                f"json_error={exc.msg} line={exc.lineno} col={exc.colno} pos={exc.pos}. "
                f"context={context}. Snippet: {snippet}..."
            ) from exc
        raise ValueError(f"LLM output is not valid JSON. Snippet: {snippet}...") from exc


def chat_text(
    runtime: LLMRuntime,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.2,
    max_tokens: int | None = 64000,
) -> str:
    response = runtime.client.chat.completions.create(
        model=runtime.model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return (response.choices[0].message.content or "").strip()
