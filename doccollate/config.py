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
class LLMConfig:
    api_key: str
    base_url: str
    model: str


@dataclass(frozen=True)
class TemplateConfig:
    proposal: Path | None
    func: Path | None
    reg: Path | None
    assess: Path | None
    env: Path | None
    copyright: Path | None


@dataclass(frozen=True)
class ProposalConfig:
    topk_default: int


@dataclass(frozen=True)
class DatesConfig:
    assess_completion_days_ago: int
    assess_dev_months_ago: int


@dataclass(frozen=True)
class DocCollateConfig:
    contact_info: Path | None
    preset_choice: str


@dataclass(frozen=True)
class AppConfig:
    llm: LLMConfig
    templates: TemplateConfig
    proposal: ProposalConfig
    doccollate: DocCollateConfig
    dates: DatesConfig
    config_path: Path


def _resolve_path(value: str, base_dir: Path) -> Path | None:
    if not value:
        return None
    expanded = Path(os.path.expanduser(value))
    if expanded.is_absolute():
        return expanded
    return (base_dir / expanded).resolve()


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
        model=_read_env("DOCCOLLATE_LLM_MODEL") or str(llm.get("model", "gpt-4o-mini")).strip() or "gpt-4o-mini",
    )

    templates = data.get("templates", {})
    template_config = TemplateConfig(
        proposal=_resolve_path(
            _read_env("DOCCOLLATE_TEMPLATE_PROPOSAL") or str(templates.get("proposal", "")).strip(),
            base_dir,
        ),
        func=_resolve_path(
            _read_env("DOCCOLLATE_TEMPLATE_FUNC") or str(templates.get("func", "")).strip(),
            base_dir,
        ),
        reg=_resolve_path(
            _read_env("DOCCOLLATE_TEMPLATE_REG") or str(templates.get("reg", "")).strip(),
            base_dir,
        ),
        assess=_resolve_path(
            _read_env("DOCCOLLATE_TEMPLATE_ASSESS") or str(templates.get("assess", "")).strip(),
            base_dir,
        ),
        env=_resolve_path(
            _read_env("DOCCOLLATE_TEMPLATE_ENV") or str(templates.get("env", "")).strip(),
            base_dir,
        ),
        copyright=_resolve_path(
            _read_env("DOCCOLLATE_TEMPLATE_COPYRIGHT") or str(templates.get("copyright", "")).strip(),
            base_dir,
        ),
    )

    proposal = data.get("proposal", {})
    proposal_config = ProposalConfig(
        topk_default=int(proposal.get("topk_default", 8)),
    )

    dates = data.get("dates", {})
    dates_config = DatesConfig(
        assess_completion_days_ago=int(dates.get("assess_completion_days_ago", 14)),
        assess_dev_months_ago=int(dates.get("assess_dev_months_ago", 5)),
    )

    doccollate = data.get("doccollate", {})
    contact_info_raw = _read_env("DOCCOLLATE_CONTACT_INFO") or str(
        doccollate.get("contact_info", "~/.doccollate/soft_copyright.yaml")
    ).strip()
    doccollate_config = DocCollateConfig(
        contact_info=_resolve_path(contact_info_raw, base_dir),
        preset_choice=str(doccollate.get("preset_choice", "")).strip(),
    )

    return AppConfig(
        llm=llm_config,
        templates=template_config,
        proposal=proposal_config,
        doccollate=doccollate_config,
        dates=dates_config,
        config_path=config_path,
    )
