from __future__ import annotations

from typing import Any

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

TABLE_MIN_SPECS = {
    "terms": (4, ["term", "definition"]),
    "resources": (2, ["name", "level", "spec", "source", "cost"]),
    "costs": (6, ["item", "amount", "note"]),
}
MILESTONE_LEN = 5
MILESTONE_KEYS = ["phase", "tasks", "start_date", "end_date", "deliverables"]


def validate_schema(output: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(output, dict):
        return ["output must be an object"]

    for key in ["placeholders", "tables"]:
        if key not in output:
            errors.append(f"missing key: {key}")

    allowed_top = {"placeholders", "tables", "evidence"}
    extra_top = set(output.keys()) - allowed_top
    if extra_top:
        errors.append(f"unexpected top-level keys: {sorted(extra_top)}")

    placeholders = output.get("placeholders")
    if isinstance(placeholders, dict):
        extra = set(placeholders.keys()) - set(PLACEHOLDER_FIELDS)
        missing = set(PLACEHOLDER_FIELDS) - set(placeholders.keys())
        if extra:
            errors.append(f"unexpected placeholder keys: {sorted(extra)}")
        if missing:
            errors.append(f"missing placeholder keys: {sorted(missing)}")
        for key in PLACEHOLDER_FIELDS:
            if key in placeholders and not isinstance(placeholders[key], str):
                errors.append(f"placeholder {key} must be string")
    else:
        errors.append("placeholders must be object")

    tables = output.get("tables")
    if isinstance(tables, dict):
        expected_tables = set(TABLE_MIN_SPECS.keys()) | {"milestones"}
        extra = set(tables.keys()) - expected_tables
        missing = expected_tables - set(tables.keys())
        if extra:
            errors.append(f"unexpected tables keys: {sorted(extra)}")
        if missing:
            errors.append(f"missing tables keys: {sorted(missing)}")
        for table_name, (min_len, item_keys) in TABLE_MIN_SPECS.items():
            items = tables.get(table_name)
            if not isinstance(items, list):
                errors.append(f"table {table_name} must be array")
                continue
            if len(items) < min_len:
                errors.append(f"table {table_name} must have at least {min_len} rows")
            for idx, item in enumerate(items):
                if not isinstance(item, dict):
                    errors.append(f"table {table_name}[{idx}] must be object")
                    continue
                extra_item = set(item.keys()) - set(item_keys)
                missing_item = set(item_keys) - set(item.keys())
                if extra_item:
                    errors.append(f"table {table_name}[{idx}] unexpected keys: {sorted(extra_item)}")
                if missing_item:
                    errors.append(f"table {table_name}[{idx}] missing keys: {sorted(missing_item)}")
                for k in item_keys:
                    if k in item and not isinstance(item[k], str):
                        errors.append(f"table {table_name}[{idx}].{k} must be string")

        milestones = tables.get("milestones")
        if not isinstance(milestones, list):
            errors.append("table milestones must be array")
        else:
            if len(milestones) != MILESTONE_LEN:
                errors.append(f"table milestones must have {MILESTONE_LEN} rows")
            for idx, item in enumerate(milestones):
                if not isinstance(item, dict):
                    errors.append(f"table milestones[{idx}] must be object")
                    continue
                extra_item = set(item.keys()) - set(MILESTONE_KEYS)
                missing_item = set(MILESTONE_KEYS) - set(item.keys())
                if extra_item:
                    errors.append(f"table milestones[{idx}] unexpected keys: {sorted(extra_item)}")
                if missing_item:
                    errors.append(f"table milestones[{idx}] missing keys: {sorted(missing_item)}")
                for k in MILESTONE_KEYS:
                    if k in item and not isinstance(item[k], str):
                        errors.append(f"table milestones[{idx}].{k} must be string")
    else:
        errors.append("tables must be object")

    evidence = output.get("evidence")
    if evidence is not None:
        if not isinstance(evidence, list):
            errors.append("evidence must be array")
        else:
            for idx, item in enumerate(evidence):
                if not isinstance(item, dict):
                    errors.append(f"evidence[{idx}] must be object")
                    continue
                allowed_keys = {"field", "chunks"}
                extra_keys = set(item.keys()) - allowed_keys
                if extra_keys:
                    errors.append(f"evidence[{idx}] unexpected keys: {sorted(extra_keys)}")
                if "field" not in item or "chunks" not in item:
                    errors.append(f"evidence[{idx}] missing keys")
                    continue
                if not isinstance(item["field"], str):
                    errors.append(f"evidence[{idx}].field must be string")
                if not isinstance(item["chunks"], list) or not all(
                    isinstance(x, str) for x in item["chunks"]
                ):
                    errors.append(f"evidence[{idx}].chunks must be array of strings")

    return errors
