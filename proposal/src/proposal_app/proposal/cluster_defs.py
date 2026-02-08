from __future__ import annotations

from typing import Any

PLACEHOLDER_FIELDS = [
    "{{ purpose }}",
    "{{ scope }}",
    "{{ project_source }}",
    "{{ current_state_and_pain_points }}",
    "{{ project_scope_and_objectives }}",
    "{{ success_metrics_and_baseline }}",
    "{{ target_customers }}",
    "{{ constraints_and_assumptions }}",
    "{{ core_scenarios_and_user_roles }}",
    "{{ requirements_overview }}",
    "{{ mvp_scope_and_boundaries }}",
    "{{ core_product_features }}",
    "{{ data_and_reporting_definitions }}",
    "{{ ui_prototypes_and_page_list }}",
    "{{ product_roadmap }}",
    "{{ architecture_and_key_decisions }}",
    "{{ data_architecture_and_governance }}",
    "{{ system_integration_and_apis }}",
    "{{ security_access_and_audit }}",
    "{{ performance_capacity_sla }}",
    "{{ deployment_architecture_and_environment }}",
    "{{ observability_and_operations }}",
    "{{ technical_feasibility_and_poc_plan }}",
    "{{ market_and_customer_feasibility }}",
    "{{ business_model_and_pricing }}",
    "{{ compliance_requirements }}",
    "{{ ip_and_open_source_compliance }}",
    "{{ team_structure_and_responsibilities }}",
    "{{ testing_and_quality_plan }}",
    "{{ communication_and_governance }}",
    "{{ risk_monitoring_and_contingency }}",
    "{{ rollout_and_pilot_strategy }}",
    "{{ operations_model_and_support_sla }}",
    "{{ training_and_enablement_plan }}",
    "{{ operational_metrics_and_continuous_improvement }}",
    "{{ summary }}",
]

TABLE_MIN_SPECS = {
    "terms": (4, ["term", "definition"]),
    "milestones": (5, ["phase", "tasks", "start_date", "end_date", "deliverables"]),
    "resources": (2, ["name", "level", "spec", "source", "cost"]),
    "references_list": (1, ["title", "type", "date", "version", "note"]),
    "risk_register": (3, ["id", "description", "probability", "impact", "level", "trigger", "mitigation"]),
}
MILESTONE_LEN = 5
MILESTONE_KEYS = ["phase", "tasks", "start_date", "end_date", "deliverables"]


def build_empty_output() -> dict[str, Any]:
    placeholders = {key: "" for key in PLACEHOLDER_FIELDS}
    tables: dict[str, list[dict[str, str]]] = {}
    for table_name, (min_len, keys) in TABLE_MIN_SPECS.items():
        rows: list[dict[str, str]] = []
        for _ in range(max(min_len, 1)):
            rows.append({k: "" for k in keys})
        tables[table_name] = rows
    tables["milestones"] = [{k: "" for k in MILESTONE_KEYS} for _ in range(MILESTONE_LEN)]
    return {"placeholders": placeholders, "tables": tables}
