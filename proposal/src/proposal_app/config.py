from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv(*args: object, **kwargs: object) -> None:
        return None

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib


@dataclass(frozen=True)
class LLMConfig:
    api_key: str
    base_url: str
    model: str
    skeleton_model: str
    final_model: str


@dataclass(frozen=True)
class TemplateConfig:
    proposal: Path | None


@dataclass(frozen=True)
class ProposalConfig:
    topk_default: int


@dataclass(frozen=True)
class ContactConfig:
    contact_info: Path | None
    preset_choice: str


@dataclass(frozen=True)
class AppConfig:
    llm: LLMConfig
    templates: TemplateConfig
    proposal: ProposalConfig
    contact: ContactConfig
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
    tool = raw.get("tool", {})
    data = tool.get("proposal", {})
    base_dir = config_path.parent

    llm = data.get("llm", {})
    model = _read_env("PROPOSAL_LLM_MODEL") or str(llm.get("model", "gpt-4o-mini")).strip() or "gpt-4o-mini"
    skeleton_model = _read_env("PROPOSAL_LLM_MODEL_SKELETON") or str(llm.get("skeleton_model", "")).strip()
    final_model = _read_env("PROPOSAL_LLM_MODEL_FINAL") or str(llm.get("final_model", "")).strip()
    llm_config = LLMConfig(
        api_key=_read_env("PROPOSAL_LLM_API_KEY") or str(llm.get("api_key", "")).strip(),
        base_url=_read_env("PROPOSAL_LLM_BASE_URL") or str(llm.get("base_url", "")).strip(),
        model=model,
        skeleton_model=skeleton_model or model,
        final_model=final_model or model,
    )

    templates = data.get("templates", {})
    template_config = TemplateConfig(
        proposal=_resolve_path(
            _read_env("PROPOSAL_TEMPLATE_PROPOSAL") or str(templates.get("proposal", "")).strip(),
            base_dir,
        ),
    )

    proposal = data.get("proposal", {})
    proposal_config = ProposalConfig(
        topk_default=int(proposal.get("topk_default", 8)),
    )

    contact_raw = _read_env("PROPOSAL_CONTACT_INFO") or str(
        data.get("contact_info", "~/.proposal/contact.yaml")
    ).strip()
    contact_config = ContactConfig(
        contact_info=_resolve_path(contact_raw, base_dir),
        preset_choice=str(data.get("preset_choice", "")).strip(),
    )

    return AppConfig(
        llm=llm_config,
        templates=template_config,
        proposal=proposal_config,
        contact=contact_config,
        config_path=config_path,
    )
