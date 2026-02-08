from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from .config import AppConfig, load_config
from .models import AssessmentInputSchema
from .renderer import generate_excel
from ..infra.ai_agent import extract_output_with_agent
from ..infra.fs import read_text_content
from ..infra.path_utils import normalize_path
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
    model = AssessmentInputSchema.model_validate(payload)

    source_text = (model.source_text or "").strip()
    if not source_text and model.spec_path:
        logger.info("Reading source text from spec_path: %s", model.spec_path)
        source_text = read_text_content(normalize_path(model.spec_path))
    if not source_text:
        logger.error("Empty source text, cannot run retrieval + LLM extraction")
        return 2

    guessed_name = ""
    guessed_version = "V1.0"
    if model.spec_path:
        guessed_name, guessed_version = _guess_app_name_and_version(model.spec_path)

    raw_data = dict(model.data or {})
    app_name = (model.app_name or raw_data.get("app__name") or guessed_name or "软件系统").strip()
    app_version = (model.app_version or raw_data.get("app__version") or guessed_version or "V1.0").strip()
    seed_data = dict(raw_data)
    seed_data.setdefault("app__name", app_name)
    seed_data.setdefault("app__version", app_version)
    seed_data["assess__workload"] = str((model.assess_workload or "").strip())
    seed_data["assess__dev_date"] = str((model.assess_dev_date or "").strip())
    seed_data["assess__completion_date"] = str((model.assess_completion_date or "").strip())

    debug_dir = None
    if bool(getattr(args, "debug", False)):
        debug_dir = cfg.config_path.parent / "debug"
        debug_dir.mkdir(parents=True, exist_ok=True)

    logger.info("LLM pipeline start: retrieval + pool scoring + structured generation")
    try:
        output_model = extract_output_with_agent(
            cfg.llm,
            source_text=source_text,
            seed_data=seed_data,
            debug_dir=debug_dir,
            base_name=Path(args.input_json).stem,
        )
    except Exception as exc:
        logger.error("LLM extraction failed: %s", exc)
        return 2

    template = cfg.templates.assessment
    if not template:
        logger.error("Missing assessment template path")
        return 2

    out_dir = normalize_path(model.resolved_output_dir())
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / build_filename("产品评估申请", app_name, app_version, suffix=".xlsx")

    logger.info("Rendering assessment excel")
    generate_excel(template, out_path, output_model.model_dump())
    logger.info("[output] generated_file=%s", out_path)
    logger.info("[output] output_dir=%s", out_dir)
    return 0
