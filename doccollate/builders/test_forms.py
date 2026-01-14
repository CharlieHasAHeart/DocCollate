from __future__ import annotations

import logging
from pathlib import Path

from ..config import AppConfig, TemplateConfig
from ..core.form_context import FormContext, collect_form_context
from ..core.form_pipeline import apply_app_metadata, build_form_data
from ..core.field_requirements import required_fields_for_target
from ..io.io_utils import build_filename, read_file_content
from ..render.renderers import (
    fill_assessment_excel,
    fill_env_table,
    fill_func_table,
    fill_reg_table,
)

logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(levelname)s - %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)

TARGET_TEST_FORMS = {
    "test_forms": "Product test forms (function/registration/environment/assessment)",
}


def ensure_local_run() -> bool:
    return True


def resolve_template_path(template_config: TemplateConfig, key: str) -> Path | None:
    mapping = {
        "func": template_config.func,
        "reg": template_config.reg,
        "assess": template_config.assess,
        "env": template_config.env,
    }
    path = mapping.get(key)
    if not path:
        print(f"[Error] Missing template path for {key} in pyproject.toml")
        return None
    return path


def _resolve_test_form_templates(template_config: TemplateConfig) -> dict[str, Path] | None:
    required = ["func", "reg", "env", "assess"]
    resolved: dict[str, Path] = {}
    missing: list[str] = []
    for key in required:
        path = resolve_template_path(template_config, key)
        if not path:
            missing.append(key)
        else:
            resolved[key] = path
    if missing:
        print(f"[Error] Missing template path(s) for test forms: {', '.join(missing)}")
        return None
    return resolved



def generate_test_forms(args: argparse.Namespace, app_config: AppConfig, runtime, context: FormContext | None = None) -> int:
    if not ensure_local_run():
        return 2

    test_templates = _resolve_test_form_templates(app_config.templates)
    if not test_templates:
        return 2

    try:
        form_context = context or collect_form_context(args, app_config, prompt_applicant_type=False)
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

        required_fields = required_fields_for_target("test_forms")
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

        output_path = form_context.output_dir / build_filename("产品测试功能表", software_name, version, ".docx")
        if not fill_func_table(test_templates["func"], output_path, data):
            print(f"[Warn] No function table generated for: {file_path}")
        else:
            print(f"[Output] Generated file: {output_path}")

        output_path = form_context.output_dir / build_filename("产品测试登记表", software_name, version, ".docx")
        if not fill_reg_table(test_templates["reg"], output_path, data, form_context.contact_info):
            print(f"[Warn] No registration form generated for: {file_path}")
        else:
            print(f"[Output] Generated file: {output_path}")

        output_path = form_context.output_dir / build_filename("非嵌入式软件环境", software_name, version, ".docx")
        if not fill_env_table(test_templates["env"], output_path, data):
            print(f"[Warn] No environment form generated for: {file_path}")
        else:
            print(f"[Output] Generated file: {output_path}")

        output_path = form_context.output_dir / build_filename("产品评估申请", software_name, version, ".xlsx")
        if not fill_assessment_excel(test_templates["assess"], output_path, data):
            print(f"[Warn] No assessment form generated for: {file_path}")
        else:
            print(f"[Output] Generated file: {output_path}")

    print(f"[Info] Outputs saved to: {form_context.output_dir}")
    return 0
