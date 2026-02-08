from __future__ import annotations

import json
import logging
import random
import re
from time import perf_counter
from pathlib import Path

from pydantic import ValidationError

from ..infra.ai_agent import extract_output_with_agent
from ..infra.fs import load_yaml_config, normalize_path, normalize_path_string, read_file_content
from ..utils.format import build_copyright_filename
from .config import AppConfig, TemplateConfig, load_config
from .models import CompanyProfileSchema, CopyrightInputSchema, CopyrightOutputSchema
from .renderer import generate_document

logger = logging.getLogger(__name__)

VERSION_RE = re.compile(r"(?:^|[_\-\s])V(\d+(?:\.\d+)*)", re.IGNORECASE)


def _guess_app_name_and_version(spec_path: str) -> tuple[str, str]:
    stem = Path(spec_path).stem
    version = "V1.0"
    m = VERSION_RE.search(stem)
    if m:
        version = f"V{m.group(1)}"
    app_name = re.sub(r"[_\-\s]*V\d+(?:\.\d+)*", "", stem, flags=re.IGNORECASE).strip("_ -")
    app_name = app_name.replace("软件说明书", "").replace("说明书", "").strip("_ -") or stem
    return app_name, version


def _pick_company_profile(config_path: Path, company_label: str) -> dict:
    config = load_yaml_config(config_path)
    if not isinstance(config, dict):
        return {}
    presets = config.get("presets", []) if isinstance(config.get("presets", []), list) else []
    if not presets:
        return {}

    target = company_label.strip() if company_label else ""
    if not target:
        target = str(config.get("preset_choice") or "").strip()

    if target:
        for item in presets:
            if isinstance(item, dict) and str(item.get("label", "")).strip() == target:
                return item

    first = presets[0]
    return first if isinstance(first, dict) else {}


def _load_input_payload(path: str, app_config: AppConfig) -> dict:
    json_path = normalize_path(path)
    logger.info("Loading input JSON: %s", json_path)
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("input-json must be a JSON object")
    payload = _resolve_company_profile_in_payload(payload, app_config)
    return payload


def _resolve_company_profile_in_payload(payload: dict, app_config: AppConfig) -> dict:
    # If company_profile already provided in input JSON, keep it.
    existing = payload.get("company_profile")
    if isinstance(existing, dict) and existing:
        return payload

    company = str(payload.get("company", "")).strip()
    if not company:
        return payload

    contact_info_path = str(payload.get("contact_info", "")).strip()
    if not contact_info_path:
        contact_info_path = str(app_config.doccollate.contact_info or "")
    if not contact_info_path:
        logger.warning("company provided but contact_info path is empty; skip company profile loading")
        return payload

    profile = _pick_company_profile(normalize_path(contact_info_path), company)
    if not profile:
        logger.warning("company '%s' not found in %s", company, contact_info_path)
        return payload

    payload["company_profile"] = profile
    logger.info("Loaded company_profile from YAML: %s", company)
    return payload


def _build_payload_from_spec(args, app_config: AppConfig) -> dict:
    spec_path = normalize_path_string(args.spec)
    if not spec_path:
        raise ValueError("--spec is required when --input-json is not provided")

    spec = normalize_path(spec_path)
    if not spec.exists() or not spec.is_file():
        raise ValueError(f"spec not found: {spec}")
    logger.info("Using spec file: %s", spec)

    out = normalize_path_string(args.out) if args.out else str(spec.parent)
    app_name_guess, app_version_guess = _guess_app_name_and_version(str(spec))

    app_name = args.app_name.strip() if args.app_name else app_name_guess
    app_version = args.app_version.strip() if args.app_version else app_version_guess

    contact_info_path = (
        normalize_path_string(args.contact_info)
        if args.contact_info
        else str(app_config.doccollate.contact_info or "")
    )
    company_profile = {}
    if contact_info_path:
        company_profile = _pick_company_profile(normalize_path(contact_info_path), args.company_label)

    payload: dict = {
        "output_dir": out,
        "spec_path": str(spec),
        "app_name": app_name,
        "app_version": app_version,
        "company_profile": company_profile,
    }
    return payload


def _resolve_template_path(template_config: TemplateConfig) -> Path | None:
    path = template_config.copyright
    if not path:
        logger.error("Missing template path for copyright in pyproject.toml")
        return None
    logger.info("Using template: %s", path)
    return path


def _ensure_source_lines(data: dict[str, object]) -> dict[str, object]:
    value = str(data.get("tech__source_lines", "")).strip()
    if value:
        return data
    generated = str(random.randint(10000, 15000))
    data["tech__source_lines"] = generated
    logger.info("Auto-filled tech__source_lines=%s", generated)
    return data


def _build_output_model(
    input_model: CopyrightInputSchema,
    app_config: AppConfig,
    debug_dir: Path | None = None,
    base_name: str = "llm",
) -> CopyrightOutputSchema:
    raw_data: dict[str, object] = dict(input_model.data or {})

    source_text = (input_model.source_text or "").strip()
    if not source_text and input_model.spec_path:
        logger.info("Reading source text from spec_path: %s", input_model.spec_path)
        source_text = read_file_content(normalize_path(input_model.spec_path))

    if raw_data:
        logger.info("Using provided JSON data for output fields")
        if input_model.app_name:
            raw_data.setdefault("app__name", input_model.app_name)
            raw_data.setdefault("app__short_name", input_model.app_name)
        if input_model.app_version:
            raw_data.setdefault("app__version", input_model.app_version)
        if input_model.completion_date:
            raw_data["copyright__completion_date"] = input_model.completion_date
        raw_data = _ensure_source_lines(raw_data)
        return CopyrightOutputSchema.model_validate(raw_data)

    seed_data: dict[str, object] = {}
    if input_model.app_name:
        seed_data["app__name"] = input_model.app_name
        seed_data["app__short_name"] = input_model.app_name
    if input_model.app_version:
        seed_data["app__version"] = input_model.app_version
    if input_model.completion_date:
        seed_data["copyright__completion_date"] = input_model.completion_date

    logger.info("Invoking LLM extraction pipeline")
    llm_output = extract_output_with_agent(
        app_config.llm,
        source_text=source_text,
        seed_data=seed_data,
        debug_dir=debug_dir,
        base_name=base_name,
    )
    normalized = llm_output.model_dump(exclude_none=True)

    for key, value in seed_data.items():
        normalized.setdefault(key, value)

    fallback_name = (input_model.app_name or "").strip()
    if fallback_name and not normalized.get("app__name"):
        normalized["app__name"] = fallback_name
        normalized.setdefault("app__short_name", fallback_name)

    normalized = _ensure_source_lines(normalized)

    return CopyrightOutputSchema.model_validate(normalized)


def _generate_from_payload(args, app_config: AppConfig, payload: dict) -> int:
    t0 = perf_counter()
    logger.info("[stage] generation.start")
    template_path = _resolve_template_path(app_config.templates)
    if not template_path:
        return 2

    try:
        input_model = CopyrightInputSchema.model_validate(payload)
    except ValidationError as exc:
        logger.error("input-json schema validation failed:\n%s", exc)
        return 2
    logger.info("[stage] input.validated")

    base_name = Path(args.input_json).stem if getattr(args, "input_json", "") else "spec_input"
    debug_dir = (app_config.config_path.parent / "debug") if getattr(args, "debug", False) else None
    if debug_dir:
        logger.info("[stage] debug.enabled dir=%s", debug_dir)
        debug_dir.mkdir(parents=True, exist_ok=True)
        for old_file in debug_dir.glob("*"):
            if old_file.is_file():
                old_file.unlink()

    try:
        output_model = _build_output_model(
            input_model,
            app_config,
            debug_dir=debug_dir,
            base_name=base_name,
        )
    except ValidationError as exc:
        logger.error("output schema validation failed:\n%s", exc)
        return 2
    except Exception as exc:
        logger.error("LLM extraction failed: %s", exc)
        return 2
    logger.info("[stage] output.validated")

    data = output_model.model_dump(exclude_none=True)

    output_dir = normalize_path(input_model.resolved_output_dir())
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info("[stage] output.dir.ready path=%s", output_dir)

    if isinstance(input_model.company_profile, CompanyProfileSchema):
        company_profile = input_model.company_profile.model_dump(exclude_none=True)
    elif isinstance(input_model.company_profile, dict):
        company_profile = input_model.company_profile
    else:
        company_profile = {}

    software_name = data["app__name"]
    version = data.get("app__version", "未标注版本")
    output_path = output_dir / build_copyright_filename(str(software_name), str(version))

    logger.info("[stage] render.start")
    generate_document(company_profile, data, template_path, output_path)
    elapsed_ms = int((perf_counter() - t0) * 1000)
    logger.info("[output] generated_file=%s", output_path)
    logger.info("[output] output_dir=%s", output_dir)
    logger.info("[stage] generation.done elapsed_ms=%s", elapsed_ms)
    return 0


def run_from_args(args) -> int:
    logger.info("Loading config: %s", args.config)
    app_config = load_config(args.config)

    try:
        if args.input_json:
            payload = _load_input_payload(args.input_json, app_config)
        else:
            payload = _build_payload_from_spec(args, app_config)
    except Exception as exc:
        logger.error("Invalid input: %s", exc)
        return 2

    return _generate_from_payload(args, app_config, payload)
