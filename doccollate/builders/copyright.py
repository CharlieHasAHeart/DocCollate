from __future__ import annotations

import logging
from pathlib import Path

from ..config import AppConfig, TemplateConfig
from ..core.form_context import FormContext, collect_form_context
from ..core.form_pipeline import apply_app_metadata, build_form_data
from ..core.field_requirements import required_fields_for_target
from ..render.fill_form import generate_document
from ..io.io_utils import build_copyright_filename, read_file_content

logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(levelname)s - %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)

TARGET_COPYRIGHT = {
    "copyright": "Software copyright application form",
}


def ensure_local_run() -> bool:
    return True


def resolve_template_path(template_config: TemplateConfig, key: str) -> Path | None:
    path = template_config.copyright if key == "copyright" else None
    if not path:
        print(f"[Error] Missing template path for {key} in pyproject.toml")
        return None
    return path



def generate_copyright(args: argparse.Namespace, app_config: AppConfig, runtime, context: FormContext | None = None) -> int:
    if not ensure_local_run():
        return 2

    template_path = resolve_template_path(app_config.templates, "copyright")
    if not template_path:
        return 2

    try:
        form_context = context or collect_form_context(args, app_config)
    except ValueError as exc:
        print(f"[Error] {exc}")
        return 2

    total = len(form_context.files)
    for idx, file_path in enumerate(form_context.files, start=1):
        print(f"[Info] Processing ({idx}/{total}): {file_path.name}")
        text = read_file_content(file_path)
        if not text:
            continue

        base_name = file_path.stem

        required_fields = required_fields_for_target("copyright")
        data = build_form_data(text, runtime, dates_config=app_config.dates, required_fields=required_fields)
        apply_app_metadata(data, form_context.applicant_type, form_context.app_name, form_context.app_version)

        software_name = data.get("app__name") or base_name
        version = data.get("app__version") or "未标注版本"
        if not data.get("app__name"):
            data["app__name"] = software_name
        if not data.get("app__version"):
            data["app__version"] = version
        if not data.get("app__short_name"):
            data["app__short_name"] = software_name

        output_path = form_context.output_dir / build_copyright_filename(software_name, version)
        generate_document(form_context.company_profile, data, template_path, output_path, dates_config=app_config.dates)

    print(f"[Info] Outputs saved to: {form_context.output_dir}")
    return 0
