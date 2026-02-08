from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .client import LLMRuntime
from .pydantic_agent import run_pydantic_agent


class TimeWindow(BaseModel):
    start: str
    end: str


class ScopeBoundary(BaseModel):
    inclusions: list[str] = Field(min_length=1)
    exclusions: list[str] = Field(min_length=1)


class AcceptanceCriteria(BaseModel):
    acceptance_definition: str
    exit_criteria: str


class PerformanceCapacity(BaseModel):
    response_time: str
    user_concurrency: str
    device_connections: str
    api_qps: str
    capacity_notes: str


class SlaSupport(BaseModel):
    availability_target: str
    rto_target: str
    response_target: str
    support_window: str


class RetentionPolicy(BaseModel):
    business_data: str
    audit_log: str
    ops_log: str
    device_raw: str
    blockchain_data: str
    notes: str


class ComplianceRequirements(BaseModel):
    data_residency: str
    regulatory_requirements: str
    security_controls: str
    retention: RetentionPolicy


class BudgetResources(BaseModel):
    budget_total: str
    resource_constraints: str


class TermRow(BaseModel):
    term: str = Field(min_length=1)
    definition: str = Field(min_length=1)


class ResourceRow(BaseModel):
    name: str = Field(min_length=1)
    level: str = Field(min_length=1)
    spec: str = Field(min_length=1)
    source: str = Field(min_length=1)
    cost: str = Field(min_length=1)


class MilestoneRow(BaseModel):
    phase: str = Field(min_length=1)
    tasks: str = Field(min_length=1)
    start_date: str = Field(min_length=1)
    end_date: str = Field(min_length=1)
    deliverables: str = Field(min_length=1)


class ReferenceRow(BaseModel):
    title: str = Field(min_length=1)
    type: str = Field(min_length=1)
    date: str = Field(min_length=1)
    version: str = Field(min_length=1)
    note: str = Field(min_length=1)


class RiskRow(BaseModel):
    id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    probability: str = Field(min_length=1)
    impact: str = Field(min_length=1)
    level: str = Field(min_length=1)
    trigger: str = Field(min_length=1)
    mitigation: str = Field(min_length=1)


class KeyTimepoints(BaseModel):
    kickoff: str = Field(min_length=1)
    delivery_window_start: str = Field(min_length=1)
    interface_freeze: str = Field(min_length=1)
    poc_start: str = Field(min_length=1)
    poc_end: str = Field(min_length=1)
    full_function_complete: str = Field(min_length=1)
    integration_complete: str = Field(min_length=1)
    uat_start: str = Field(min_length=1)
    uat_pass: str = Field(min_length=1)
    launch_window_start: str = Field(min_length=1)
    stabilization_window: TimeWindow
    handover_complete: str = Field(min_length=1)
    delivery_window_end: str = Field(min_length=1)


class LedgerTables(BaseModel):
    terms: list[TermRow] = Field(min_length=4)
    resources: list[ResourceRow] = Field(min_length=2)
    milestones: list[MilestoneRow] = Field(min_length=5)
    references_list: list[ReferenceRow] = Field(min_length=1)
    risk_register: list[RiskRow] = Field(min_length=3)


class LedgerOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str
    delivery_window: TimeWindow
    poc_window: TimeWindow
    key_timepoints: KeyTimepoints
    scope_boundary: ScopeBoundary
    acceptance_criteria: AcceptanceCriteria
    performance_capacity: PerformanceCapacity
    sla_support: SlaSupport
    compliance_requirements: ComplianceRequirements
    budget_resources: BudgetResources
    tables: LedgerTables


def call_ledger_with_pydantic(prompt: str, runtime: LLMRuntime) -> dict[str, Any]:
    return run_pydantic_agent(
        prompt=prompt,
        runtime=runtime,
        result_model=LedgerOutput,
        system_prompt="You are a careful JSON generator. Output JSON only.",
    )
