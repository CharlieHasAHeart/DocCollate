from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class PoolCandidate:
    candidate_id: str
    app_type: str
    content: str


ENV_FIELD_KEYS = (
    "tech__hardware_dev",
    "tech__hardware_run",
    "tech__os_dev",
    "tech__dev_tools",
    "tech__os_run",
    "tech__run_support",
)


_RESOURCE_PATH = Path(__file__).resolve().parents[1] / "resources" / "env_config_pools.yaml"


def _load_pools_from_yaml(path: Path) -> dict[str, list[PoolCandidate]]:
    if not path.exists():
        raise FileNotFoundError(f"env config pool yaml not found: {path}")

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("env config pool yaml root must be a mapping")

    pools: dict[str, list[PoolCandidate]] = {}
    for field in ENV_FIELD_KEYS:
        items = raw.get(field, [])
        if not isinstance(items, list):
            raise ValueError(f"{field} must be a list in env config pool yaml")
        candidates: list[PoolCandidate] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            candidate_id = str(item.get("candidate_id", "")).strip()
            app_type = str(item.get("app_type", "")).strip()
            content = str(item.get("content", "")).strip()
            if not candidate_id or not app_type or not content:
                continue
            candidates.append(
                PoolCandidate(candidate_id=candidate_id, app_type=app_type, content=content)
            )
        pools[field] = candidates

    return pools


ENV_CONFIG_POOLS: dict[str, list[PoolCandidate]] = _load_pools_from_yaml(_RESOURCE_PATH)


def serialize_pools_for_prompt() -> dict[str, list[dict[str, str]]]:
    out: dict[str, list[dict[str, str]]] = {}
    for field, candidates in ENV_CONFIG_POOLS.items():
        out[field] = [
            {"candidate_id": c.candidate_id, "app_type": c.app_type, "content": c.content}
            for c in candidates
        ]
    return out
