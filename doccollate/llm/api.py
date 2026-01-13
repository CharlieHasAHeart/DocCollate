from __future__ import annotations

import json
import textwrap
from typing import Any

from .client import LLMRuntime, chat_json, chat_text


PLACEHOLDER_FIELDS = [
    "{{ purpose }}",
    "{{ scope }}",
    "{{ references }}",
    "{{ project_source }}",
    "{{ project_scope_objectives }}",
    "{{ potential_customers }}",
    "{{ product_features }}",
    "{{ product_goals }}",
    "{{ architecture }}",
    "{{ technical_feasibility }}",
    "{{ market_feasibility }}",
    "{{ ip_analysis }}",
    "{{ conclusion }}",
]


def build_prompt(manual_inputs: dict[str, Any], field_evidence: dict[str, list[dict[str, Any]]]) -> str:
    rules = textwrap.dedent(
        """
        你是一个严谨的文档生成器。只输出严格 JSON，且必须符合给定 schema。
        全局规则：
        - 不依赖章节号；只依据证据 chunks
        - 不编造具体产品/技术名；缺失可用“待确认”保守表述
        - 风格：正式、决策向、可执行；避免营销语
        - 字段输出独立成段，便于直接填入 Word
        字段硬规则：
        - {{ product_features }}: 用于立项建议书的“建设内容/核心能力概述”，3-6条；必须使用统一排版便于扫读：
          1) 每条独占一行
          2) 每条以 "• " 开头
          3) 统一格式："• 能力/建设项：覆盖范围/业务价值（1-2句）"
          4) 使用全角冒号 "：" 分隔标题与描述
          5) 避免细粒度功能清单、页面/按钮级描述与模板化“可以...”
        - 表格 terms/resources/costs 至少满足最少行数，可输出更多；milestones 固定 5 行
        里程碑时间硬规则：
        - tables.milestones[*].start_date / end_date 必须输出准确日期字符串，推荐格式 YYYY-MM-DD
        - 不要输出 tables.milestones[*].time 字段（将由程序用 start/end 统一拼接展示）
        - milestones 日期必须落在 manual_inputs.schedule.start_date 与 end_date 范围内，并均匀规划 5 段
        - 金额字段强规则（禁止“待评估”）：
          - tables.resources[*].cost：必须给出人民币估算，格式统一为 "¥50,000"
          - tables.costs[*].amount：必须给出人民币估算，格式统一为 "¥50,000"
        - 若表格不足最少行数：请新增合理条目补齐（不要用“待评估/空字符串”填充金额字段）
        """
    ).strip()

    evidence_lines: list[str] = []
    for field, chunks in field_evidence.items():
        evidence_lines.append(f"FIELD: {field}")
        for chunk in chunks:
            evidence_lines.append(f"- {chunk['id']}: {chunk['text']}")
        evidence_lines.append("")

    schema = {
        "placeholders": {key: "" for key in PLACEHOLDER_FIELDS},
        "tables": {
            "terms": [
                {"term": "", "definition": ""},
                {"term": "", "definition": ""},
                {"term": "", "definition": ""},
                {"term": "", "definition": ""},
            ],
            "resources": [
                {"name": "", "level": "", "spec": "", "source": "", "cost": ""},
                {"name": "", "level": "", "spec": "", "source": "", "cost": ""},
            ],
            "costs": [
                {"item": "", "amount": "", "note": ""},
                {"item": "", "amount": "", "note": ""},
                {"item": "", "amount": "", "note": ""},
                {"item": "", "amount": "", "note": ""},
                {"item": "", "amount": "", "note": ""},
                {"item": "", "amount": "", "note": ""},
            ],
            "milestones": [
                {"phase": "", "tasks": "", "start_date": "", "end_date": "", "deliverables": ""},
                {"phase": "", "tasks": "", "start_date": "", "end_date": "", "deliverables": ""},
                {"phase": "", "tasks": "", "start_date": "", "end_date": "", "deliverables": ""},
                {"phase": "", "tasks": "", "start_date": "", "end_date": "", "deliverables": ""},
                {"phase": "", "tasks": "", "start_date": "", "end_date": "", "deliverables": ""},
            ],
        },
        "evidence": [
            {"field": "{{ product_features }}", "chunks": ["chunk_0001"]}
        ],
    }

    prompt = textwrap.dedent(
        f"""
        任务：根据 manual_inputs 与 field evidence 生成 JSON。
        manual_inputs:
        {json.dumps(manual_inputs, ensure_ascii=False)}

        field evidence:
        {"\n".join(evidence_lines)}

        schema 示例（仅示意结构与字段，不要省略任何字段）：
        {json.dumps(schema, ensure_ascii=False)}

        规则：
        {rules}

        只输出 JSON，不要输出任何额外文本。
        """
    ).strip()
    return prompt


def call_llm(prompt: str, runtime: LLMRuntime) -> dict[str, Any]:
    return chat_json(
        runtime,
        system_prompt="You are a careful JSON generator.",
        user_prompt=prompt,
        temperature=0.2,
    )


def translate_to_english(text: str, runtime: LLMRuntime) -> str:
    prompt = (
        "Translate the following project name into clear, professional English. "
        "Return ONLY the English name with no quotes or extra text:\n"
        f"{text}"
    )
    content = chat_text(
        runtime,
        system_prompt="You are a precise translator.",
        user_prompt=prompt,
        temperature=0.2,
    )
    return content.strip().strip("\"").strip("'")
