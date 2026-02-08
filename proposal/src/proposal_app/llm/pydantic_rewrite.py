from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from .client import LLMRuntime
from .pydantic_agent import run_pydantic_agent


class DocRewriteOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    placeholders: dict[str, str] = {}


class ParagraphFix(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str
    index: int
    text: str


class ParagraphRewriteOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    paragraph_fixes: list[ParagraphFix] = []


class CombinedRewriteOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    placeholders: dict[str, str] = {}
    paragraph_fixes: list[ParagraphFix] = []


class MissingPatchOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    placeholders: dict[str, str] = {}
    tables: dict[str, list[dict[str, str]]] = {}


def call_doc_rewrite_with_pydantic(prompt: str, runtime: LLMRuntime) -> dict[str, Any]:
    return run_pydantic_agent(
        prompt=prompt,
        runtime=runtime,
        result_model=DocRewriteOutput,
        system_prompt="You are a careful JSON generator. Output JSON only.",
    )


def call_paragraph_rewrite_with_pydantic(prompt: str, runtime: LLMRuntime) -> dict[str, Any]:
    return run_pydantic_agent(
        prompt=prompt,
        runtime=runtime,
        result_model=ParagraphRewriteOutput,
        system_prompt="You are a careful JSON generator. Output JSON only.",
    )


def call_combined_rewrite_with_pydantic(prompt: str, runtime: LLMRuntime) -> dict[str, Any]:
    return run_pydantic_agent(
        prompt=prompt,
        runtime=runtime,
        result_model=CombinedRewriteOutput,
        system_prompt="You are a careful JSON generator. Output JSON only.",
    )


def call_missing_patch_with_pydantic(prompt: str, runtime: LLMRuntime) -> dict[str, Any]:
    return run_pydantic_agent(
        prompt=prompt,
        runtime=runtime,
        result_model=MissingPatchOutput,
        system_prompt="You are a careful JSON generator. Output JSON only.",
    )
