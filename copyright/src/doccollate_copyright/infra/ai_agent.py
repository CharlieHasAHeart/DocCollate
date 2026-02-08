from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

from ..core.config import LLMConfig
from ..core.models import CopyrightOutputSchema
from .env_pools import ENV_CONFIG_POOLS, ENV_FIELD_KEYS, serialize_pools_for_prompt
from .retrieval import retrieve_field_contexts

logger = logging.getLogger(__name__)

SINGLE_PASS_SYSTEM_PROMPT = (
    "你是软件著作权登记申请表字段抽取器。"
    "你会收到字段级检索片段，请结合片段与原文抽取并规范化字段。"
    "禁止编造公司信息；有依据时尽量填写，不确定则写“待补充”占位。"
    "输出必须满足 schema。"
)

ENV_OUTPUT_RULES = """\
你必须严格按以下规范写入字段（禁止空话如“主流/常规/不限/若干/可部署”）：
1) tech__hardware_dev（软件开发硬件环境）
- 结构固定为两行：
  最低配置：CPU：___；内存：___；存储：___；网络：___；
  推荐配置：CPU：___；内存：___；存储：___；网络：___；
2) tech__hardware_run（软件运行硬件环境）
- 至少包含三行：
  客户端（最低/推荐）：CPU___；内存___；存储___；网络___；
  服务器端（最低/推荐）：CPU___；内存___；存储___；网络___；
  数据库/中间件服务器（最低/推荐）：CPU___；内存___；存储___；网络___；
3) tech__os_dev（开发该软件的操作系统）
- 格式：OS 名称 + 版本范围 + 架构（64位），列出1-3种。
4) tech__dev_tools（软件开发环境/开发工具）
- 至少包含：IDE/编辑器、版本管理、语言/SDK/运行时、构建/依赖管理。
5) tech__os_run（软件运行平台/操作系统）
- 按角色列出客户端和服务器端平台，包含 OS + 版本范围。
6) tech__run_support（软件运行支撑环境/支持软件）
- 至少两类：运行时/应用环境 + 数据支撑；B/S需写 Web服务/代理。
"""


class CandidateScore(BaseModel):
    candidate_id: str
    score: float = Field(ge=0, le=100)


class FieldPoolScoring(BaseModel):
    scores: list[CandidateScore]
    selected_candidate_id: str
    reason: str = ""


class EnvPoolSelectionSchema(BaseModel):
    tech__hardware_dev: FieldPoolScoring
    tech__hardware_run: FieldPoolScoring
    tech__os_dev: FieldPoolScoring
    tech__dev_tools: FieldPoolScoring
    tech__os_run: FieldPoolScoring
    tech__run_support: FieldPoolScoring


POOL_SELECT_SYSTEM_PROMPT = (
    "你是配置池匹配专家。"
    "你会看到项目文本和六个字段的候选配置池。"
    "请按相关性为每个字段的所有候选都给出0-100分，并给出最终选中项。"
    "必须每个字段都输出完整 scores 列表，并给出 selected_candidate_id。"
)


def _build_single_prompt(
    source_text: str,
    field_contexts: dict[str, list[dict[str, object]]],
    seed_data: dict[str, Any] | None = None,
) -> str:
    seed_json = json.dumps(seed_data or {}, ensure_ascii=False, indent=2)
    ctx_json = json.dumps(field_contexts, ensure_ascii=False, indent=2)
    return (
        "任务：根据字段级检索结果和原文，抽取软件著作权登记申请字段。\n"
        "优先保留 seed_data 的值，如文本中有更清晰证据再修正。\n\n"
        f"{ENV_OUTPUT_RULES}\n\n"
        f"seed_data:\n{seed_json}\n\n"
        f"field_contexts:\n{ctx_json}\n\n"
        f"source_text:\n{source_text}\n"
    )


def _build_pool_select_prompt(
    source_text: str,
    field_contexts: dict[str, list[dict[str, object]]],
) -> str:
    pools_json = json.dumps(serialize_pools_for_prompt(), ensure_ascii=False, indent=2)
    ctx_json = json.dumps(field_contexts, ensure_ascii=False, indent=2)
    return (
        "任务：对6个目标字段分别对候选池逐项评分并选择最优配置。\n"
        "选择标准：与项目类型、部署形态、技术栈和运行环境描述的匹配度。\n"
        "要求：每个字段都要给出 scores 列表（每个候选都必须出现一次），并给出 selected_candidate_id 与简短 reason。\n\n"
        f"field_contexts:\n{ctx_json}\n\n"
        f"candidate_pools:\n{pools_json}\n\n"
        f"source_text:\n{source_text}\n"
    )


def _build_model(llm: LLMConfig) -> OpenAIModel:
    model_name = (llm.final_model or llm.model or "gpt-4o-mini").strip()
    logger.info("Initializing LLM model: %s", model_name)
    provider = OpenAIProvider(
        base_url=(llm.base_url or None),
        api_key=(llm.api_key or None),
    )
    return OpenAIModel(model_name=model_name, provider=provider)


def _is_blank(value: str) -> bool:
    return not value or not value.strip()


def _default_hardware_dev() -> str:
    return (
        "最低配置：CPU：待补充；内存：待补充；存储：待补充；网络：待补充；\n"
        "推荐配置：CPU：待补充；内存：待补充；存储：待补充；网络：待补充；"
    )


def _default_hardware_run() -> str:
    return (
        "客户端（最低/推荐）：CPU待补充/待补充；内存待补充/待补充；存储待补充/待补充；网络待补充/待补充；\n"
        "服务器端（最低/推荐）：CPU待补充/待补充；内存待补充/待补充；存储待补充/待补充；网络待补充/待补充；\n"
        "数据库/中间件服务器（最低/推荐）：CPU待补充/待补充；内存待补充/待补充；存储待补充/待补充；网络待补充/待补充；"
    )


def _default_os_dev() -> str:
    return "Windows 10/11（64位）；Ubuntu 20.04+（64位）；macOS 12+（64位）"


def _default_dev_tools() -> str:
    return (
        "IDE/编辑器：待补充；版本管理：Git（版本待补充）；"
        "语言/SDK/运行时：待补充；构建/依赖管理：待补充。"
    )


def _default_os_run() -> str:
    return "客户端运行平台：浏览器（Windows 10/11 或 macOS 12+）；服务器运行平台：Linux（Ubuntu 20.04+）。"


def _default_run_support() -> str:
    return "运行时/应用环境：待补充；Web服务/代理：待补充；数据库/存储：待补充。"


def _coerce_env_fields(data: dict[str, Any]) -> dict[str, Any]:
    out = dict(data)

    if _is_blank(str(out.get("tech__hardware_dev", ""))):
        out["tech__hardware_dev"] = _default_hardware_dev()
    if _is_blank(str(out.get("tech__hardware_run", ""))):
        out["tech__hardware_run"] = _default_hardware_run()
    if _is_blank(str(out.get("tech__os_dev", ""))):
        out["tech__os_dev"] = _default_os_dev()
    if _is_blank(str(out.get("tech__dev_tools", ""))):
        out["tech__dev_tools"] = _default_dev_tools()
    if _is_blank(str(out.get("tech__os_run", ""))):
        out["tech__os_run"] = _default_os_run()
    if _is_blank(str(out.get("tech__run_support", ""))):
        out["tech__run_support"] = _default_run_support()

    return out


def _build_pool_seed(selection: EnvPoolSelectionSchema) -> tuple[dict[str, str], dict[str, dict[str, object]]]:
    seed: dict[str, str] = {}
    selected_info: dict[str, dict[str, object]] = {}
    selected = selection.model_dump()
    for field in ENV_FIELD_KEYS:
        field_data = selected.get(field) or {}
        score_items = field_data.get("scores", []) if isinstance(field_data, dict) else []
        top_candidate_id = ""
        top_score = -1.0
        for item in score_items:
            if not isinstance(item, dict):
                continue
            cid = str(item.get("candidate_id", "")).strip()
            score = float(item.get("score", 0))
            if score > top_score:
                top_score = score
                top_candidate_id = cid

        model_selected = str(field_data.get("selected_candidate_id", "")).strip() if isinstance(field_data, dict) else ""
        candidate_id = top_candidate_id or model_selected
        candidates = ENV_CONFIG_POOLS.get(field, [])
        matched = next((c for c in candidates if c.candidate_id == candidate_id), None)
        if not matched and candidates:
            matched = candidates[0]
        if matched:
            seed[field] = matched.content
            selected_info[field] = {
                "candidate_id": matched.candidate_id,
                "score": top_score if top_score >= 0 else None,
                "model_selected_candidate_id": model_selected,
            }
    return seed, selected_info


def _default_pool_seed() -> dict[str, str]:
    seed: dict[str, str] = {}
    for field in ENV_FIELD_KEYS:
        candidates = ENV_CONFIG_POOLS.get(field, [])
        if candidates:
            seed[field] = candidates[0].content
    return seed


def extract_output_with_agent(
    llm: LLMConfig,
    source_text: str,
    seed_data: dict[str, Any] | None = None,
    debug_dir: Path | None = None,
    base_name: str = "llm",
) -> CopyrightOutputSchema:
    model = _build_model(llm)
    field_contexts = retrieve_field_contexts(source_text, top_k=3)

    pool_agent = Agent(
        model,
        output_type=EnvPoolSelectionSchema,
        system_prompt=POOL_SELECT_SYSTEM_PROMPT,
        retries=2,
    )
    logger.info("LLM stage 1/2: retrieval contexts + pool scoring")
    pool_selection: EnvPoolSelectionSchema | None = None
    pool_selected_info: dict[str, dict[str, object]] = {}
    pool_seed: dict[str, str] = {}
    try:
        pool_result = pool_agent.run_sync(_build_pool_select_prompt(source_text, field_contexts))
        pool_selection = pool_result.output
        pool_seed, pool_selected_info = _build_pool_seed(pool_selection)
    except Exception as exc:
        logger.warning("Pool scoring failed, fallback to default pool seed: %s", exc)
        pool_seed = _default_pool_seed()

    merged_seed_data = dict(seed_data or {})
    merged_seed_data.update(pool_seed)

    agent = Agent(
        model,
        output_type=CopyrightOutputSchema,
        system_prompt=SINGLE_PASS_SYSTEM_PROMPT,
        retries=2,
    )
    if debug_dir:
        debug_dir.mkdir(parents=True, exist_ok=True)
        (debug_dir / f"{base_name}.stage1.json").write_text(
            json.dumps(
                {
                    "seed_data": seed_data or {},
                    "field_contexts": field_contexts,
                    "pool_selection": pool_selection.model_dump() if pool_selection else {},
                    "pool_selected_info": pool_selected_info,
                    "pool_seed": pool_seed,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    logger.info("LLM stage 2/2: single-pass structured generation")
    try:
        result = agent.run_sync(
            _build_single_prompt(source_text, field_contexts, seed_data=merged_seed_data)
        )
        stage2_data = _coerce_env_fields(result.output.model_dump(exclude_none=True))
        final_output = CopyrightOutputSchema.model_validate(stage2_data)
    except Exception as exc:
        logger.error("Stage2 structured generation failed, fallback to seed-only output: %s", exc)
        fallback_data = _coerce_env_fields(dict(merged_seed_data))
        final_output = CopyrightOutputSchema.model_validate(fallback_data)
    if debug_dir:
        (debug_dir / f"{base_name}.stage2.json").write_text(
            json.dumps(final_output.model_dump(exclude_none=True), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    logger.info("LLM pipeline completed")
    return final_output
