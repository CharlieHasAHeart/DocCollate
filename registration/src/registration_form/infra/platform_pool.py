from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

_RESOURCE = Path(__file__).resolve().parents[1] / "resources" / "env_platform_pools.yaml"


@dataclass(frozen=True)
class PlatformProfile:
    app_type: str
    keywords: list[str]
    env__dev_platform: str
    env__run_platform: str
    product__app_domain: str


def _load_profiles() -> list[PlatformProfile]:
    raw = yaml.safe_load(_RESOURCE.read_text(encoding="utf-8")) or {}
    items = raw.get("profiles", []) if isinstance(raw, dict) else []
    profiles: list[PlatformProfile] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        app_type = str(item.get("app_type", "")).strip()
        if not app_type:
            continue
        kws = [str(k).strip().lower() for k in (item.get("keywords", []) or []) if str(k).strip()]
        profiles.append(
            PlatformProfile(
                app_type=app_type,
                keywords=kws,
                env__dev_platform=str(item.get("env__dev_platform", "待补充")).strip() or "待补充",
                env__run_platform=str(item.get("env__run_platform", "待补充")).strip() or "待补充",
                product__app_domain=str(item.get("product__app_domain", "信息管理软件")).strip() or "信息管理软件",
            )
        )
    return profiles


PROFILES = _load_profiles()


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def allowed_app_types() -> list[str]:
    return [p.app_type for p in PROFILES]


def normalize_app_type(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    raw_lc = raw.lower()
    for app_type in allowed_app_types():
        if app_type.lower() == raw_lc:
            return app_type
    return raw


def select_platform_profile(source_text: str, explicit_app_type: str = "") -> tuple[PlatformProfile | None, dict[str, float]]:
    if not PROFILES:
        return None, {}

    explicit = (explicit_app_type or "").strip().lower()
    if explicit:
        for p in PROFILES:
            if p.app_type.lower() == explicit:
                return p, {p.app_type: 100.0}

    text = _normalize(source_text)
    scores: dict[str, float] = {}
    for p in PROFILES:
        score = 0.0
        for kw in p.keywords:
            if not kw:
                continue
            if kw in text:
                score += 1.0
        # Mild prior to prefer common enterprise web style when no signal.
        if p.app_type == "B/S业务系统":
            score += 0.2
        scores[p.app_type] = score

    best = max(PROFILES, key=lambda p: scores.get(p.app_type, 0.0))
    return best, scores
