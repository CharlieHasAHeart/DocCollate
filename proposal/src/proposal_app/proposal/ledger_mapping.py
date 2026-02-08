from __future__ import annotations

from typing import Any, Iterable

Path = tuple[str, ...]


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return any(_has_value(item) for item in value)
    if isinstance(value, dict):
        return any(_has_value(item) for item in value.values())
    return True


def _get_from_path(data: dict[str, Any], path: Path) -> Any:
    current: Any = data
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _set_path(target: dict[str, Any], path: Path, value: Any) -> None:
    current = target
    for key in path[:-1]:
        if key not in current or not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]
    current[path[-1]] = value


def _prune_value(value: Any) -> Any:
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k, v in value.items():
            pruned = _prune_value(v)
            if _has_value(pruned):
                out[k] = pruned
        return out
    if isinstance(value, list):
        items: list[Any] = []
        for item in value:
            pruned = _prune_value(item)
            if _has_value(pruned):
                items.append(pruned)
        return items
    if isinstance(value, str):
        return value.strip()
    return value


def build_ledger_scope(
    ledger: dict[str, Any] | None,
    placeholders: Iterable[str],
    *,
    extra_paths: Iterable[Path] | None = None,
) -> dict[str, Any]:
    if not isinstance(ledger, dict):
        return {}
    scope = _prune_value(ledger)
    if not isinstance(scope, dict):
        scope = {}
    if "schema_version" in ledger and "schema_version" not in scope:
        scope["schema_version"] = ledger.get("schema_version")
    if extra_paths:
        for path in extra_paths:
            value = _get_from_path(ledger, path)
            if _has_value(value):
                _set_path(scope, path, value)
    return scope
