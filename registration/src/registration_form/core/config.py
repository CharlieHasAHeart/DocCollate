from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib


@dataclass(frozen=True)
class TemplateConfig:
    registration: Path | None


@dataclass(frozen=True)
class LLMConfig:
    api_key: str
    base_url: str
    model: str
    timeout_seconds: int


@dataclass(frozen=True)
class DocCollateConfig:
    contact_info: Path | None


@dataclass(frozen=True)
class AppConfig:
    llm: LLMConfig
    templates: TemplateConfig
    doccollate: DocCollateConfig
    config_path: Path


def _resolve_path(value: str, base_dir: Path) -> Path | None:
    raw = (value or "").strip()
    if not raw:
        return None
    p = Path(os.path.expanduser(raw))
    if p.is_absolute():
        return p
    return (base_dir / p).resolve()


def _read_env(key: str) -> str:
    return os.getenv(key, "").strip()


def load_config(path: str) -> AppConfig:
    config_path = Path(path).expanduser().resolve()
    load_dotenv(config_path.parent / ".env")

    raw = tomllib.loads(config_path.read_text(encoding="utf-8"))
    data = raw.get("tool", {}).get("doccollate", {})
    base_dir = config_path.parent

    llm = data.get("llm", {})
    llm_config = LLMConfig(
        api_key=_read_env("DOCCOLLATE_LLM_API_KEY") or str(llm.get("api_key", "")).strip(),
        base_url=_read_env("DOCCOLLATE_LLM_BASE_URL") or str(llm.get("base_url", "")).strip(),
        model=(
            _read_env("DOCCOLLATE_LLM_MODEL")
            or str(llm.get("model", "qwen3-max")).strip()
            or "qwen3-max"
        ),
        timeout_seconds=int(
            _read_env("DOCCOLLATE_LLM_TIMEOUT")
            or str(llm.get("timeout_seconds", 25)).strip()
            or "25"
        ),
    )

    templates = data.get("templates", {})
    registration_template = _resolve_path(
        _read_env("DOCCOLLATE_TEMPLATE_REGISTRATION") or str(templates.get("registration", "")).strip(),
        base_dir,
    )

    cfg = data.get("doccollate", {})
    contact_info = _resolve_path(
        _read_env("DOCCOLLATE_CONTACT_INFO")
        or str(cfg.get("contact_info", "src/registration_form/resources/soft_copyright.yaml")).strip(),
        base_dir,
    )

    return AppConfig(
        llm=llm_config,
        templates=TemplateConfig(registration=registration_template),
        doccollate=DocCollateConfig(contact_info=contact_info),
        config_path=config_path,
    )
