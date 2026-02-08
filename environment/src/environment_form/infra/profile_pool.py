from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_RESOURCE = Path(__file__).resolve().parents[1] / "resources" / "env_profile_pools.yaml"


@dataclass(frozen=True)
class EnvProfile:
    app_type: str
    keywords: list[str]
    env__server_os: str
    env__server_soft: str
    env__server_model: str
    env__server_config: str
    env__server_id: str
    env__client_os: str
    env__client_soft: str
    env__client_model: str
    env__client_config: str
    env__client_id: str


def _load_yaml() -> dict[str, Any]:
    raw = yaml.safe_load(_RESOURCE.read_text(encoding="utf-8")) or {}
    return raw if isinstance(raw, dict) else {}


_RAW = _load_yaml()
_SETTINGS = _RAW.get("settings", {}) if isinstance(_RAW.get("settings", {}), dict) else {}
ALIASES = {
    str(k).strip(): str(v).strip()
    for k, v in (_SETTINGS.get("aliases", {}) or {}).items()
    if str(k).strip() and str(v).strip()
}
APP_TYPE_PRIORS = {
    str(k).strip(): float(v)
    for k, v in (_SETTINGS.get("app_type_priors", {}) or {}).items()
    if str(k).strip()
}
DEFAULT_APP_TYPE = str(_SETTINGS.get("default_app_type", "")).strip()


def _load_profiles(raw: dict[str, Any]) -> list[EnvProfile]:
    items = raw.get("profiles", []) if isinstance(raw, dict) else []
    profiles: list[EnvProfile] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        app_type = str(item.get("app_type", "")).strip()
        if not app_type:
            continue
        kws = [str(k).strip().lower() for k in (item.get("keywords", []) or []) if str(k).strip()]
        profiles.append(
            EnvProfile(
                app_type=app_type,
                keywords=kws,
                env__server_os=str(item.get("env__server_os", "")).strip(),
                env__server_soft=str(item.get("env__server_soft", "")).strip(),
                env__server_model=str(item.get("env__server_model", "")).strip(),
                env__server_config=str(item.get("env__server_config", "")).strip(),
                env__server_id=str(item.get("env__server_id", "")).strip(),
                env__client_os=str(item.get("env__client_os", "")).strip(),
                env__client_soft=str(item.get("env__client_soft", "")).strip(),
                env__client_model=str(item.get("env__client_model", "")).strip(),
                env__client_config=str(item.get("env__client_config", "")).strip(),
                env__client_id=str(item.get("env__client_id", "")).strip(),
            )
        )
    return profiles


PROFILES = _load_profiles(_RAW)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def normalize_app_type(app_type: str) -> str:
    raw = (app_type or "").strip()
    return ALIASES.get(raw, raw)


def allowed_app_types() -> list[str]:
    return [p.app_type for p in PROFILES]


def get_default_profile() -> EnvProfile | None:
    if not PROFILES:
        return None
    wanted = normalize_app_type(DEFAULT_APP_TYPE).lower()
    if wanted:
        for p in PROFILES:
            if p.app_type.lower() == wanted:
                return p
    return PROFILES[0]


def select_profile(source_text: str, explicit_app_type: str = "") -> tuple[EnvProfile | None, dict[str, float]]:
    if not PROFILES:
        return None, {}

    explicit = normalize_app_type(explicit_app_type).lower()
    if explicit:
        for p in PROFILES:
            if p.app_type.lower() == explicit:
                return p, {p.app_type: 100.0}

    text = _normalize(source_text)
    scores: dict[str, float] = {}
    for p in PROFILES:
        score = 0.0
        for kw in p.keywords:
            if kw and kw in text:
                score += 1.0
        score += float(APP_TYPE_PRIORS.get(p.app_type, 0.0))
        scores[p.app_type] = score

    best = max(PROFILES, key=lambda p: scores.get(p.app_type, 0.0))
    return best, scores
