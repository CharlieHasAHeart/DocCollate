from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional



class Stage(str, Enum):
    LEDGER = "ledger"
    DOC_POST = "doc_post"


class ActionType(str, Enum):
    REPAIR_LEDGER = "repair_ledger"
    REWRITE_DOC_SECTION = "rewrite_doc_section"


@dataclass
class Issue:
    rule_id: str
    severity: str
    message: str
    location: Optional[str] = None
    evidence: Optional[Dict[str, Any]] = None
    suggested_action: Optional[ActionType] = None
    repair_hint: Optional[str] = None


@dataclass
class RuleResult:
    passed: bool
    issues: List[Issue] = field(default_factory=list)


@dataclass
class Rule:
    rule_id: str
    stage: Stage
    description: str
    severity_on_fail: str
    check: Callable[[Dict[str, Any]], RuleResult]


@dataclass
class PipelineContext:
    ledger: Dict[str, Any]
    llm_output: Optional[Dict[str, Any]] = None
    ledger_scope: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


def run_rules(ctx: PipelineContext, rules: List[Rule], stage: Stage) -> List[Issue]:
    issues: List[Issue] = []
    payload = {
        "ledger": ctx.ledger,
        "llm_output": ctx.llm_output,
        "ledger_scope": ctx.ledger_scope,
        "metadata": ctx.metadata,
    }
    for rule in rules:
        if rule.stage != stage:
            continue
        res = rule.check(payload)
        if not res.passed:
            issues.extend(res.issues)
    return issues


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def _as_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if value is None:
        return ""
    return str(value).strip()


def _contains_any(text: str, tokens: tuple[str, ...]) -> bool:
    return any(tok in text for tok in tokens)


_YMD_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
_JSON_LEAK_PATTERNS = (
    re.compile(r"\{[^}]*\"[^\"]+\"\s*:\s*[^}]+\}"),
    re.compile(r"\"[a-zA-Z0-9_]+\"\s*:\s*\"?[^\"]+\"?"),
    re.compile(r"\[\s*\{"),
    re.compile(r"\}\s*,\s*\{"),
    re.compile(r"\}\s*\]"),
)


def _parse_ymd(text: str) -> date | None:
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def _extract_dates(text: str) -> list[date]:
    out: list[date] = []
    for item in _YMD_RE.findall(text):
        d = _parse_ymd(item)
        if d:
            out.append(d)
    return out


def _parse_required_date(
    value: Any,
    *,
    rule_id: str,
    label: str,
    location: str,
    issues: List["Issue"],
    action: ActionType,
) -> date | None:
    raw = _as_text(value)
    if not raw:
        issues.append(
            Issue(
                rule_id=rule_id,
                severity="error",
                message=f"{label} 不能为空",
                location=location,
                suggested_action=action,
                repair_hint="补齐 YYYY-MM-DD 格式日期。",
            )
        )
        return None
    parsed = _parse_ymd(raw)
    if not parsed:
        issues.append(
            Issue(
                rule_id=rule_id,
                severity="error",
                message=f"{label} 日期格式需为 YYYY-MM-DD",
                location=location,
                suggested_action=action,
                repair_hint="使用 YYYY-MM-DD 格式。",
            )
        )
        return None
    return parsed


def _get_nested(data: Dict[str, Any], path: tuple[str, ...]) -> Any:
    cur: Any = data
    for key in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def _list_non_empty(value: Any) -> bool:
    if not isinstance(value, list):
        return False
    for item in value:
        if isinstance(item, str) and item.strip():
            return True
        if isinstance(item, dict) and any(_as_text(v) for v in item.values()):
            return True
    return False


def rule_time_windows_valid(payload: Dict[str, Any]) -> RuleResult:
    ledger = payload.get("ledger") or {}
    issues: List[Issue] = []

    def _check_window(name: str) -> tuple[date | None, date | None]:
        window = ledger.get(name) if isinstance(ledger.get(name), dict) else {}
        start_raw = _as_text(window.get("start"))
        end_raw = _as_text(window.get("end"))
        if not start_raw or not end_raw:
            issues.append(
                Issue(
                    rule_id="LG1",
                    severity="error",
                    message=f"{name} 必须包含 start/end",
                    location=f"ledger.{name}",
                    suggested_action=ActionType.REPAIR_LEDGER,
                    repair_hint="补齐 YYYY-MM-DD 格式的起止日期。",
                )
            )
            return None, None
        start = _parse_ymd(start_raw)
        end = _parse_ymd(end_raw)
        if not start or not end:
            issues.append(
                Issue(
                    rule_id="LG1",
                    severity="error",
                    message=f"{name} 日期格式需为 YYYY-MM-DD",
                    location=f"ledger.{name}",
                    suggested_action=ActionType.REPAIR_LEDGER,
                    repair_hint="使用 YYYY-MM-DD 格式。",
                )
            )
            return None, None
        if end < start:
            issues.append(
                Issue(
                    rule_id="LG1",
                    severity="error",
                    message=f"{name} 结束日期早于开始日期",
                    location=f"ledger.{name}",
                    suggested_action=ActionType.REPAIR_LEDGER,
                    repair_hint="确保 end 不早于 start。",
                )
            )
        return start, end

    delivery_start, delivery_end = _check_window("delivery_window")
    poc_start, poc_end = _check_window("poc_window")
    if delivery_start and delivery_end and poc_start and poc_end:
        if poc_start < delivery_start or poc_end > delivery_end:
            issues.append(
                Issue(
                    rule_id="LG1",
                    severity="error",
                    message="PoC 窗口需落在交付窗口内",
                    location="ledger.poc_window",
                    suggested_action=ActionType.REPAIR_LEDGER,
                    repair_hint="调整 PoC 窗口，使其完全包含在交付窗口内。",
                )
            )

    return RuleResult(passed=(len(issues) == 0), issues=issues)


def rule_key_timepoints_and_milestones(payload: Dict[str, Any]) -> RuleResult:
    ledger = payload.get("ledger") or {}
    issues: List[Issue] = []
    rule_id = "LG8"

    delivery = ledger.get("delivery_window") if isinstance(ledger.get("delivery_window"), dict) else {}
    delivery_start = _parse_ymd(_as_text(delivery.get("start")))
    delivery_end = _parse_ymd(_as_text(delivery.get("end")))
    if not delivery_start or not delivery_end:
        return RuleResult(passed=(len(issues) == 0), issues=issues)

    key = ledger.get("key_timepoints")
    if not isinstance(key, dict):
        issues.append(
            Issue(
                rule_id=rule_id,
                severity="error",
                message="key_timepoints 必须为对象且完整填写",
                location="ledger.key_timepoints",
                suggested_action=ActionType.REPAIR_LEDGER,
                repair_hint="补齐关键时间点字段。",
            )
        )
        return RuleResult(passed=False, issues=issues)

    def _check_within_window(label: str, dt: date | None, location: str) -> None:
        if not dt:
            return
        if dt < delivery_start or dt > delivery_end:
            issues.append(
                Issue(
                    rule_id=rule_id,
                    severity="error",
                    message=f"{label} 必须落在交付窗口内",
                    location=location,
                    suggested_action=ActionType.REPAIR_LEDGER,
                    repair_hint=f"调整到 {delivery_start} ~ {delivery_end} 区间内。",
                )
            )

    kickoff = _parse_required_date(
        key.get("kickoff"),
        rule_id=rule_id,
        label="项目启动/交付窗口期开始",
        location="ledger.key_timepoints.kickoff",
        issues=issues,
        action=ActionType.REPAIR_LEDGER,
    )
    delivery_start_tp = _parse_required_date(
        key.get("delivery_window_start"),
        rule_id=rule_id,
        label="交付窗口期开始",
        location="ledger.key_timepoints.delivery_window_start",
        issues=issues,
        action=ActionType.REPAIR_LEDGER,
    )
    interface_freeze = _parse_required_date(
        key.get("interface_freeze"),
        rule_id=rule_id,
        label="环境与接口口径冻结点",
        location="ledger.key_timepoints.interface_freeze",
        issues=issues,
        action=ActionType.REPAIR_LEDGER,
    )
    poc_start = _parse_required_date(
        key.get("poc_start"),
        rule_id=rule_id,
        label="POC启动点",
        location="ledger.key_timepoints.poc_start",
        issues=issues,
        action=ActionType.REPAIR_LEDGER,
    )
    poc_end = _parse_required_date(
        key.get("poc_end"),
        rule_id=rule_id,
        label="POC验收/结论点",
        location="ledger.key_timepoints.poc_end",
        issues=issues,
        action=ActionType.REPAIR_LEDGER,
    )
    full_function_complete = _parse_required_date(
        key.get("full_function_complete"),
        rule_id=rule_id,
        label="全功能开发完成点",
        location="ledger.key_timepoints.full_function_complete",
        issues=issues,
        action=ActionType.REPAIR_LEDGER,
    )
    integration_complete = _parse_required_date(
        key.get("integration_complete"),
        rule_id=rule_id,
        label="三方接口集成完成点",
        location="ledger.key_timepoints.integration_complete",
        issues=issues,
        action=ActionType.REPAIR_LEDGER,
    )
    uat_start = _parse_required_date(
        key.get("uat_start"),
        rule_id=rule_id,
        label="UAT开始点",
        location="ledger.key_timepoints.uat_start",
        issues=issues,
        action=ActionType.REPAIR_LEDGER,
    )
    uat_pass = _parse_required_date(
        key.get("uat_pass"),
        rule_id=rule_id,
        label="UAT通过点",
        location="ledger.key_timepoints.uat_pass",
        issues=issues,
        action=ActionType.REPAIR_LEDGER,
    )
    launch_window_start = _parse_required_date(
        key.get("launch_window_start"),
        rule_id=rule_id,
        label="上线窗口开始点",
        location="ledger.key_timepoints.launch_window_start",
        issues=issues,
        action=ActionType.REPAIR_LEDGER,
    )
    handover_complete = _parse_required_date(
        key.get("handover_complete"),
        rule_id=rule_id,
        label="移交完成点",
        location="ledger.key_timepoints.handover_complete",
        issues=issues,
        action=ActionType.REPAIR_LEDGER,
    )
    delivery_end_tp = _parse_required_date(
        key.get("delivery_window_end"),
        rule_id=rule_id,
        label="交付窗口期截止点",
        location="ledger.key_timepoints.delivery_window_end",
        issues=issues,
        action=ActionType.REPAIR_LEDGER,
    )

    stabilization = key.get("stabilization_window") if isinstance(key.get("stabilization_window"), dict) else {}
    stabilization_start = _parse_required_date(
        stabilization.get("start"),
        rule_id=rule_id,
        label="稳定运行观察期开始点",
        location="ledger.key_timepoints.stabilization_window.start",
        issues=issues,
        action=ActionType.REPAIR_LEDGER,
    )
    stabilization_end = _parse_required_date(
        stabilization.get("end"),
        rule_id=rule_id,
        label="稳定运行观察期结束点",
        location="ledger.key_timepoints.stabilization_window.end",
        issues=issues,
        action=ActionType.REPAIR_LEDGER,
    )
    if stabilization_start and stabilization_end and stabilization_end < stabilization_start:
        issues.append(
            Issue(
                rule_id=rule_id,
                severity="error",
                message="稳定运行观察期结束点不得早于开始点",
                location="ledger.key_timepoints.stabilization_window",
                suggested_action=ActionType.REPAIR_LEDGER,
                repair_hint="调整稳定运行观察期起止顺序。",
            )
        )

    for label, dt, loc in [
        ("项目启动/交付窗口期开始", kickoff, "ledger.key_timepoints.kickoff"),
        ("交付窗口期开始", delivery_start_tp, "ledger.key_timepoints.delivery_window_start"),
        ("环境与接口口径冻结点", interface_freeze, "ledger.key_timepoints.interface_freeze"),
        ("POC启动点", poc_start, "ledger.key_timepoints.poc_start"),
        ("POC验收/结论点", poc_end, "ledger.key_timepoints.poc_end"),
        ("全功能开发完成点", full_function_complete, "ledger.key_timepoints.full_function_complete"),
        ("三方接口集成完成点", integration_complete, "ledger.key_timepoints.integration_complete"),
        ("UAT开始点", uat_start, "ledger.key_timepoints.uat_start"),
        ("UAT通过点", uat_pass, "ledger.key_timepoints.uat_pass"),
        ("上线窗口开始点", launch_window_start, "ledger.key_timepoints.launch_window_start"),
        ("稳定运行观察期开始点", stabilization_start, "ledger.key_timepoints.stabilization_window.start"),
        ("稳定运行观察期结束点", stabilization_end, "ledger.key_timepoints.stabilization_window.end"),
        ("移交完成点", handover_complete, "ledger.key_timepoints.handover_complete"),
        ("交付窗口期截止点", delivery_end_tp, "ledger.key_timepoints.delivery_window_end"),
    ]:
        _check_within_window(label, dt, loc)

    if kickoff and delivery_start and kickoff != delivery_start:
        issues.append(
            Issue(
                rule_id=rule_id,
                severity="error",
                message="项目启动/交付窗口期开始需等于 delivery_window.start",
                location="ledger.key_timepoints.kickoff",
                suggested_action=ActionType.REPAIR_LEDGER,
                repair_hint="将 kickoff 与 delivery_window.start 对齐。",
            )
        )
    if delivery_start_tp and delivery_start and delivery_start_tp != delivery_start:
        issues.append(
            Issue(
                rule_id=rule_id,
                severity="error",
                message="delivery_window_start 需等于 delivery_window.start",
                location="ledger.key_timepoints.delivery_window_start",
                suggested_action=ActionType.REPAIR_LEDGER,
                repair_hint="将 delivery_window_start 与 delivery_window.start 对齐。",
            )
        )
    if delivery_end_tp and delivery_end and delivery_end_tp != delivery_end:
        issues.append(
            Issue(
                rule_id=rule_id,
                severity="error",
                message="delivery_window_end 需等于 delivery_window.end",
                location="ledger.key_timepoints.delivery_window_end",
                suggested_action=ActionType.REPAIR_LEDGER,
                repair_hint="将 delivery_window_end 与 delivery_window.end 对齐。",
            )
        )

    poc_window = ledger.get("poc_window") if isinstance(ledger.get("poc_window"), dict) else {}
    poc_window_start = _parse_ymd(_as_text(poc_window.get("start")))
    poc_window_end = _parse_ymd(_as_text(poc_window.get("end")))
    if poc_start and poc_window_start and poc_start != poc_window_start:
        issues.append(
            Issue(
                rule_id=rule_id,
                severity="error",
                message="POC启动点需等于 poc_window.start",
                location="ledger.key_timepoints.poc_start",
                suggested_action=ActionType.REPAIR_LEDGER,
                repair_hint="将 poc_start 与 poc_window.start 对齐。",
            )
        )
    if poc_end and poc_window_end and poc_end != poc_window_end:
        issues.append(
            Issue(
                rule_id=rule_id,
                severity="error",
                message="POC验收/结论点需等于 poc_window.end",
                location="ledger.key_timepoints.poc_end",
                suggested_action=ActionType.REPAIR_LEDGER,
                repair_hint="将 poc_end 与 poc_window.end 对齐。",
            )
        )

    tables = ledger.get("tables") if isinstance(ledger.get("tables"), dict) else {}
    milestones = tables.get("milestones") if isinstance(tables, dict) else None
    if not isinstance(milestones, list) or len(milestones) < 5:
        issues.append(
            Issue(
                rule_id=rule_id,
                severity="error",
                message="milestones 必须至少包含 5 个阶段",
                location="ledger.tables.milestones",
                suggested_action=ActionType.REPAIR_LEDGER,
                repair_hint="补齐 5 个里程表阶段及时间段。",
            )
        )
        return RuleResult(passed=(len(issues) == 0), issues=issues)

    milestone_dates: list[tuple[date | None, date | None]] = []
    for idx in range(5):
        row = milestones[idx] if idx < len(milestones) else {}
        if not isinstance(row, dict):
            row = {}
        start_dt = _parse_required_date(
            row.get("start_date"),
            rule_id=rule_id,
            label=f"里程表第{idx + 1}阶段开始日期",
            location=f"ledger.tables.milestones[{idx}].start_date",
            issues=issues,
            action=ActionType.REPAIR_LEDGER,
        )
        end_dt = _parse_required_date(
            row.get("end_date"),
            rule_id=rule_id,
            label=f"里程表第{idx + 1}阶段结束日期",
            location=f"ledger.tables.milestones[{idx}].end_date",
            issues=issues,
            action=ActionType.REPAIR_LEDGER,
        )
        if start_dt and end_dt and end_dt < start_dt:
            issues.append(
                Issue(
                    rule_id=rule_id,
                    severity="error",
                    message=f"里程表第{idx + 1}阶段结束日期早于开始日期",
                    location=f"ledger.tables.milestones[{idx}]",
                    suggested_action=ActionType.REPAIR_LEDGER,
                    repair_hint="调整该阶段时间段顺序。",
                )
            )
        if start_dt and (start_dt < delivery_start or start_dt > delivery_end):
            issues.append(
                Issue(
                    rule_id=rule_id,
                    severity="error",
                    message=f"里程表第{idx + 1}阶段开始日期超出交付窗口",
                    location=f"ledger.tables.milestones[{idx}].start_date",
                    suggested_action=ActionType.REPAIR_LEDGER,
                    repair_hint=f"调整到 {delivery_start} ~ {delivery_end} 范围内。",
                )
            )
        if end_dt and (end_dt < delivery_start or end_dt > delivery_end):
            issues.append(
                Issue(
                    rule_id=rule_id,
                    severity="error",
                    message=f"里程表第{idx + 1}阶段结束日期超出交付窗口",
                    location=f"ledger.tables.milestones[{idx}].end_date",
                    suggested_action=ActionType.REPAIR_LEDGER,
                    repair_hint=f"调整到 {delivery_start} ~ {delivery_end} 范围内。",
                )
            )
        milestone_dates.append((start_dt, end_dt))

    m1_start, m1_end = milestone_dates[0]
    m2_start, m2_end = milestone_dates[1]
    m3_start, m3_end = milestone_dates[2]
    m4_start, m4_end = milestone_dates[3]
    m5_start, m5_end = milestone_dates[4]

    def _expect_equal(label: str, left: date | None, right: date | None, location: str) -> None:
        if left and right and left != right:
            issues.append(
                Issue(
                    rule_id=rule_id,
                    severity="error",
                    message=f"{label} 必须与里程表对应节点一致",
                    location=location,
                    suggested_action=ActionType.REPAIR_LEDGER,
                    repair_hint="对齐关键时间点与里程表阶段边界。",
                )
            )

    _expect_equal("项目启动/交付窗口期开始", kickoff, m1_start, "ledger.key_timepoints.kickoff")
    _expect_equal("环境与接口口径冻结点", interface_freeze, m1_end, "ledger.key_timepoints.interface_freeze")
    _expect_equal("POC启动点", poc_start, m2_start, "ledger.key_timepoints.poc_start")
    _expect_equal("POC验收/结论点", poc_end, m2_end, "ledger.key_timepoints.poc_end")
    _expect_equal("三方接口集成完成点", integration_complete, m3_end, "ledger.key_timepoints.integration_complete")
    _expect_equal("UAT开始点", uat_start, m4_start, "ledger.key_timepoints.uat_start")
    _expect_equal("UAT通过点", uat_pass, m4_end, "ledger.key_timepoints.uat_pass")
    _expect_equal("上线窗口开始点", launch_window_start, m5_start, "ledger.key_timepoints.launch_window_start")
    _expect_equal("移交完成点", handover_complete, m5_end, "ledger.key_timepoints.handover_complete")
    _expect_equal("交付窗口期截止点", delivery_end_tp, m5_end, "ledger.key_timepoints.delivery_window_end")

    for idx in range(4):
        prev_start, prev_end = milestone_dates[idx]
        next_start, _next_end = milestone_dates[idx + 1]
        if prev_end and next_start and next_start > prev_end + timedelta(days=1):
            issues.append(
                Issue(
                    rule_id=rule_id,
                    severity="error",
                    message=f"里程表阶段{idx + 1}与阶段{idx + 2}之间存在空档期",
                    location=f"ledger.tables.milestones[{idx + 1}].start_date",
                    suggested_action=ActionType.REPAIR_LEDGER,
                    repair_hint="确保下一阶段 start_date 紧接上一阶段 end_date（同日或次日）。",
                )
            )

    if full_function_complete and m3_start and m3_end:
        if full_function_complete < m3_start or full_function_complete > m3_end:
            issues.append(
                Issue(
                    rule_id=rule_id,
                    severity="error",
                    message="全功能开发完成点需落在阶段3时间段内",
                    location="ledger.key_timepoints.full_function_complete",
                    suggested_action=ActionType.REPAIR_LEDGER,
                    repair_hint="将全功能开发完成点调整到阶段3范围内。",
                )
            )

    if stabilization_start and m5_start and stabilization_start < m5_start:
        issues.append(
            Issue(
                rule_id=rule_id,
                severity="error",
                message="稳定运行观察期开始点不得早于阶段5开始",
                location="ledger.key_timepoints.stabilization_window.start",
                suggested_action=ActionType.REPAIR_LEDGER,
                repair_hint="将稳定观察期开始点对齐阶段5范围。",
            )
        )
    if stabilization_end and m5_end and stabilization_end > m5_end:
        issues.append(
            Issue(
                rule_id=rule_id,
                severity="error",
                message="稳定运行观察期结束点不得晚于阶段5结束",
                location="ledger.key_timepoints.stabilization_window.end",
                suggested_action=ActionType.REPAIR_LEDGER,
                repair_hint="将稳定观察期结束点对齐阶段5范围。",
            )
        )

    return RuleResult(passed=(len(issues) == 0), issues=issues)


def rule_scope_boundary_minimum(payload: Dict[str, Any]) -> RuleResult:
    ledger = payload.get("ledger") or {}
    scope = ledger.get("scope_boundary") if isinstance(ledger.get("scope_boundary"), dict) else {}
    issues: List[Issue] = []

    if not _list_non_empty(scope.get("inclusions")):
        issues.append(
            Issue(
                rule_id="LG2",
                severity="error",
                message="scope_boundary.inclusions 不能为空",
                location="ledger.scope_boundary.inclusions",
                suggested_action=ActionType.REPAIR_LEDGER,
                repair_hint="补齐范围包含项。",
            )
        )
    if not _list_non_empty(scope.get("exclusions")):
        issues.append(
            Issue(
                rule_id="LG2",
                severity="error",
                message="scope_boundary.exclusions 不能为空",
                location="ledger.scope_boundary.exclusions",
                suggested_action=ActionType.REPAIR_LEDGER,
                repair_hint="补齐范围排除项。",
            )
        )

    return RuleResult(passed=(len(issues) == 0), issues=issues)


def rule_metrics_kpi_minimum(payload: Dict[str, Any]) -> RuleResult:
    ledger = payload.get("ledger") or {}
    criteria = ledger.get("acceptance_criteria") if isinstance(ledger.get("acceptance_criteria"), dict) else {}
    issues: List[Issue] = []

    if not _as_text(criteria.get("acceptance_definition")):
        issues.append(
            Issue(
                rule_id="LG3",
                severity="error",
                message="acceptance_criteria.acceptance_definition 不能为空",
                location="ledger.acceptance_criteria.acceptance_definition",
                suggested_action=ActionType.REPAIR_LEDGER,
                repair_hint="补齐验收口径定义。",
            )
        )
    if not _as_text(criteria.get("exit_criteria")):
        issues.append(
            Issue(
                rule_id="LG3",
                severity="error",
                message="acceptance_criteria.exit_criteria 不能为空",
                location="ledger.acceptance_criteria.exit_criteria",
                suggested_action=ActionType.REPAIR_LEDGER,
                repair_hint="补齐退出/验收标准。",
            )
        )

    return RuleResult(passed=(len(issues) == 0), issues=issues)


def rule_sla_ops_minimum(payload: Dict[str, Any]) -> RuleResult:
    ledger = payload.get("ledger") or {}
    sla_support = ledger.get("sla_support") if isinstance(ledger.get("sla_support"), dict) else {}
    issues: List[Issue] = []

    for field in ("availability_target", "rto_target", "response_target", "support_window"):
        if not _as_text(sla_support.get(field)):
            issues.append(
                Issue(
                    rule_id="LG4",
                    severity="error",
                    message=f"sla_support.{field} 不能为空",
                    location=f"ledger.sla_support.{field}",
                    suggested_action=ActionType.REPAIR_LEDGER,
                    repair_hint="补齐 SLA/运维硬性口径。",
                )
            )

    return RuleResult(passed=(len(issues) == 0), issues=issues)


def rule_compliance_retention_minimum(payload: Dict[str, Any]) -> RuleResult:
    ledger = payload.get("ledger") or {}
    compliance = ledger.get("compliance_requirements") if isinstance(ledger.get("compliance_requirements"), dict) else {}
    issues: List[Issue] = []

    for field in ("data_residency", "regulatory_requirements", "security_controls"):
        if not _as_text(compliance.get(field)):
            issues.append(
                Issue(
                    rule_id="LG5",
                    severity="error",
                    message=f"compliance_requirements.{field} 不能为空",
                    location=f"ledger.compliance_requirements.{field}",
                    suggested_action=ActionType.REPAIR_LEDGER,
                    repair_hint="补齐合规硬性要求。",
                )
            )

    retention = compliance.get("retention") if isinstance(compliance.get("retention"), dict) else {}
    for field in ("business_data", "audit_log", "ops_log", "device_raw", "blockchain_data"):
        if not _as_text(retention.get(field)):
            issues.append(
                Issue(
                    rule_id="LG5",
                    severity="error",
                    message=f"compliance_requirements.retention.{field} 不能为空",
                    location=f"ledger.compliance_requirements.retention.{field}",
                    suggested_action=ActionType.REPAIR_LEDGER,
                    repair_hint="补齐留存口径。",
                )
            )

    return RuleResult(passed=(len(issues) == 0), issues=issues)


def rule_architecture_minimum(payload: Dict[str, Any]) -> RuleResult:
    ledger = payload.get("ledger") or {}
    perf = ledger.get("performance_capacity") if isinstance(ledger.get("performance_capacity"), dict) else {}
    issues: List[Issue] = []

    for field in ("response_time", "user_concurrency", "device_connections", "api_qps"):
        if not _as_text(perf.get(field)):
            issues.append(
                Issue(
                    rule_id="LG6",
                    severity="error",
                    message=f"performance_capacity.{field} 不能为空",
                    location=f"ledger.performance_capacity.{field}",
                    suggested_action=ActionType.REPAIR_LEDGER,
                    repair_hint="补齐性能/容量硬性指标。",
                )
            )

    return RuleResult(passed=(len(issues) == 0), issues=issues)


def rule_cost_resources_minimum(payload: Dict[str, Any]) -> RuleResult:
    ledger = payload.get("ledger") or {}
    cost = ledger.get("budget_resources") if isinstance(ledger.get("budget_resources"), dict) else {}
    issues: List[Issue] = []

    for field in ("budget_total", "resource_constraints"):
        if not _as_text(cost.get(field)):
            issues.append(
                Issue(
                    rule_id="LG7",
                    severity="error",
                    message=f"budget_resources.{field} 不能为空",
                    location=f"ledger.budget_resources.{field}",
                    suggested_action=ActionType.REPAIR_LEDGER,
                    repair_hint="补齐成本/商业口径。",
                )
            )

    return RuleResult(passed=(len(issues) == 0), issues=issues)


def _iter_placeholder_texts(llm_output: dict[str, Any]) -> List[tuple[str, str]]:
    placeholders = llm_output.get("placeholders", {}) if isinstance(llm_output, dict) else {}
    items: List[tuple[str, str]] = []
    if isinstance(placeholders, dict):
        for key, value in placeholders.items():
            if isinstance(value, str) and value.strip():
                items.append((key, value))
    return items


def _iter_table_texts(llm_output: dict[str, Any]) -> List[tuple[str, str]]:
    tables = llm_output.get("tables", {}) if isinstance(llm_output, dict) else {}
    items: List[tuple[str, str]] = []
    if not isinstance(tables, dict):
        return items
    for table_name, rows in tables.items():
        if not isinstance(rows, list):
            continue
        for idx, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            for key, value in row.items():
                if isinstance(value, str) and value.strip():
                    items.append((f"tables.{table_name}[{idx}].{key}", value))
    return items

def rule_doc_no_json_leak(payload: Dict[str, Any]) -> RuleResult:
    llm_output = payload.get("llm_output") or {}
    issues: List[Issue] = []
    for key, text in _iter_placeholder_texts(llm_output):
        paragraphs = [p for p in text.split("\n\n")]
        for idx, paragraph in enumerate(paragraphs):
            for pat in _JSON_LEAK_PATTERNS:
                m = pat.search(paragraph)
                if m:
                    issues.append(
                        Issue(
                            rule_id="DOC1",
                            severity="error",
                            message="正文出现结构化 JSON/数组泄漏，应渲染为自然语言。",
                            location=f"placeholders.{key}#p{idx}",
                            evidence={
                                "paragraph_index": idx,
                                "paragraph_text": paragraph,
                            },
                            suggested_action=ActionType.REWRITE_DOC_SECTION,
                            repair_hint="将该段落改写为自然语言描述，禁止出现 [] {} \"metric\": 等结构。",
                        )
                    )
                    break
    return RuleResult(passed=(len(issues) == 0), issues=issues)


def rule_doc_dates_within_delivery(payload: Dict[str, Any]) -> RuleResult:
    ledger = payload.get("ledger") or {}
    llm_output = payload.get("llm_output") or {}
    issues: List[Issue] = []

    delivery = ledger.get("delivery_window") if isinstance(ledger.get("delivery_window"), dict) else {}
    delivery_start = _parse_ymd(_as_text(delivery.get("start")))
    delivery_end = _parse_ymd(_as_text(delivery.get("end")))
    if not delivery_start or not delivery_end:
        return RuleResult(passed=True, issues=issues)

    def _check_text_dates(text: str, location: str) -> None:
        for dt in _extract_dates(text):
            if dt < delivery_start or dt > delivery_end:
                issues.append(
                    Issue(
                        rule_id="DOC2",
                        severity="error",
                        message="正文日期超出交付窗口期",
                        location=location,
                        suggested_action=ActionType.REWRITE_DOC_SECTION,
                        repair_hint=f"调整日期到 {delivery_start} ~ {delivery_end} 范围内。",
                    )
                )

    for key, text in _iter_placeholder_texts(llm_output):
        _check_text_dates(text, f"placeholders.{key}")
    for location, text in _iter_table_texts(llm_output):
        _check_text_dates(text, location)

    return RuleResult(passed=(len(issues) == 0), issues=issues)


_WEAK_TRADE_TRIGGERS = ("交易数据", "交易记录", "交易链路", "上链", "存证", "凭证", "核验", "确权", "溯源")
_STRONG_TRADE_TRIGGERS = (
    "撮合",
    "清结算",
    "结算",
    "对接交易所",
    "挂牌",
    "撮合成交",
    "订单撮合",
    "资金结算",
    "对外交易平台",
)
_TRADE_CONFUSION_PATTERNS = (
    "覆盖交易全链条",
    "交易全链条",
    "交易全链路",
    "支撑碳资产交易",
    "首笔交易",
    "交易平台",
    "交易模块",
    "交易撮合",
    "交易与溯源",
    "交易看板",
)
_BOUNDARY_HINTS = (
    "不做撮合",
    "不撮合",
    "不做清结算",
    "不清结算",
    "不提供撮合清结算",
    "不对接外部交易",
    "不对接外部交易平台",
    "不对接交易所",
    "非撮合",
    "非清结算",
)


def _is_title_like_paragraph(text: str) -> bool:
    s = text.strip()
    if not s:
        return True
    if len(s) < 15 and all(p not in s for p in ("。", "；", "！", "？", ".", ";", "!", "?")):
        return True
    return False


def rule_trade_boundary_sentence(payload: Dict[str, Any]) -> RuleResult:
    llm_output = payload.get("llm_output") or {}
    issues: List[Issue] = []
    doc_has_boundary = False
    doc_has_trade_mention = False
    first_trade_loc: str | None = None

    for key, text in _iter_placeholder_texts(llm_output):
        paragraphs = text.split("\n\n")
        for idx, p in enumerate(paragraphs):
            if _is_title_like_paragraph(p):
                continue
            if any(b in p for b in _BOUNDARY_HINTS):
                doc_has_boundary = True
            if any(t in p for t in _WEAK_TRADE_TRIGGERS) or any(t in p for t in _STRONG_TRADE_TRIGGERS) or any(
                t in p for t in _TRADE_CONFUSION_PATTERNS
            ):
                doc_has_trade_mention = True
                if first_trade_loc is None:
                    first_trade_loc = f"placeholders.{key}#p{idx}"

    if doc_has_trade_mention and not doc_has_boundary:
        issues.append(
            Issue(
                rule_id="R5",
                severity="error",
                message="全文出现“交易/上链/存证/溯源”等表述但缺少一次明确边界声明（非撮合/非清结算/不对接外部交易平台）。",
                location=first_trade_loc,
                suggested_action=ActionType.REWRITE_DOC_SECTION,
                repair_hint="在“范围与边界/系统集成与接口”等段落补充一次边界声明：仅存证核验/溯源查询，不提供撮合清结算，不对接外部交易平台/交易所。",
            )
        )

    for key, text in _iter_placeholder_texts(llm_output):
        paragraphs = text.split("\n\n")
        for idx, p in enumerate(paragraphs):
            if _is_title_like_paragraph(p):
                continue
            strong_hit = any(t in p for t in _STRONG_TRADE_TRIGGERS) or any(t in p for t in _TRADE_CONFUSION_PATTERNS)
            if not strong_hit:
                continue
            if any(b in p for b in _BOUNDARY_HINTS):
                continue
            issues.append(
                Issue(
                    rule_id="R5",
                    severity="error",
                    message="段落出现可能被误解为交易平台能力的表述，但未同段给出边界声明（非撮合/非清结算/不对接外部交易平台）。",
                    location=f"placeholders.{key}#p{idx}",
                    suggested_action=ActionType.REWRITE_DOC_SECTION,
                    repair_hint="优先将“交易”改写为“存证核验/凭证流转/交付确认”等，再补一句边界声明：不提供撮合清结算，不对接外部交易平台/交易所。",
                )
            )
    return RuleResult(passed=(len(issues) == 0), issues=issues)


_CLAIM_A_TERMS = (
    "已签署意向书",
    "已签署合同",
    "已验收",
    "已通过测试",
    "已通过压测",
    "已压测",
    "已完成压测",
    "已完成验证",
    "已验证达到",
    "已获得等保",
    "已通过等保",
    "已获得认证",
    "已完成认证",
)
_CLAIM_B_TERMS = ("已开展PoC", "已完成调研", "已完成原型评审", "已完成评审", "已开展试点")
_CLAIM_VERBS = ("达到", "实现", "满足", "通过", "证明", "显示", "表明", "验证表明", "实测显示", "压测结果")
_PERF_TERMS = ("TPS", "QPS", "并发", "响应时间", "延迟", "时延", "可用性", "准确率", "成功率", "吞吐", "ms", "毫秒", "%")
_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}|\d{4}年\d{1,2}月\d{1,2}日")
_EVIDENCE_FMT_RE = re.compile(r"(依据|见|参考)\s*[:：]?\s*.*?(\d{4}-\d{2}-\d{2}|\d{4}年\d{1,2}月\d{1,2}日)")
_EVIDENCE_ANCHOR_RE = re.compile(r"(依据|见|参考)\s*[:：]?\s*(.{0,120})")
_PLAN_HINT_RE = re.compile(r"(计划|将|拟|预计|目标)[^。；\n]{0,16}(完成|开展|进行|验证|测试|评审|验收|达成)")
_DONE_RE = re.compile(
    r"(已经|已(完成|通过|验收|上线|投产|取得|签署|实测|压测|开展|验证|获得)|完成验收|通过验收|完成测试|通过测试)"
)

_REF_POLICY_WORDS = ("规划", "政策", "通知", "条例", "办法", "规范", "标准", "指导意见", "实施方案")
_REF_TEST_WORDS = ("测试", "压测", "性能", "JMeter", "测试报告", "压测报告", "基准测试")
_REF_POC_WORDS = ("PoC", "POC", "试点", "联调")
_REF_MEETING_WORDS = ("纪要", "会议", "访谈", "评审", "确认单")
_REF_CONTRACT_WORDS = ("合同", "意向书", "签署", "框架协议")
_REF_ACCEPTANCE_WORDS = ("验收", "UAT", "上线", "投产")
_REF_SECURITY_WORDS = ("等保", "测评", "安全评估", "渗透测试", "漏洞扫描")


def _ref_text_fields(ref: Any) -> list[str]:
    if isinstance(ref, str):
        return [ref]
    if not isinstance(ref, dict):
        return []
    vals: list[str] = []
    for k in ("ref_id", "id", "title", "name", "type", "date", "version", "note"):
        v = ref.get(k)
        if isinstance(v, str) and v.strip():
            vals.append(v.strip())
    return vals


def _ref_id(ref: Any) -> str:
    if isinstance(ref, dict):
        for k in ("ref_id", "id"):
            v = ref.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
    return ""


def _ref_title(ref: Any) -> str:
    if isinstance(ref, dict):
        v = ref.get("title") or ref.get("name")
        if isinstance(v, str) and v.strip():
            return v.strip()
    if isinstance(ref, str):
        return ref.strip()
    return ""


def _ref_category(ref: Any) -> str:
    text = " ".join(_ref_text_fields(ref))
    if any(w in text for w in _REF_POLICY_WORDS):
        return "policy"
    if any(w in text for w in _REF_SECURITY_WORDS):
        return "security"
    if any(w in text for w in _REF_ACCEPTANCE_WORDS):
        return "acceptance"
    if any(w in text for w in _REF_CONTRACT_WORDS):
        return "contract"
    if any(w in text for w in _REF_TEST_WORDS):
        return "test"
    if any(w in text for w in _REF_POC_WORDS):
        return "poc"
    if any(w in text for w in _REF_MEETING_WORDS):
        return "meeting"
    return "other"


def _matched_refs_in_paragraph(paragraph: str, references: Any) -> list[Any]:
    if not isinstance(references, list):
        return []
    hits: list[Any] = []
    for ref in references:
        rid = _ref_id(ref)
        title = _ref_title(ref)
        if rid and rid in paragraph:
            hits.append(ref)
            continue
        if title and title in paragraph:
            hits.append(ref)
            continue
    return hits


def _claim_required_categories(paragraph: str, claim_level: str) -> set[str]:
    if "签署" in paragraph or "意向书" in paragraph or "合同" in paragraph:
        return {"contract"}
    if "验收" in paragraph or "UAT" in paragraph or "上线" in paragraph or "投产" in paragraph:
        return {"acceptance"}
    if "等保" in paragraph or "安全" in paragraph or "渗透" in paragraph:
        return {"security"}
    if any(t in paragraph for t in _PERF_TERMS) and re.search(r"\d+\.?\d*", paragraph):
        return {"test"}
    if claim_level == "B":
        return {"meeting", "poc", "test"}
    return {"test", "poc", "meeting", "contract", "acceptance", "security"}


def rule_strong_claim_requires_evidence(payload: Dict[str, Any]) -> RuleResult:
    ledger = payload.get("ledger") or {}
    llm_output = payload.get("llm_output") or {}
    references = ledger.get("references") or []
    has_refs = bool(references)
    issues: List[Issue] = []
    for key, text in _iter_placeholder_texts(llm_output):
        paragraphs = text.split("\n\n")
        for idx, p in enumerate(paragraphs):
            if _is_title_like_paragraph(p):
                continue
            # Planned statements should not be treated as completed strong claims.
            plan_tokens = ("计划", "拟", "预计", "将", "目标", "计划验证", "拟验证", "预计验证", "计划通过", "拟通过")
            if any(t in p for t in plan_tokens):
                continue
            has_done = bool(_DONE_RE.search(p))
            claim_level: str | None = None
            if any(t in p for t in _CLAIM_A_TERMS):
                claim_level = "A"
            elif any(t in p for t in _CLAIM_B_TERMS):
                claim_level = "B"
            else:
                has_number = bool(re.search(r"\d+\.?\d*", p))
                has_perf = any(t in p for t in _PERF_TERMS)
                has_claim_verb = any(t in p for t in _CLAIM_VERBS)
                # Only treat as strong claim if there is a completion verb.
                # Requirement-style sentences (e.g., "应/需/必须/目标") should not be treated as completed claims.
                requirement_tokens = ("应", "需", "必须", "要求", "目标", "计划", "拟", "预计")
                has_requirement = any(t in p for t in requirement_tokens)
                if has_done and not has_requirement and ((has_perf and has_number) or has_claim_verb):
                    claim_level = "A"

            if claim_level is None:
                continue

            has_evidence = bool(_EVIDENCE_FMT_RE.search(p))

            if not has_refs:
                issues.append(
                    Issue(
                        rule_id="R6",
                        severity="error",
                        message="强结论需台账 references 支撑；缺少可审计证据时必须降级为计划验证。",
                        location=f"placeholders.{key}#p{idx}",
                        evidence={"claim_level": claim_level},
                        suggested_action=ActionType.REWRITE_DOC_SECTION,
                        repair_hint="若无台账证据，请将“已/已通过/已验证”降级为“计划在××阶段完成验证（退出标准…）”；不要凭空编造报告/纪要。",
                    )
                )
                continue

            if not has_evidence:
                issues.append(
                    Issue(
                        rule_id="R6",
                        severity="error",
                        message="强结论需可审计证据格式（依据/见/参考 + 日期），否则降级为计划验证。",
                        location=f"placeholders.{key}#p{idx}",
                        evidence={"claim_level": claim_level},
                        suggested_action=ActionType.REWRITE_DOC_SECTION,
                        repair_hint="必须将强结论降级为计划验证（去掉“已/已通过/已验证/实测”等完成态表述），不要补充证据或日期。",
                    )
                )
                continue

            matched = _matched_refs_in_paragraph(p, references)
            if not matched:
                issues.append(
                    Issue(
                        rule_id="R6",
                        severity="error",
                        message="强结论的证据需绑定台账 references（段内必须包含 references 的标题或ID + 日期）。",
                        location=f"placeholders.{key}#p{idx}",
                        evidence={"claim_level": claim_level},
                        suggested_action=ActionType.REWRITE_DOC_SECTION,
                        repair_hint="必须将强结论降级为计划验证（去掉“已/已通过/已验证/实测”等完成态表述），不要补充证据或日期。",
                    )
                )
                continue

            required = _claim_required_categories(p, claim_level)
            acceptable = []
            for ref in matched:
                cat = _ref_category(ref)
                if cat == "policy":
                    continue
                if cat in required:
                    acceptable.append(ref)
            if not acceptable:
                titles = [t for t in (_ref_title(r) for r in matched) if t]
                issues.append(
                    Issue(
                        rule_id="R6",
                        severity="error",
                        message="强结论的证据类型不匹配：压测/签署/验收/安全等结论不得引用政策规划类材料。",
                        location=f"placeholders.{key}#p{idx}",
                        evidence={"claim_level": claim_level, "matched_titles": titles[:3]},
                        suggested_action=ActionType.REWRITE_DOC_SECTION,
                        repair_hint="若台账缺少匹配类型的证据（测试报告/压测报告/纪要/意向书/验收报告/测评报告），请将强结论降级为“计划在××阶段完成验证”。",
                    )
                )
    return RuleResult(passed=(len(issues) == 0), issues=issues)


def rule_risk_reference_consistency(payload: Dict[str, Any]) -> RuleResult:
    ledger = payload.get("ledger") or {}
    llm_output = payload.get("llm_output") or {}
    risk = ledger.get("risk") or {}
    register = risk.get("register") or []
    if not isinstance(register, list) or not register:
        return RuleResult(passed=True)

    risk_map: Dict[str, str] = {}
    for item in register:
        if not isinstance(item, dict):
            continue
        rid = str(item.get("id", "")).strip().upper()
        desc = str(item.get("description", "")).strip()
        if rid and desc:
            risk_map[rid] = desc

    if not risk_map:
        return RuleResult(passed=True)

    issues: List[Issue] = []
    pattern = re.compile(r"(R\d{2})(?:\s*（([^）]+)）)?")
    for key, text in _iter_placeholder_texts(llm_output):
        if not isinstance(text, str):
            continue
        for idx, p in enumerate(text.split("\\n\\n")):
            for rid, desc in pattern.findall(p):
                rid_norm = rid.upper()
                expected = risk_map.get(rid_norm)
                if not expected:
                    issues.append(
                        Issue(
                            rule_id="R15",
                            severity="error",
                            message=f"正文引用风险编号{rid}但台账中不存在该编号。",
                            location=f"placeholders.{key}#p{idx}",
                            suggested_action=ActionType.REWRITE_DOC_SECTION,
                            repair_hint="请仅引用台账风险编号，并按‘Rxx（台账描述）’格式绑定描述。",
                        )
                    )
                    continue
                if not desc:
                    issues.append(
                        Issue(
                            rule_id="R15",
                            severity="error",
                            message=f"正文引用风险编号{rid}但未绑定台账描述。",
                            location=f"placeholders.{key}#p{idx}",
                            suggested_action=ActionType.REWRITE_DOC_SECTION,
                            repair_hint=f"请改为‘{rid_norm}（{expected}）’格式。",
                        )
                    )
                    continue
                if expected not in desc:
                    issues.append(
                        Issue(
                            rule_id="R15",
                            severity="error",
                            message=f"正文中{rid}的描述与台账不一致。",
                            location=f"placeholders.{key}#p{idx}",
                            evidence={"expected": expected, "found": desc},
                            suggested_action=ActionType.REWRITE_DOC_SECTION,
                            repair_hint=f"请将描述改为台账描述：{expected}。",
                        )
                    )

    return RuleResult(passed=(len(issues) == 0), issues=issues)


def rule_risk_id_coverage(payload: Dict[str, Any]) -> RuleResult:
    ledger = payload.get("ledger") or {}
    risk = ledger.get("risk") or {}
    register = risk.get("register") or []
    if not isinstance(register, list) or not register:
        return RuleResult(passed=True)

    risk_ids = {str(item.get("id", "")).strip().upper() for item in register if isinstance(item, dict)}
    risk_ids = {rid for rid in risk_ids if rid}
    if not risk_ids:
        return RuleResult(passed=True)

    issues: List[Issue] = []
    pattern = re.compile(r"R\d{2}")
    for field, label in (("monitoring_plan", "risk.monitoring_plan"), ("contingency_plans", "risk.contingency_plans")):
        text = str(risk.get(field, "")).strip()
        if not text:
            continue
        referenced = {rid.upper() for rid in pattern.findall(text)}
        missing = sorted([rid for rid in referenced if rid not in risk_ids])
        if missing:
            issues.append(
                Issue(
                    rule_id="R16",
                    severity="error",
                    message=f"风险说明引用了不存在的编号：{', '.join(missing)}",
                    location=label,
                    suggested_action=ActionType.REPAIR_LEDGER,
                    repair_hint="仅引用 risk.register 中存在的风险编号。",
                )
            )

    return RuleResult(passed=(len(issues) == 0), issues=issues)


def _risk_trigger_text_map(register: list[dict[str, Any]]) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in register:
        if not isinstance(item, dict):
            continue
        rid = str(item.get("id", "")).strip()
        trigger = str(item.get("trigger", "")).strip()
        if rid and trigger:
            out[rid] = trigger
    return out


def _extract_threshold_tokens(text: str) -> list[str]:
    pattern = re.compile(r"\\d+\\s*(秒|分钟|小时|天)")
    return [m.group(0) for m in pattern.finditer(text)]


def rule_risk_trigger_threshold_consistency(payload: Dict[str, Any]) -> RuleResult:
    ledger = payload.get("ledger") or {}
    llm_output = payload.get("llm_output") or {}
    risk = ledger.get("risk") or {}
    register = risk.get("register") or []
    if not isinstance(register, list) or not register:
        return RuleResult(passed=True)

    trigger_map = _risk_trigger_text_map(register)
    if not trigger_map:
        return RuleResult(passed=True)

    issues: List[Issue] = []
    pattern = re.compile(r"(R\d{2})(?:\s*（([^）]+)）)?")
    for key, text in _iter_placeholder_texts(llm_output):
        if not isinstance(text, str):
            continue
        for idx, p in enumerate(text.split("\\n\\n")):
            refs = pattern.findall(p)
            if not refs:
                continue
            para_thresholds = _extract_threshold_tokens(p)
            if not para_thresholds:
                continue
            for rid, _ in refs:
                trigger = trigger_map.get(rid.upper(), "")
                if not trigger:
                    continue
                expected_thresholds = _extract_threshold_tokens(trigger)
                if not expected_thresholds:
                    continue
                if not any(t in trigger for t in para_thresholds):
                    issues.append(
                        Issue(
                            rule_id="R17",
                            severity="error",
                            message=f"风险{rid}触发阈值在正文与台账不一致。",
                            location=f"placeholders.{key}#p{idx}",
                            evidence={"expected": expected_thresholds, "found": para_thresholds},
                            suggested_action=ActionType.REWRITE_DOC_SECTION,
                            repair_hint="风险阈值必须与台账 trigger 完全一致；如需引用阈值，请直接复用台账触发条件中的数字与单位。",
                        )
                    )
    return RuleResult(passed=(len(issues) == 0), issues=issues)


_FORBIDDEN_SUBJECTIVE_WORDS = ("极其", "绝对", "最先进", "第一", "领先", "完美", "无与伦比")


def compute_soft_metrics(ctx: PipelineContext) -> Dict[str, Any]:
    llm_output = ctx.llm_output or {}
    ledger = ctx.ledger or {}
    
    # 1. Subjective density (S1)
    subjective_hits = 0
    total_chars = 0
    total_paragraphs = 0
    
    # 2. New number risk (S2)
    # Extract numbers from ledger
    def _extract_numbers(data: Any) -> set[str]:
        nums = set()
        if isinstance(data, dict):
            for v in data.values():
                nums.update(_extract_numbers(v))
        elif isinstance(data, list):
            for v in data:
                nums.update(_extract_numbers(v))
        elif isinstance(data, (int, float)):
            nums.add(str(data))
        elif isinstance(data, str):
            # Find numbers in string
            for n in re.findall(r"\d+\.?\d*", data):
                nums.add(n)
        return nums

    ledger_numbers = _extract_numbers(ledger)
    new_number_hits = 0
    
    for _, text in _iter_placeholder_texts(llm_output):
        total_chars += len(text)
        paragraphs = text.split("\n\n")
        total_paragraphs += len(paragraphs)
        
        # S1 count
        for word in _FORBIDDEN_SUBJECTIVE_WORDS:
            subjective_hits += text.count(word)
        
        # S2 count
        doc_numbers = re.findall(r"\d+\.?\d*", text)
        for n in doc_numbers:
            if n not in ledger_numbers:
                new_number_hits += 1
                
    char_count_k = total_chars / 1000.0 if total_chars > 0 else 1.0
    
    return {
        "subjective_density_per_k": subjective_hits / char_count_k,
        "new_number_risk_per_k": new_number_hits / char_count_k,
        "doc_char_count": total_chars,
        "total_paragraphs": total_paragraphs,
    }


RULES: List[Rule] = [
    Rule("LG1", Stage.LEDGER, "Ledger/时间窗口有效性", "error", rule_time_windows_valid),
    Rule("LG2", Stage.LEDGER, "Ledger/范围边界完整性", "error", rule_scope_boundary_minimum),
    Rule("LG3", Stage.LEDGER, "Ledger/验收口径完整性", "error", rule_metrics_kpi_minimum),
    Rule("LG4", Stage.LEDGER, "Ledger/SLA硬性指标完整性", "error", rule_sla_ops_minimum),
    Rule("LG5", Stage.LEDGER, "Ledger/合规与留存硬性口径完整性", "error", rule_compliance_retention_minimum),
    Rule("LG6", Stage.LEDGER, "Ledger/性能与容量硬性口径完整性", "error", rule_architecture_minimum),
    Rule("LG7", Stage.LEDGER, "Ledger/预算与资源上限完整性", "error", rule_cost_resources_minimum),
    Rule("LG8", Stage.LEDGER, "Ledger/关键时间点与里程表联动", "error", rule_key_timepoints_and_milestones),
    Rule("DOC1", Stage.DOC_POST, "Doc/正文JSON泄漏禁止", "error", rule_doc_no_json_leak),
    Rule("DOC2", Stage.DOC_POST, "Doc/日期需落在交付窗口内", "error", rule_doc_dates_within_delivery),
]
