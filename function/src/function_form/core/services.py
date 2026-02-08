from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from .config import AppConfig, load_config
from .models import (
    FunctionInputSchema,
    FunctionItem,
    FunctionModule,
    FunctionOutputSchema,
    LLMFunctionSchema,
)
from .renderer import generate_document
from ..infra.function_llm import infer_functions_with_llm
from ..infra.fs import read_text_content
from ..infra.path_utils import normalize_path
from ..infra.retrieval import chunk_text, retrieve_function_chunks
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


def _coerce_items(raw_items: object) -> list[FunctionItem]:
    if not isinstance(raw_items, list):
        return []
    out: list[FunctionItem] = []
    for item in raw_items:
        if isinstance(item, dict):
            name = str(item.get("name") or item.get("一级功能") or "").strip()
            desc = str(item.get("desc") or item.get("功能描述") or "").strip()
            if name and desc:
                out.append(FunctionItem(name=name, desc=desc))
        elif isinstance(item, str):
            name = item.strip()
            if name:
                out.append(FunctionItem(name=name, desc=f"可以进行{name}相关管理"))
    return out


def _coerce_modules(raw_modules: object) -> list[FunctionModule]:
    if not isinstance(raw_modules, list):
        return []
    modules: list[FunctionModule] = []
    for module in raw_modules:
        if not isinstance(module, dict):
            continue
        name = str(module.get("name") or module.get("一级功能") or "").strip()
        raw_items = module.get("items")
        items = _coerce_items(raw_items)
        if name and items:
            modules.append(FunctionModule(name=name, items=items))
    return modules


def _group_items_as_modules(items: list[FunctionItem]) -> list[FunctionModule]:
    grouped: dict[str, list[FunctionItem]] = {}
    for item in items:
        grouped.setdefault(item.name, []).append(item)
    return [FunctionModule(name=name, items=rows) for name, rows in grouped.items() if rows]


def _llm_to_modules(output: LLMFunctionSchema) -> list[FunctionModule]:
    modules: list[FunctionModule] = []
    for primary in output.primary_functions:
        sec_items: list[FunctionItem] = []
        if primary.secondary:
            for sec in primary.secondary:
                desc = sec.desc.strip()
                if not desc:
                    desc = f"可以进行{sec.name}管理"
                if not desc.startswith("可以"):
                    desc = f"可以{desc}"
                sec_items.append(
                    FunctionItem(
                        name=sec.name.strip(),
                        desc=desc,
                    )
                )
        else:
            sec_items.append(
                FunctionItem(
                    name="待补充",
                    desc=f"可以进行{primary.name.strip()}管理",
                )
            )
        modules.append(FunctionModule(name=primary.name.strip(), items=sec_items))
    return modules


def run_from_args(args) -> int:
    logger.info("Loading config: %s", args.config)
    cfg: AppConfig = load_config(args.config)

    payload = _load_payload(args.input_json)
    model = FunctionInputSchema.model_validate(payload)

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

    provided_modules = _coerce_modules(raw_data.get("module_list"))
    provided_items = _coerce_items(raw_data.get("product__func_list"))
    if provided_modules:
        modules = provided_modules
    elif provided_items:
        modules = _group_items_as_modules(provided_items)
    else:
        chunks = chunk_text(source_text)
        retrieved = retrieve_function_chunks(chunks, top_k=10)
        logger.info("Chunked spec into %s chunks; retrieved %s chunks for LLM", len(chunks), len(retrieved))
        try:
            llm_struct = infer_functions_with_llm(cfg.llm, retrieved)
        except Exception as exc:
            logger.error("LLM extraction failed: %s", exc)
            return 2
        modules = _llm_to_modules(llm_struct)
        rows = sum(len(m.items) for m in modules)
        logger.info("Using LLM extracted function hierarchy: modules=%s rows=%s", len(modules), rows)

    output_model = FunctionOutputSchema.model_validate(
        {
            "app__name": app_name,
            "app__version": app_version,
            "module_list": [m.model_dump() for m in modules],
        }
    )

    template = cfg.templates.function
    if not template:
        logger.error("Missing function template path")
        return 2

    out_dir = normalize_path(model.resolved_output_dir())
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / build_filename("产品测试功能表", output_model.app__name, output_model.app__version)

    logger.info("Rendering test function form")
    generate_document(
        template,
        out_path,
        [x.model_dump() for x in output_model.module_list],
    )
    logger.info("[output] generated_file=%s", out_path)
    logger.info("[output] output_dir=%s", out_dir)
    return 0
