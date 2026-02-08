from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources


@dataclass(frozen=True)
class FieldPoolCandidate:
    candidate_id: str
    label: str


def _resource_text() -> str:
    return resources.files("assessment_form.resources").joinpath("field_pools.json").read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def load_field_pools() -> dict[str, list[FieldPoolCandidate]]:
    raw = json.loads(_resource_text())
    out: dict[str, list[FieldPoolCandidate]] = {}
    for field, items in raw.items():
        picks: list[FieldPoolCandidate] = []
        for item in items:
            cid = str(item.get("candidate_id", "")).strip()
            label = str(item.get("label", "")).strip()
            if cid and label:
                picks.append(FieldPoolCandidate(candidate_id=cid, label=label))
        if picks:
            out[field] = picks
    return out


def serialize_field_pools() -> dict[str, list[dict[str, str]]]:
    pools = load_field_pools()
    return {
        key: [{"candidate_id": item.candidate_id, "label": item.label} for item in items]
        for key, items in pools.items()
    }

