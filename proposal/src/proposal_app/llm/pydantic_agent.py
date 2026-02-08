from __future__ import annotations

import inspect
import logging
import os
from typing import Any, Type

from pydantic import BaseModel

from .client import LLMRuntime, chat_text, _loads_json_best_effort


def _set_openai_env(runtime: LLMRuntime) -> None:
    if runtime.api_key:
        os.environ["OPENAI_API_KEY"] = runtime.api_key
    if runtime.base_url:
        os.environ["OPENAI_BASE_URL"] = runtime.base_url


def _model_to_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, BaseModel):
        return value.model_dump()
    if isinstance(value, dict):
        return value
    return {}


def _coerce_missing_patch_payload(data: Any) -> Any:
    """
    Best-effort coercion for MissingPatchOutput:
    - placeholders values must be strings; join list[str] into paragraphs
    - tables cell values must be strings
    """
    if isinstance(data, BaseModel):
        data = data.model_dump()
    if not isinstance(data, dict):
        return data

    placeholders = data.get("placeholders")
    if isinstance(placeholders, dict):
        coerced_ph: dict[str, str] = {}
        for k, v in placeholders.items():
            if not isinstance(k, str):
                continue
            if isinstance(v, str):
                coerced_ph[k] = v
                continue
            if isinstance(v, list):
                parts = [str(x).strip() for x in v if str(x).strip()]
                coerced_ph[k] = "\n\n".join(parts)
                continue
            coerced_ph[k] = "" if v is None else str(v)
        data["placeholders"] = coerced_ph

    tables = data.get("tables")
    if isinstance(tables, dict):
        coerced_tables: dict[str, list[dict[str, str]]] = {}
        for name, rows in tables.items():
            if not isinstance(name, str) or not isinstance(rows, list):
                continue
            out_rows: list[dict[str, str]] = []
            for row in rows:
                if not isinstance(row, dict):
                    continue
                out_row: dict[str, str] = {}
                for ck, cv in row.items():
                    if not isinstance(ck, str):
                        continue
                    if isinstance(cv, str):
                        out_row[ck] = cv
                    elif isinstance(cv, list):
                        parts = [str(x).strip() for x in cv if str(x).strip()]
                        out_row[ck] = "\n".join(parts)
                    else:
                        out_row[ck] = "" if cv is None else str(cv)
                if out_row:
                    out_rows.append(out_row)
            coerced_tables[name] = out_rows
        data["tables"] = coerced_tables

    return data


def run_pydantic_agent(
    *,
    prompt: str,
    runtime: LLMRuntime,
    result_model: Type[BaseModel],
    system_prompt: str,
) -> dict[str, Any]:
    debug_flag = os.getenv("PROPOSAL_DEBUG_LLM", "").strip().lower()
    is_missing_patch = result_model.__name__ == "MissingPatchOutput"
    debug_missing_patch = is_missing_patch and debug_flag in {"1", "true", "yes", "y"}
    debug_snippet = 240

    def _snippet(text: str) -> str:
        return text[:debug_snippet].replace("\n", "\\n")

    def _debug(label: str, text: str, exc: Exception | None = None) -> None:
        if not debug_missing_patch:
            return
        msg = f"[LLM Debug] {label} len={len(text)} snippet={_snippet(text)}"
        if exc is not None:
            msg += f" err={type(exc).__name__}: {exc}"
        logging.getLogger(__name__).info("%s", msg)

    def _repair_json(raw: str) -> dict[str, Any]:
        _debug("missing_patch.raw", raw)
        try:
            data = _loads_json_best_effort(raw)
            if is_missing_patch:
                data = _coerce_missing_patch_payload(data)
            return result_model.model_validate(data).model_dump()
        except Exception as exc:
            _debug("missing_patch.raw_validate_failed", raw, exc)
            repaired = chat_text(
                runtime,
                system_prompt="You are a careful JSON repairer. Output JSON only.",
                user_prompt=f"Fix to valid JSON only:\n{raw}",
                temperature=0.0,
            )
            _debug("missing_patch.repaired", repaired)
            data = _loads_json_best_effort(repaired)
            try:
                if is_missing_patch:
                    data = _coerce_missing_patch_payload(data)
                return result_model.model_validate(data).model_dump()
            except Exception as exc2:
                _debug("missing_patch.repaired_validate_failed", repaired, exc2)
                raise

    try:
        from pydantic_ai import Agent
        from pydantic_ai.models.openai import OpenAIModel
    except Exception:
        raw = chat_text(runtime, system_prompt=system_prompt, user_prompt=prompt, temperature=0.2)
        return _repair_json(raw)

    _set_openai_env(runtime)
    model = OpenAIModel(runtime.model)

    agent_params = {"model": model, "system_prompt": system_prompt}
    if "result_type" in inspect.signature(Agent).parameters:
        agent_params["result_type"] = result_model
    agent = Agent(**agent_params)

    run_sig = inspect.signature(agent.run_sync)
    run_kwargs: dict[str, Any] = {}
    if "result_type" in run_sig.parameters and "result_type" not in agent_params:
        run_kwargs["result_type"] = result_model
    try:
        result = agent.run_sync(prompt, **run_kwargs)
        data = result.data if hasattr(result, "data") else result
        try:
            # Always validate the agent result; pydantic-ai may return partial dicts.
            if is_missing_patch:
                data = _coerce_missing_patch_payload(data)
            return result_model.model_validate(data).model_dump()
        except Exception as exc:
            if debug_missing_patch:
                _debug("missing_patch.agent_validate_failed", str(data), exc)
            raw = chat_text(runtime, system_prompt=system_prompt, user_prompt=prompt, temperature=0.2)
            return _repair_json(raw)
    except Exception:
        raw = chat_text(runtime, system_prompt=system_prompt, user_prompt=prompt, temperature=0.2)
        return _repair_json(raw)
