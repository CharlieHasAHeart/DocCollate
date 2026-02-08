from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from .config import AppConfig, load_config
from .models import EnvironmentInputSchema, EnvironmentOutputSchema
from .renderer import generate_document
from ..infra.app_type_llm import infer_app_type_via_llm
from ..infra.fs import read_text_content
from ..infra.path_utils import normalize_path
from ..infra.profile_pool import get_default_profile, select_profile
from ..utils.format import build_filename

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


def _load_payload(input_json: str) -> dict:
    p = normalize_path(input_json)
    return json.loads(p.read_text(encoding="utf-8"))


def run_from_args(args) -> int:
    logger.info("Loading config: %s", args.config)
    cfg: AppConfig = load_config(args.config)

    payload = _load_payload(args.input_json)
    model = EnvironmentInputSchema.model_validate(payload)

    raw_data = dict(model.data or {})

    source_text = (model.source_text or "").strip()
    if not source_text and model.spec_path:
        logger.info("Reading source text from spec_path: %s", model.spec_path)
        source_text = read_text_content(normalize_path(model.spec_path))

    guessed_name = ""
    guessed_version = "V1.0"
    if model.spec_path:
        guessed_name, guessed_version = _guess_app_name_and_version(model.spec_path)

    app_name = (model.app_name or raw_data.get("app__name") or guessed_name or "软件系统").strip()
    app_version = (model.app_version or raw_data.get("app__version") or guessed_version or "V1.0").strip()

    try:
        llm_app_type = str(infer_app_type_via_llm(cfg.llm, source_text)).strip()
    except Exception as exc:
        logger.error("LLM app_type inference failed: %s", exc)
        return 2
    selected_app_type = llm_app_type
    profile, scores = select_profile(source_text, explicit_app_type=selected_app_type)
    default_profile = get_default_profile()
    if profile:
        logger.info("Selected app_type by LLM: %s", llm_app_type)
        logger.info("Selected environment profile: app_type=%s", profile.app_type)
        logger.info("Profile scores: %s", scores)

    effective_profile = profile or default_profile

    def _pick_field(field_name: str) -> str:
        raw_value = str(raw_data.get(field_name, "")).strip()
        if raw_value:
            return raw_value
        if effective_profile:
            return str(getattr(effective_profile, field_name, "")).strip()
        return ""

    output_model = EnvironmentOutputSchema.model_validate(
        {
            "env__server_os": _pick_field("env__server_os"),
            "env__server_soft": _pick_field("env__server_soft"),
            "env__server_model": _pick_field("env__server_model"),
            "env__server_config": _pick_field("env__server_config"),
            "env__server_id": _pick_field("env__server_id"),
            "env__client_os": _pick_field("env__client_os"),
            "env__client_soft": _pick_field("env__client_soft"),
            "env__client_model": _pick_field("env__client_model"),
            "env__client_config": _pick_field("env__client_config"),
            "env__client_id": _pick_field("env__client_id"),
        }
    )

    template = cfg.templates.environment
    if not template:
        logger.error("Missing environment template path")
        return 2

    out_dir = normalize_path(model.resolved_output_dir())
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / build_filename("非嵌入式软件环境", app_name, app_version)

    logger.info("Rendering non-embedded environment form")
    generate_document(template, out_path, output_model.model_dump())
    logger.info("[output] generated_file=%s", out_path)
    logger.info("[output] output_dir=%s", out_dir)
    return 0
