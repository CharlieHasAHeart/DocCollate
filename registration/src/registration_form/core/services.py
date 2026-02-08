from __future__ import annotations

import json
import logging
from pathlib import Path

from .config import AppConfig, load_config
from .models import RegistrationInputSchema, RegistrationOutputSchema
from .renderer import generate_document
from ..infra.fs import detect_dev_lang, detect_platform, load_yaml_config, read_text_content
from ..infra.path_utils import normalize_path
from ..infra.platform_pool import select_platform_profile_by_domain
from ..infra.registration_llm import infer_registration_fields_with_llm
from ..utils.format import build_filename

logger = logging.getLogger(__name__)


def _pick_company_profile(config: dict, company: str) -> dict:
    presets = config.get("presets", []) if isinstance(config.get("presets", []), list) else []
    if not presets:
        return {}
    target = (company or "").strip()
    if target:
        for item in presets:
            if isinstance(item, dict) and str(item.get("label", "")).strip() == target:
                return item
    return presets[0] if isinstance(presets[0], dict) else {}


def _load_payload(input_json: str) -> dict:
    p = normalize_path(input_json)
    return json.loads(p.read_text(encoding="utf-8"))


def run_from_args(args) -> int:
    logger.info("Loading config: %s", args.config)
    cfg: AppConfig = load_config(args.config)

    payload = _load_payload(args.input_json)
    model = RegistrationInputSchema.model_validate(payload)

    raw_data = dict(model.data or {})
    app_name = (model.app_name or raw_data.get("app__name") or "").strip()
    app_version = (model.app_version or raw_data.get("app__version") or "V1.0").strip()
    app_short_name = ""

    source_text = (model.source_text or "").strip()
    if not source_text and model.spec_path:
        source_text = read_text_content(normalize_path(model.spec_path))

    try:
        llm_result = infer_registration_fields_with_llm(cfg.llm, source_text)
    except Exception as exc:
        logger.error("Registration LLM inference failed: %s", exc)
        return 2

    selected_domain = str(llm_result.get("product__app_domain", "")).strip()
    profile, scores = select_platform_profile_by_domain(source_text, explicit_domain=selected_domain)
    if profile:
        logger.info("Selected profile by domain: domain=%s app_type=%s", selected_domain, profile.app_type)
        logger.info("Profile scores: %s", scores)

    env_dev_lang = (
        str(raw_data.get("env__dev_lang") or "").strip()
        or str(llm_result.get("env__dev_lang", "")).strip()
        or detect_dev_lang(source_text)
    )
    env_dev_platform = (
        str(raw_data.get("env__dev_platform") or "").strip()
        or (profile.env__dev_platform if profile else "")
        or detect_platform(source_text)
    )
    env_run_platform = (
        str(raw_data.get("env__run_platform") or "").strip()
        or (profile.env__run_platform if profile else "")
        or detect_platform(source_text)
    )
    product_app_domain = (
        str(raw_data.get("product__app_domain") or "").strip()
        or selected_domain
        or "企业管理"
    )

    contact_config = load_yaml_config(normalize_path(model.contact_info) if model.contact_info else cfg.doccollate.contact_info)
    company_profile = _pick_company_profile(contact_config, model.company or "")
    contact_info = company_profile.get("contact_info", {}) if isinstance(company_profile, dict) else {}
    holder_name = (
        str(contact_info.get("owner", "")).strip()
        or str(company_profile.get("label", "")).strip()
        or str(model.company or "").strip()
    )
    holder_address = str(contact_info.get("address", "")).strip()
    holder_zip = str(contact_info.get("zip_code", "")).strip()

    output_model = RegistrationOutputSchema.model_validate(
        {
            "app__name": app_name,
            "app__short_name": app_short_name,
            "app__version": app_version,
            "env__dev_lang": env_dev_lang,
            "env__dev_platform": env_dev_platform,
            "env__run_platform": env_run_platform,
            "product__app_domain": product_app_domain,
            "holder__name": holder_name,
            "holder__address": holder_address,
            "holder__zip_code": holder_zip,
            "holder__contact_name": str(contact_info.get("contact_name", "")),
            "holder__contact_mobile": str(contact_info.get("contact_mobile", "")),
            "holder__contact_email": str(contact_info.get("contact_email", "")),
            "holder__contact_landline": str(contact_info.get("contact_landline", "")),
            "holder__tech_contact_name": str(contact_info.get("tech_contact_name", "")),
            "holder__tech_contact_mobile": str(contact_info.get("tech_contact_mobile", "")),
        }
    )

    template = cfg.templates.registration
    if not template:
        logger.error("Missing registration template path")
        return 2

    out_dir = normalize_path(model.resolved_output_dir())
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / build_filename("产品测试登记表", output_model.app__name, output_model.app__version)

    logger.info("Rendering registration form")
    generate_document(template, out_path, output_model.model_dump())
    logger.info("[output] generated_file=%s", out_path)
    logger.info("[output] output_dir=%s", out_dir)
    return 0
