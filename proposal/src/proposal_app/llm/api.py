from __future__ import annotations

import json
import textwrap
import re
from typing import Any

from .client import LLMRuntime, chat_json, chat_text, _loads_json_best_effort
from .pydantic_ledger import call_ledger_with_pydantic
from .pydantic_rewrite import (
    call_combined_rewrite_with_pydantic,
    call_doc_rewrite_with_pydantic,
    call_missing_patch_with_pydantic,
    call_paragraph_rewrite_with_pydantic,
)
from ..proposal.ledger_mapping import build_ledger_scope
from ..proposal.cluster_defs import PLACEHOLDER_FIELDS


LEDGER_EXTRA_PATHS: tuple[tuple[str, ...], ...] = ()


def _ledger_schema() -> dict[str, Any]:
    return {
        "schema_version": "ledger_hard_v3",
        "delivery_window": {"start": "", "end": ""},
        "poc_window": {"start": "", "end": ""},
        "key_timepoints": {
            "kickoff": "",
            "delivery_window_start": "",
            "interface_freeze": "",
            "poc_start": "",
            "poc_end": "",
            "full_function_complete": "",
            "integration_complete": "",
            "uat_start": "",
            "uat_pass": "",
            "launch_window_start": "",
            "stabilization_window": {"start": "", "end": ""},
            "handover_complete": "",
            "delivery_window_end": "",
        },
        "scope_boundary": {
            "inclusions": [""],
            "exclusions": [""],
        },
        "acceptance_criteria": {
            "acceptance_definition": "",
            "exit_criteria": "",
        },
        "performance_capacity": {
            "response_time": "",
            "user_concurrency": "",
            "device_connections": "",
            "api_qps": "",
            "capacity_notes": "",
        },
        "sla_support": {
            "availability_target": "",
            "rto_target": "",
            "response_target": "",
            "support_window": "",
        },
        "compliance_requirements": {
            "data_residency": "",
            "regulatory_requirements": "",
            "security_controls": "",
            "retention": {
                "business_data": "",
                "audit_log": "",
                "ops_log": "",
                "device_raw": "",
                "blockchain_data": "",
                "notes": "",
            },
        },
        "budget_resources": {
            "budget_total": "",
            "resource_constraints": "",
        },
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
            "milestones": [
                {"phase": "", "tasks": "", "start_date": "", "end_date": "", "deliverables": ""},
                {"phase": "", "tasks": "", "start_date": "", "end_date": "", "deliverables": ""},
                {"phase": "", "tasks": "", "start_date": "", "end_date": "", "deliverables": ""},
                {"phase": "", "tasks": "", "start_date": "", "end_date": "", "deliverables": ""},
                {"phase": "", "tasks": "", "start_date": "", "end_date": "", "deliverables": ""},
            ],
            "references_list": [
                {"title": "", "type": "", "date": "", "version": "", "note": ""},
            ],
            "risk_register": [
                {
                    "id": "",
                    "description": "",
                    "probability": "",
                    "impact": "",
                    "level": "",
                    "trigger": "",
                    "mitigation": "",
                },
                {
                    "id": "",
                    "description": "",
                    "probability": "",
                    "impact": "",
                    "level": "",
                    "trigger": "",
                    "mitigation": "",
                },
                {
                    "id": "",
                    "description": "",
                    "probability": "",
                    "impact": "",
                    "level": "",
                    "trigger": "",
                    "mitigation": "",
                },
            ],
        },
    }


def build_ledger_prompt(spec_text: str, manual_inputs: dict[str, Any] | None = None) -> str:
    schema = _ledger_schema()
    manual_inputs = manual_inputs if isinstance(manual_inputs, dict) else {}
    start_date = str(manual_inputs.get("start_date", "")).strip()
    end_date = str(manual_inputs.get("end_date", "")).strip()
    schedule_hint = ""
    if start_date or end_date:
        schedule_hint = f"已确认交付窗口期：{start_date or ''} ~ {end_date or ''}（如已给出，必须严格使用，不得更改）"

    return textwrap.dedent(
        f"""
        你是立项建议书台账(JSON)生成器。只输出严格 JSON，必须符合给定 schema。
        规则：
        - 字段齐全、口径一致、用词统一
        - delivery_window 与 poc_window 必须给出明确起止日期
        - poc_window 必须落在 delivery_window 内
        - schema_version 固定为 ledger_hard_v3
        - tables 必须补齐：terms≥4行、resources≥2行、milestones=5行、references_list≥1行、risk_register≥3行
        - milestones 的 start_date/end_date 必须在 delivery_window 内，且不得与 delivery_window 冲突
        - milestones 相邻阶段之间不得出现空档期（下一阶段 start_date 应与上一阶段 end_date 同日或次日）
        - resources 必须覆盖软件资源/硬件资源/人力资源三类（至少各 1 行）
        - 若给出 start_date/end_date，delivery_window 必须严格等于该区间
        - key_timepoints 必须补齐，且全部时间点落在 delivery_window 内
        - kickoff 与 delivery_window_start 必须等于 delivery_window.start
        - delivery_window_end 必须等于 delivery_window.end
        - poc_start/poc_end 必须分别等于 poc_window.start/poc_window.end
        - 关键时间点与里程表联动关系遵循 时间逻辑.md 描述

        输入：
        - 说明书全文：{spec_text}
        - 交付窗口期（人工输入，若为空则由说明书推断）：{schedule_hint or "未提供"}
        - schema：{json.dumps(schema, ensure_ascii=False)}

        只输出 JSON。
        """
    ).strip()


def build_ledger_fix_prompt(
    spec_text: str,
    manual_inputs: dict[str, Any] | None,
    ledger: dict[str, Any],
    issues: list[Any],
) -> str:
    schema = _ledger_schema()
    manual_inputs = manual_inputs if isinstance(manual_inputs, dict) else {}
    start_date = str(manual_inputs.get("start_date", "")).strip()
    end_date = str(manual_inputs.get("end_date", "")).strip()
    schedule_hint = ""
    if start_date or end_date:
        schedule_hint = f"{start_date or ''} ~ {end_date or ''}"
    
    def _render_issue(item: Any) -> str:
        if isinstance(item, str):
            return f"- {item}"
        if not isinstance(item, dict):
            return f"- {str(item)}"
        rule_id = str(item.get("rule_id", "")).strip()
        message = str(item.get("message", "")).strip()
        location = str(item.get("location", "")).strip()
        hint = str(item.get("repair_hint", "")).strip()
        parts = [p for p in [f"{rule_id}: {message}" if rule_id else message, f"loc={location}" if location else ""] if p]
        base = " | ".join(parts) if parts else str(item)
        if hint:
            return f"- {base} | hint={hint}"
        return f"- {base}"

    issue_lines = "\n".join([_render_issue(item) for item in issues]) if issues else "- 无"
    issues_json = json.dumps(issues, ensure_ascii=False) if issues else "[]"
    current_ledger = json.dumps(ledger, ensure_ascii=False)
    return textwrap.dedent(
        f"""
        你是立项建议书统一口径数据修复器。请修复给定 ledger 中的问题，并输出完整 JSON。
        修复要求：
        - 仅修复问题清单相关内容，其他字段尽量保持不变
        - 必须符合给定 schema 与全部约束

        问题清单：
        {issue_lines}

        问题清单（结构化，需优先遵循 repair_hint）：
        {issues_json}

        当前 ledger：
        {current_ledger}

        约束：
        - 术语与口径统一，避免同义词混用
        - 数字口径一致（关键指标/周期等不能互相冲突）
        - 责任人仅写岗位，不写姓名
        - delivery_window 与 poc_window 不得冲突，且 poc_window 必须落在 delivery_window 内
        - scope_boundary.inclusions 与 scope_boundary.exclusions 必须非空
        - acceptance_criteria.acceptance_definition 与 acceptance_criteria.exit_criteria 必须非空
        - performance_capacity 必须给出响应时间/并发/设备连接数/API QPS
        - sla_support 必须给出可用性/RTO/响应时效/支持窗口
        - compliance_requirements.retention 需拆分业务数据/审计日志/运维日志/设备原始/区块链数据留存口径
        - budget_resources 必须给出总预算与资源上限/约束
        - schema_version 固定为 ledger_hard_v3
        - schema 中数组至少填写一项内容，不得留空数组
        - tables 必须补齐：terms≥4行、resources≥2行、milestones=5行、references_list≥1行、risk_register≥3行
        - milestones 的 start_date/end_date 必须在 delivery_window 内
        - milestones 相邻阶段之间不得出现空档期（下一阶段 start_date 应与上一阶段 end_date 同日或次日）
        - resources 必须覆盖软件资源/硬件资源/人力资源三类（至少各 1 行）
        - 若给出 start_date/end_date，delivery_window 必须严格等于该区间，不得修改
        - key_timepoints 必须补齐，且全部时间点落在 delivery_window 内
        - kickoff 与 delivery_window_start 必须等于 delivery_window.start
        - delivery_window_end 必须等于 delivery_window.end
        - poc_start/poc_end 必须分别等于 poc_window.start/poc_window.end
        - 关键时间点与里程表联动关系遵循 时间逻辑.md 描述

        输入：
        - 说明书全文：{spec_text}
        - 交付窗口期（人工输入，若为空则由说明书推断）：{schedule_hint or "未提供"}
        schema 示例（仅示意结构与字段，不要省略任何字段）：
        {json.dumps(schema, ensure_ascii=False)}

        只输出 JSON，不要输出任何额外文本或代码块。
        """
    ).strip()


def build_doc_rewrite_prompt(
    *,
    ledger_scope: dict[str, Any],
    llm_output: dict[str, Any],
    issues: list[dict[str, Any]],
) -> str:
    """
    Build a prompt for targeted doc rewrites. Expects issues containing:
    - rule_id, location, message, repair_hint
    Only placeholders listed in issues should be rewritten.
    """
    placeholders = llm_output.get("placeholders", {}) if isinstance(llm_output, dict) else {}
    rewrite_targets: dict[str, str] = {}
    for item in issues:
        location = str(item.get("location", "")).strip()
        if location.startswith("placeholders."):
            key = location[len("placeholders.") :]
            if key in placeholders and isinstance(placeholders.get(key), str):
                rewrite_targets[key] = placeholders[key]
    targets_json = json.dumps(rewrite_targets, ensure_ascii=False)
    issues_json = json.dumps(issues, ensure_ascii=False)
    ledger_json = json.dumps(ledger_scope, ensure_ascii=False)
    return textwrap.dedent(
        f"""
        你是立项建议书正文修复器。仅重写指定占位字段，输出 JSON。
        约束：
        - 只输出包含 placeholders 的 JSON，如：{{"placeholders": {{"{{{{ key }}}}": "..."}}}}
        - 仅修复问题清单涉及的字段，不得新增或删除字段
        - 严格遵循 ledger 口径，不引入新数字/新口径
        - 文本字段必须为 2–3 句完整段落，单段输出且以句号“。”结尾（表格字段除外）

        统一口径数据（ledger scope）:
        {ledger_json}

        需要重写的占位字段（key -> 当前文本）:
        {targets_json}

        问题清单（用于指导修复）:
        {issues_json}

        只输出 JSON，不要输出任何额外文本或代码块。
        """
    ).strip()


def build_doc_paragraph_rewrite_prompt(
    *,
    ledger_scope: dict[str, Any],
    paragraph_targets: list[dict[str, Any]],
) -> str:
    """
    Rewrite specific paragraphs within placeholders.
    paragraph_targets items: {"key": "{{ ... }}", "index": int, "text": "...", "hint": "..."}
    """
    ledger_json = json.dumps(ledger_scope, ensure_ascii=False)
    targets_json = json.dumps(paragraph_targets, ensure_ascii=False)
    return textwrap.dedent(
        f"""
        你是立项建议书正文修复器。只重写指定段落，输出 JSON。
        约束：
        - 只输出 JSON，结构为 {{\"paragraph_fixes\": [{{\"key\": \"{{{{ ... }}}}\", \"index\": 0, \"text\": \"...\"}}]}}
        - 仅修复给定段落，不得新增或删除段落
        - 严格遵循 ledger 口径，不引入新数字/新口径
        - 禁止输出 JSON 结构字面量（[]/{{}}/\"metric\":）出现在段落中
        - 重写段落必须为 2–3 句完整段落，且以句号“。”结尾

        统一口径数据（ledger scope）:
        {ledger_json}

        需要重写的段落（key/index/text/hint）:
        {targets_json}

        只输出 JSON，不要输出任何额外文本或代码块。
        """
    ).strip()


def build_doc_rewrite_combined_prompt(
    *,
    ledger_scope: dict[str, Any],
    llm_output: dict[str, Any],
    issues: list[dict[str, Any]],
) -> str:
    ledger_json = json.dumps(ledger_scope, ensure_ascii=False)
    placeholders = llm_output.get("placeholders", {}) if isinstance(llm_output, dict) else {}
    paragraph_targets: list[dict[str, Any]] = []
    rewrite_targets: dict[str, str] = {}

    for item in issues:
        location = str(item.get("location", "")).strip()
        if not location.startswith("placeholders."):
            continue
        key = location[len("placeholders.") :]
        if "#p" in key:
            key_only, p_idx = key.split("#p", 1)
            try:
                idx = int(p_idx)
            except ValueError:
                continue
            current = placeholders.get(key_only)
            if isinstance(current, str):
                parts = current.split("\n\n")
                if 0 <= idx < len(parts):
                    paragraph_targets.append(
                        {
                            "key": key_only,
                            "index": idx,
                            "text": parts[idx],
                            "hint": str(item.get("repair_hint") or item.get("message") or ""),
                        }
                    )
            continue
        if key in placeholders and isinstance(placeholders.get(key), str):
            rewrite_targets[key] = placeholders[key]

    payload = {
        "rewrite_targets": rewrite_targets,
        "paragraph_targets": paragraph_targets,
        "issues": issues,
    }
    payload_json = json.dumps(payload, ensure_ascii=False)
    return textwrap.dedent(
        f"""
        你是立项建议书正文修复器。根据问题清单修复正文，并输出 JSON。
        约束：
        - 只输出 JSON，结构为 {{"placeholders": {{"{{{{ key }}}}": "..."}}, "paragraph_fixes": [{{"key":"{{{{ ... }}}}","index":0,"text":"..."}}]}}
        - 仅修复给定的问题与目标字段/段落，不得新增或删除字段
        - 严格遵循 ledger 口径，不引入新数字/新口径
        - 禁止在段落文本中输出 JSON 结构字面量
        - 若问题 rule_id=R6，必须将相关段落改写为“计划验证/拟开展/预计验证”口径，去掉完成态措辞，不得补充证据或日期
        - 文本字段/段落必须为 2–3 句完整段落，且以句号“。”结尾

        统一口径数据（ledger scope）:
        {ledger_json}

        输入（目标字段/目标段落/问题清单）:
        {payload_json}

        只输出 JSON，不要输出任何额外文本或代码块。
        """
    ).strip()


def build_missing_patch_prompt(
    *,
    ledger_scope: dict[str, Any],
    llm_output: dict[str, Any],
    missing_fields: list[str],
) -> str:
    ledger_json = json.dumps(ledger_scope, ensure_ascii=False)
    missing_block = "\n".join([f"- {x}" for x in missing_fields]) if missing_fields else "- 无"
    current_json = json.dumps(llm_output, ensure_ascii=False)
    return textwrap.dedent(
        f"""
        你是立项建议书 JSON 补丁生成器。只补齐缺失字段，输出 JSON patch。
        约束：
        - 只输出 JSON，结构为 {{"placeholders": {{"{{{{ key }}}}": "..."}}, "tables": {{"table_name": [{{...}}]}}}}
        - 仅输出缺失字段对应的键；不得输出未在缺失字段列表中的键
        - 严格遵循 ledger 口径，不引入新数字/新口径
        - 表格补齐不得输出空行；每个单元格必须非空
        - 文本字段必须为 2–3 句完整段落，且以句号“。”结尾（表格字段除外）

        统一口径数据（ledger scope）:
        {ledger_json}

        当前 llm_output（用于参考现状，尽量不改动非缺失字段）:
        {current_json}

        缺失字段列表（需要补齐，不能为空）:
        {missing_block}

        只输出 JSON，不要输出任何额外文本或代码块。
        """
    ).strip()


def _build_rules() -> str:
    return textwrap.dedent(
        """
        你是一个严谨的立项建议书撰写者。只输出严格 JSON，且必须符合给定 schema。
        全局规则：
        - 除 {{ core_product_features }} 外，其他字段基于说明书全文撰写，不依赖章节号
        - 不编造具体产品/技术名；如信息不足用最佳实践合理假设补齐
        - 风格：正式、决策向、可执行；避免营销语
        - 字段输出独立成段，便于直接填入 Word
        - 正文类字段必须写成完整叙述，不能只给关键词或字段值堆叠；单段输出（名称/日期/金额/单值类短字段除外）
        - 单段内控制 2-4 句，句式自然，避免清单化表达
        - resources 为资源成本表，必须包含软件资源/硬件资源/人力资源三类条目；成本不可为 0，内部资源也需给出成本估算
        - 禁止使用项目符号或编号列点，禁止输出以 "- "、"•"、"1."、"1)" 等开头的行
        字段硬规则：
        - 所有占位字段与表格字段必须非空；不得使用“待确认/需补充/待提供/待定”等占位或推脱表述
        - 你是立项规划与方案专家，需基于最佳实践给出可执行、可落地的填充内容
        - 统一口径：同一概念、指标、周期口径必须在全文一致；若有多个口径需明确区分并保持一致
        - 统一口径数据优先：术语、指标、周期、容量、合规等级等敏感口径必须引用统一口径数据内容，禁止引入统一口径数据之外的新口径或新数字
        - 非敏感描述可用最佳实践补齐，但不得新增可量化承诺（如 99.9%、7×24、10万设备），除非 ledger 明确提供
        - 结论需附证据：每个关键结论后补一条可验证依据或来源（来自说明书描述、实践经验或工程常识）
        - 证据必须融入正文，不得出现“依据来自/上下文/台账/基准数据/基准信息/统一口径数据/字段/decisions/metrics/cadence”等元叙述或键名
        - 若运维支持SLA/响应时效出现到场承诺且 MTTR/RTO 目标不大于到场时限，必须明确“远程修复为主、到场仅少数场景”口径
        - 数字一致性：关键指标/周期等数字在各段落保持一致，不得自相矛盾
        - 技术描述需可验证：避免堆栈罗列，必须说明关键决策的取舍理由与可验证标准
        - 可读性：段落控制在 2-4 句，句式自然，避免清单化
        - 独立成章：不得引用前文或后文，不出现“见前文/如上所述/见下文”等跨章措辞
        - 禁止使用“X：Y”句式或全角冒号“：”作为输出文本
        - 不要用“；”进行清单式列点，改为自然段落或拆分短句
        - 禁止“评审式点评句/自评语气”，例如“简洁有力/清晰/稳健/合理/已通过评审/该计划确保/该模型证明”等；必须以事实+论证+结论表达
        - 范围与采购一致：若包含IT服务器/存储等资源采购，范围需明确为包含平台基础设施、不含生产侧工艺硬件
        - PoC与MVP口径一致：PoC周期与交付窗口不可混用，MVP范围与阶段交付物需对应
        - MVP承诺一致：若MVP排除项非空，指标与承诺需显式分阶段表述，不得在MVP阶段承诺排除能力
        - 环境口径一致：若出现8GB与16GB内存要求，需区分开发测试与生产推荐配置
        - SLA口径一致：自动恢复目标与工单响应SLA需明确适用范围，避免混为一谈
        - SLA口径必须分离：availability_target/rto_target 仅写可用性/恢复目标，response_target 仅写响应时间，support_window 仅写支持时段/到场承诺；不得混用
        - 留存口径一致：数据留存/日志留存的年限必须一致或明确范围（例如“审计日志3年，业务数据不超过2年”）
        - 合规等级一致：等保等级统一为三级并说明适用范围，不得出现二级
        - 部署模式一致：仅允许私有化/专有云口径，不得出现 SaaS 表述
        - 指标口径一致：指标定义需包含计算公式、统计窗口与目标阈值，并注明PoC/MVP/稳定期目标分层
        - 商业模式一致：对外销售口径下，商业/定价叙述需与定位一致
        - 若正文出现“交易/交易记录/交易看板/上链”等词，必须在同段或相邻段落显式说明“非撮合、非清结算、非对外交易平台对接”（如适用）
        - 若 scope_boundary.exclusions 明确“不包含撮合/清结算/外部交易平台对接”，正文不得出现“参与交易/碳交易/交易闭环/交易平台/交易所/成交”等表述；必须改写为“溯源/合规证明/交易准备/可信流转”等不越界表述
        - 若提供交付窗口，所有日期/月份/阶段/周期仅允许落在该窗口内；不得出现超出窗口的时间表述
        - PoC 时间口径必须统一：poc_window 与里程碑表 PoC 阶段，日期必须完全一致
        - 里程碑表不得拆分“项目启动”与“PoC验证”为不同日期范围，应合并为同一 PoC 阶段并覆盖 poc_window
        - 成本与资源类叙述禁止出现超出交付窗口的工期或薪资周期（例如“8个月薪资”）
        - 服务器规格一致：涉及服务器/环境规格需保持一致或明确区分环境
        - 并发口径一致：区分用户并发、API QPS 与设备连接数，不混用
        - 若出现“已验证/已通过/已压测/已评审”，必须在同段给出依据（报告/纪要编号与日期）；信息不足时改写为“计划在××阶段完成验证”
        - 若 sla_support.availability_target 涉及可用性或百分比目标，运维支持SLA需包含告警接收/升级或自动恢复策略之一，避免“仅工作日支持”口径冲突
        - 禁止使用自我评价式措辞（如“清晰/有力/合理/完善/严谨/避免歧义/挑战性与可达性平衡/符合SMART/该计划确保”等）
        - 禁止输出 true/false 或类似布尔值；如统一口径数据为布尔字段，必须转写为清晰中文句式
        - 合规口径一致：上线前与上线后合规要求分阶段表述
        - 角色与责任人仅写岗位，不写姓名（例如“产品负责人”“技术负责人”）
        - 输出必须是单个 JSON 对象，不要输出代码块或额外文本
        - {{ core_product_features }}: 用于“产品核心功能描述”，使用自然段落完整叙述，不得使用项目符号
        里程碑时间硬规则：
        """
    ).strip()


def build_prompt(
    manual_inputs: dict[str, Any],
    spec_text: str,
    field_evidence: dict[str, list[dict[str, Any]]],
    ledger: dict[str, Any] | None = None,
) -> str:
    rules = _build_rules()

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
            "milestones": [
                {"phase": "", "tasks": "", "start_date": "", "end_date": "", "deliverables": ""},
                {"phase": "", "tasks": "", "start_date": "", "end_date": "", "deliverables": ""},
                {"phase": "", "tasks": "", "start_date": "", "end_date": "", "deliverables": ""},
                {"phase": "", "tasks": "", "start_date": "", "end_date": "", "deliverables": ""},
                {"phase": "", "tasks": "", "start_date": "", "end_date": "", "deliverables": ""},
            ],
            "references_list": [
                {"title": "", "type": "", "date": "", "version": "", "note": ""},
            ],
            "risk_register": [
                {
                    "id": "",
                    "description": "",
                    "probability": "",
                    "impact": "",
                    "level": "",
                    "trigger": "",
                    "mitigation": "",
                },
            ],
        },
        "evidence": [
            {"field": "{{ core_product_features }}", "chunks": ["chunk_0001"]}
        ],
    }

    ledger_scope = build_ledger_scope(ledger or {}, PLACEHOLDER_FIELDS, extra_paths=LEDGER_EXTRA_PATHS)
    ledger_json = json.dumps(ledger_scope, ensure_ascii=False)
    evidence_block = "\n".join(evidence_lines)
    prompt = textwrap.dedent(
        f"""
        任务：根据 manual_inputs 与 field evidence 生成 JSON。
        manual_inputs:
        {json.dumps(manual_inputs, ensure_ascii=False)}

        说明书全文:
        {spec_text}

        统一口径数据（最小口径，仅包含本次生成所需字段）:
        {ledger_json}

        field evidence（仅用于 {{ core_product_features }}）:
        {evidence_block}

        schema 示例（仅示意结构与字段，不要省略任何字段）：
        {json.dumps(schema, ensure_ascii=False)}

        表格填充规则：
        - terms/resources/references_list/risk_register 至少满足最少行数，可输出更多
        - milestones 输出 5 行（不足补齐）
        - 补齐仅允许细化现有阶段任务/条目，不得新增阶段或新增日期口径
        - 若表格不足最少行数：请新增合理条目补齐（不要用“待评估/空字符串”填充金额字段）

        规则：
        {rules}

        只输出 JSON，不要输出任何额外文本。
        """
    ).strip()
    return prompt


def build_full_prompt(
    manual_inputs: dict[str, Any],
    spec_text: str,
    ledger: dict[str, Any] | None,
    full_schema: dict[str, Any],
    missing_fields: list[str] | None = None,
) -> str:
    rules = _build_rules()
    ledger_scope = build_ledger_scope(ledger or {}, PLACEHOLDER_FIELDS, extra_paths=LEDGER_EXTRA_PATHS)
    ledger_json = json.dumps(ledger_scope, ensure_ascii=False)
    missing_block = "\n".join([f"- {x}" for x in (missing_fields or [])]) if missing_fields else "无"
    return textwrap.dedent(
        f"""
        任务：一次性生成整份立项建议书 JSON 输出。
        约束：只填 schema 中包含的字段，不得输出 schema 之外的字段。
        写作要求：基于统一口径数据进行完整叙述，输出单段文本（禁止使用 "\\n\\n" 分段）；不要只列字段值或短语；禁止项目符号或编号列点。
        强制段落规则：从 {{ purpose }} 到 {{ summary }} 的所有非表格字段，必须写成 2–3 句，并且以句号“。”结尾。
        完整性要求：placeholders 与 tables 中所有必填字段不得为空字符串；表格不得输出空行。
        若给出缺失字段列表：优先补齐缺失字段，其他内容尽量保持不变。

        manual_inputs:
        {json.dumps(manual_inputs, ensure_ascii=False)}

        说明书全文:
        {spec_text}

        统一口径数据（ledger）:
        {ledger_json}

        schema 示例（仅示意结构与字段，不要省略任何字段）：
        {json.dumps(full_schema, ensure_ascii=False)}

        表格填充规则：
        - terms/resources/references_list/risk_register 至少满足最少行数，可输出更多
        - milestones 输出 5 行（不足补齐）
        - 补齐仅允许细化现有阶段任务/条目，不得新增阶段或新增日期口径
        - resources 为资源成本表，重点在成本估算；必须覆盖软件资源/硬件资源/人力资源三类，且每类至少一行
        - resources 每行需包含资源名称、重要性等级、规格/配置、来源、成本；成本不得为 0
        - 若表格不足最少行数：请新增合理条目补齐（不要用“待评估/空字符串/0”填充成本字段）

        缺失字段列表（需要补齐，不能为空）：
        {missing_block}

        规则：
        {rules}

        只输出 JSON，不要输出任何额外文本。
        """
    ).strip()


def build_section_prompt(
    manual_inputs: dict[str, Any],
    spec_text: str,
    ledger: dict[str, Any] | None,
    full_schema: dict[str, Any],
    focus_placeholders: list[str] | None = None,
    focus_tables: list[str] | None = None,
) -> str:
    rules = _build_rules()
    ledger_scope = build_ledger_scope(ledger or {}, PLACEHOLDER_FIELDS, extra_paths=LEDGER_EXTRA_PATHS)
    ledger_json = json.dumps(ledger_scope, ensure_ascii=False)

    def _norm_placeholder(tag: str) -> str:
        inner = (tag or "").strip()
        inner = inner.lstrip("{").rstrip("}")
        inner = inner.strip()
        return "{{ " + inner + " }}"

    focus_placeholders = [p for p in (focus_placeholders or []) if isinstance(p, str) and p.strip()]
    focus_placeholders = [_norm_placeholder(p) for p in focus_placeholders if _norm_placeholder(p) in PLACEHOLDER_FIELDS]
    focus_tables = [t for t in (focus_tables or []) if isinstance(t, str) and t.strip()]

    return textwrap.dedent(
        f"""
        任务：仅生成指定章节占位符与表格内容（用于并行生成）。
        约束：只填 schema 中包含的字段，不得输出 schema 之外的字段。
        写作要求：对指定 placeholders 输出 2-3 句自然段落，单段输出（禁止使用 "\\n\\n" 分段）；禁止项目符号或编号列点。

        只允许填充以下 placeholders（其余必须留空字符串）：
        {json.dumps(focus_placeholders, ensure_ascii=False)}

        只允许填充以下 tables（其余必须为空数组）：
        {json.dumps(focus_tables, ensure_ascii=False)}

        manual_inputs:
        {json.dumps(manual_inputs, ensure_ascii=False)}

        说明书全文:
        {spec_text}

        统一口径数据（ledger）:
        {ledger_json}

        schema 示例（仅示意结构与字段，不要省略任何字段）：
        {json.dumps(full_schema, ensure_ascii=False)}

        规则：
        {rules}

        只输出 JSON，不要输出任何额外文本。
        """
    ).strip()


def call_llm(prompt: str, runtime: LLMRuntime) -> dict[str, Any]:
    raw = chat_text(
        runtime,
        system_prompt="You are a careful JSON generator. Output JSON only.",
        user_prompt=prompt,
        temperature=0.2,
    )
    try:
        return _loads_json_best_effort(raw)
    except Exception:
        repaired = chat_text(
            runtime,
            system_prompt="You are a careful JSON repairer. Output JSON only.",
            user_prompt=f"Fix to valid JSON only:\n{raw}",
            temperature=0.0,
        )
        return _loads_json_best_effort(repaired)


def call_llm_ledger(prompt: str, runtime: LLMRuntime) -> dict[str, Any]:
    return call_ledger_with_pydantic(prompt, runtime)


def call_llm_doc_rewrite(prompt: str, runtime: LLMRuntime) -> dict[str, Any]:
    return call_doc_rewrite_with_pydantic(prompt, runtime)


def call_llm_paragraph_rewrite(prompt: str, runtime: LLMRuntime) -> dict[str, Any]:
    return call_paragraph_rewrite_with_pydantic(prompt, runtime)


def call_llm_doc_rewrite_combined(prompt: str, runtime: LLMRuntime) -> dict[str, Any]:
    return call_combined_rewrite_with_pydantic(prompt, runtime)


def call_llm_missing_patch(prompt: str, runtime: LLMRuntime) -> dict[str, Any]:
    return call_missing_patch_with_pydantic(prompt, runtime)


def call_llm_text(prompt: str, runtime: LLMRuntime, temperature: float = 0.2) -> str:
    return chat_text(
        runtime,
        system_prompt="You are a precise planning assistant.",
        user_prompt=prompt,
        temperature=temperature,
    )


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
            out.append(ch)
        else:
            if ch == "\"":
                in_string = True
            out.append(ch)
    return "".join(out)


def _try_parse_json(text: str) -> dict[str, Any] | None:
    try:
        return json.loads(text)
    except Exception:
        pass
    try:
        return json.loads(_escape_control_chars_in_strings(text))
    except Exception:
        return None


def _extract_json(text: str) -> dict[str, Any] | None:
    if not text:
        return None
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        parsed = _try_parse_json(match.group(1))
        if parsed is not None:
            return parsed
    parsed = _try_parse_json(text)
    if parsed is not None:
        return parsed
    text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start : end + 1]
        return _try_parse_json(candidate)
    if start != -1 and (end == -1 or end < start):
        candidate = text[start:]
        in_string = False
        escaped = False
        depth = 0
        for ch in candidate:
            if in_string:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == "\"":
                    in_string = False
            else:
                if ch == "\"":
                    in_string = True
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
        if depth > 0:
            fixed = candidate + ("}" * depth)
            parsed = _try_parse_json(fixed)
            if parsed is not None:
                return parsed
    return None


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
