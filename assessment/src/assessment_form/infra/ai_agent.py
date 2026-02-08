from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from openai import OpenAI
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

from ..core.config import LLMConfig
from ..core.models import AssessmentOutputSchema
from .field_pools import load_field_pools
from .retrieval import retrieve_field_contexts

logger = logging.getLogger(__name__)

POOL_TOP_N = 5
POOL_TIMEOUT_SEC = 20
POOL_MAX_ATTEMPTS = 2

SYSTEM_PROMPT = (
    "你是产品评估申请表结构化填表助手。"
    "你会收到字段级检索结果和说明书全文。"
    "你必须输出 AssessmentOutputSchema 对应的结构化字段，禁止输出额外键。"
    "禁止输出“待补充/待确认/TBD”等占位词；证据不足时也要给出保守且可落表的确定性表达。"
)

NORM_RULES = """\
填写规范（必须遵守）：
1) product__service_object：30-80字，包含“对象+业务+价值”。
2) product__main_functions：按“功能点：详细描述”输出，建议4-6个功能点，总字数不超过200字。
3) product__tech_specs：2-6条可验证技术能力，优先并发/响应/可用性/安全/兼容，避免“先进稳定高效”空词。
4) app__product_type_text：必须从候选池中选择。
5) env__memory_req：纯数字字符串（单位由表格MB承担），例如“512”“1024”。
6) env__os + env__os_version：必须一致，不得出现系统与版本矛盾；B/S需体现客户端与服务器角色。
7) env__language：1-3种主要语言，需与开发平台工具链一致。
8) env__sw_dev_platform：至少包含 开发OS + IDE/编辑器 + SDK/运行时 + 构建/依赖工具 + 版本管理。
9) env__hw_dev_platform：至少包含 CPU/内存/存储 三要素，尽量加网络描述。
10) app__category_assess：必须从候选池中选择。
11) assess__product_mode_val 只能是 pure 或 embedded。
12) 对“软驱/光驱/声卡/显卡”若无证据，默认 false（不依赖）。
13) assess__is_self_dev / assess__has_docs / assess__has_source 无反证时默认 true。
"""


class CandidateScore(BaseModel):
    candidate_id: str
    score: float = Field(ge=0, le=100)


class FieldPoolScoreResult(BaseModel):
    selected_candidate_id: str = ""
    scores: list[CandidateScore] = Field(default_factory=list)
    reason: str = ""


def _build_model(llm: LLMConfig) -> OpenAIModel:
    model_name = (llm.model or "gpt-4o-mini").strip() or "gpt-4o-mini"
    provider = OpenAIProvider(base_url=(llm.base_url or None), api_key=(llm.api_key or None))
    return OpenAIModel(model_name=model_name, provider=provider)


def _build_prompt(
    source_text: str,
    field_contexts: dict[str, list[dict[str, object]]],
    seed_data: dict[str, Any] | None = None,
) -> str:
    return (
        "任务：根据检索片段与原文生成评估申请字段。\n"
        "优先保留 seed_data 已明确的值；若与证据冲突，以证据更充分者为准。\n\n"
        f"{NORM_RULES}\n\n"
        f"seed_data:\n{json.dumps(seed_data or {}, ensure_ascii=False, indent=2)}\n\n"
        f"field_contexts:\n{json.dumps(field_contexts, ensure_ascii=False, indent=2)}\n\n"
        f"source_text:\n{source_text}\n"
    )


def _build_pool_prompt(
    field: str,
    source_text: str,
    field_contexts: dict[str, list[dict[str, object]]],
    candidates: list[dict[str, str]],
) -> str:
    return (
        "你只需要对一个字段的候选池评分。\n"
        "输出 JSON：selected_candidate_id, scores, reason。\n"
        f"要求：scores 只保留最相关的前{POOL_TOP_N}项，不需要全量。\n"
        "score 取值 0-100。\n\n"
        f"field: {field}\n"
        f"contexts:\n{json.dumps(field_contexts.get(field, []), ensure_ascii=False, indent=2)}\n\n"
        f"candidates:\n{json.dumps(candidates, ensure_ascii=False, indent=2)}\n\n"
        f"source_text:\n{source_text}\n"
    )


def _call_pool_llm_json(llm: LLMConfig, user_prompt: str) -> dict[str, Any]:
    client = OpenAI(
        api_key=llm.api_key,
        base_url=(llm.base_url or None),
        max_retries=0,
        timeout=POOL_TIMEOUT_SEC,
    )
    resp = client.chat.completions.create(
        model=llm.model,
        messages=[
            {
                "role": "system",
                "content": "你是软件分类打分器。只返回JSON，不要解释文本。",
            },
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
    )
    content = (resp.choices[0].message.content or "{}").strip()
    return json.loads(content)


def _coerce_pool_result(raw: dict[str, Any], valid_ids: set[str]) -> FieldPoolScoreResult:
    selected = str(raw.get("selected_candidate_id", "")).strip()
    reason = str(raw.get("reason", "")).strip()

    scores: list[CandidateScore] = []
    for item in raw.get("scores", []) if isinstance(raw.get("scores"), list) else []:
        if not isinstance(item, dict):
            continue
        cid = str(item.get("candidate_id", "")).strip()
        if cid not in valid_ids:
            continue
        try:
            score = float(item.get("score", 0))
        except Exception:
            score = 0.0
        score = max(0.0, min(100.0, score))
        scores.append(CandidateScore(candidate_id=cid, score=score))

    # Deduplicate by best score for same candidate.
    best_by_id: dict[str, float] = {}
    for item in scores:
        prev = best_by_id.get(item.candidate_id)
        if prev is None or item.score > prev:
            best_by_id[item.candidate_id] = item.score

    compact = [CandidateScore(candidate_id=k, score=v) for k, v in best_by_id.items()]
    compact.sort(key=lambda x: x.score, reverse=True)
    compact = compact[:POOL_TOP_N]

    if selected not in valid_ids:
        selected = compact[0].candidate_id if compact else ""

    return FieldPoolScoreResult(selected_candidate_id=selected, scores=compact, reason=reason)


def _score_single_pool_field(
    llm: LLMConfig,
    field: str,
    source_text: str,
    field_contexts: dict[str, list[dict[str, object]]],
) -> tuple[str, dict[str, Any]]:
    pools = load_field_pools()
    candidates = pools.get(field, [])
    if not candidates:
        return "", {"error": "missing_candidates"}

    candidate_payload = [{"candidate_id": c.candidate_id, "label": c.label} for c in candidates]
    valid_ids = {c.candidate_id for c in candidates}

    last_error = ""
    for attempt in range(1, POOL_MAX_ATTEMPTS + 1):
        try:
            raw = _call_pool_llm_json(
                llm,
                _build_pool_prompt(field, source_text, field_contexts, candidate_payload),
            )
            parsed = _coerce_pool_result(raw, valid_ids)
            selected = parsed.selected_candidate_id
            if not selected:
                selected = parsed.scores[0].candidate_id if parsed.scores else candidates[0].candidate_id
            chosen = next((c for c in candidates if c.candidate_id == selected), candidates[0])
            return chosen.label, {
                "attempt": attempt,
                "selected_candidate_id": selected,
                "resolved_label": chosen.label,
                "scores": [s.model_dump() for s in parsed.scores],
                "reason": parsed.reason,
            }
        except Exception as exc:
            last_error = str(exc)

    # Fallback: deterministic first candidate, no long retries.
    fallback = candidates[0]
    return fallback.label, {
        "attempt": POOL_MAX_ATTEMPTS,
        "selected_candidate_id": fallback.candidate_id,
        "resolved_label": fallback.label,
        "scores": [],
        "reason": "fallback_first_candidate",
        "error": last_error,
    }


def _ensure_defaults(data: dict[str, Any]) -> dict[str, Any]:
    out = dict(data)
    memory = str(out.get("env__memory_req", "") or "").strip()
    nums = re.findall(r"\d+", memory)
    out["env__memory_req"] = nums[0] if nums else "512"

    mode = str(out.get("assess__product_mode_val", "") or "").strip().lower()
    out["assess__product_mode_val"] = "embedded" if mode == "embedded" else "pure"

    for key in (
        "assess__support_floppy",
        "assess__support_sound",
        "assess__support_cdrom",
        "assess__support_gpu",
        "assess__support_other",
    ):
        out[key] = bool(out.get(key, False))
    for key in ("assess__is_self_dev", "assess__has_docs", "assess__has_source"):
        out[key] = bool(out.get(key, True))

    defaults = {
        "product__service_object": "面向业务操作与管理人员，提供业务协同与流程管理能力，用于提升执行效率与过程可追溯性。",
        "product__main_functions": "用户与权限管理；业务数据管理；流程编排与执行；统计分析与报表；系统配置与运维",
        "product__tech_specs": "支持基于角色的权限控制；支持关键业务流程可追踪；支持常用浏览器兼容访问",
        "app__product_type_text": "应用软件-信息管理软件",
        "env__memory_req": "512",
        "env__hardware_model": "通用计算机",
        "env__os": "客户端：Windows 10/11；服务器：Linux",
        "env__os_version": "客户端：Windows 10/11；服务器：Ubuntu 22.04 LTS",
        "env__language": "Python",
        "env__sw_dev_platform": "Windows 10/11；VS Code；Python 3.10+；pip；Git",
        "env__hw_dev_platform": "CPU：4核；内存：8GB；存储：256GB SSD；网络：千兆以太网",
        "env__database": "PostgreSQL 13",
        "env__soft_scale": "中",
        "app__category_assess": "30 其它计算机应用软件和信息服务",
    }
    for key, value in defaults.items():
        if not str(out.get(key, "") or "").strip():
            out[key] = value

    _sanitize_placeholders(out)
    out["product__main_functions"] = _normalize_main_functions(str(out.get("product__main_functions", "") or ""))

    for key in (
        "assess__support_floppy",
        "assess__support_sound",
        "assess__support_cdrom",
        "assess__support_gpu",
        "assess__support_other",
    ):
        if key not in out:
            out[key] = False
    return out


def _sanitize_placeholders(data: dict[str, Any]) -> None:
    placeholder_re = re.compile(
        r"(待补充|待确认|tbd|todo|n/?a|未知|未明确|未明确指定|未说明|未提供|不详|暂无)",
        re.IGNORECASE,
    )
    fallback_by_key = {
        "product__service_object": "面向业务操作与管理人员，提供业务协同与流程管理能力，用于提升执行效率与过程可追溯性。",
        "product__main_functions": "用户与权限：支持账号、角色和权限分配；业务数据管理：支持数据录入、校验与查询；流程编排：支持流程配置与执行跟踪",
        "product__tech_specs": "支持基于角色的权限控制；支持关键业务流程可追踪；支持常用浏览器兼容访问",
        "app__product_type_text": "应用软件-信息管理软件",
        "env__memory_req": "512",
        "env__hardware_model": "通用计算机",
        "env__os": "客户端：Windows 10/11；服务器：Linux",
        "env__language": "Python",
        "env__database": "PostgreSQL 13",
        "env__soft_scale": "中",
        "env__os_version": "客户端：Windows 10/11；服务器：Ubuntu 22.04 LTS",
        "env__hw_dev_platform": "CPU：4核；内存：8GB；存储：256GB SSD；网络：千兆以太网",
        "env__sw_dev_platform": "Windows 10/11；VS Code；Python 3.10+；pip；Git",
        "app__category_assess": "30 其它计算机应用软件和信息服务",
    }
    for key, value in list(data.items()):
        if not isinstance(value, str):
            continue
        txt = value.strip()
        if not txt:
            continue
        if placeholder_re.search(txt):
            data[key] = fallback_by_key.get(key, "")


def _normalize_main_functions(text: str, max_chars: int = 200) -> str:
    raw = (text or "").strip()
    if not raw:
        raw = "用户与权限；业务数据管理；流程编排；统计分析；系统运维"

    parts = [p.strip() for p in re.split(r"[；;\n]+", raw) if p.strip()]
    if len(parts) <= 1 and "、" in raw:
        parts = [p.strip() for p in raw.split("、") if p.strip()]

    normalized: list[str] = []
    for part in parts:
        clean = re.sub(r"^\s*\d+[\.\)、\s]*", "", part).strip("。；;，, ")
        if not clean:
            continue
        if "：" in clean:
            name, desc = [x.strip() for x in clean.split("：", 1)]
            if not desc:
                desc = f"支持{name}相关流程处理与状态跟踪"
        elif ":" in clean:
            name, desc = [x.strip() for x in clean.split(":", 1)]
            if not desc:
                desc = f"支持{name}相关流程处理与状态跟踪"
        else:
            name = clean[:12]
            desc = f"支持{name}相关流程处理与状态跟踪"
        normalized.append(f"{name}：{desc}")

    if not normalized:
        normalized = [
            "用户与权限：支持账号、角色和权限分配",
            "业务数据管理：支持数据录入、校验与查询",
            "流程编排：支持流程配置、执行与跟踪",
            "统计分析：支持指标汇总与报表导出",
            "系统运维：支持参数配置与日志审计",
        ]

    out = ""
    for item in normalized:
        candidate = item if not out else f"{out}；{item}"
        if len(candidate) <= max_chars:
            out = candidate
        else:
            if not out:
                out = item[:max_chars]
            break
    return out


def extract_output_with_agent(
    llm: LLMConfig,
    source_text: str,
    seed_data: dict[str, Any] | None = None,
    debug_dir: Path | None = None,
    base_name: str = "llm",
) -> AssessmentOutputSchema:
    if not (llm.api_key or "").strip():
        raise ValueError("Missing DOCCOLLATE_LLM_API_KEY")

    model = _build_model(llm)
    field_contexts = retrieve_field_contexts(source_text, top_k=3)

    logger.info("LLM stage 1/2: pool scoring (single-field + top-%s)", POOL_TOP_N)
    pool_seed: dict[str, str] = {}
    pool_info: dict[str, Any] = {}
    for field in ("app__product_type_text", "app__category_assess"):
        label, info = _score_single_pool_field(llm, field, source_text, field_contexts)
        pool_seed[field] = label
        pool_info[field] = info

    merged_seed = dict(seed_data or {})
    merged_seed.update(pool_seed)

    if debug_dir:
        debug_dir.mkdir(parents=True, exist_ok=True)
        (debug_dir / f"{base_name}.stage1.json").write_text(
            json.dumps(
                {
                    "seed_data": seed_data or {},
                    "field_contexts": field_contexts,
                    "pool_selected_info": pool_info,
                    "pool_seed": pool_seed,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    logger.info("LLM stage 2/2: structured generation")
    agent = Agent(
        model,
        output_type=AssessmentOutputSchema,
        system_prompt=SYSTEM_PROMPT,
        retries=1,
    )
    result = agent.run_sync(_build_prompt(source_text, field_contexts, seed_data=merged_seed))
    data = _ensure_defaults(result.output.model_dump(exclude_none=True))

    data["app__product_type_text"] = pool_seed.get("app__product_type_text", data.get("app__product_type_text", ""))
    data["app__category_assess"] = pool_seed.get("app__category_assess", data.get("app__category_assess", ""))

    output = AssessmentOutputSchema.model_validate(data)
    if debug_dir:
        (debug_dir / f"{base_name}.stage2.json").write_text(
            json.dumps(output.model_dump(exclude_none=True), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return output
