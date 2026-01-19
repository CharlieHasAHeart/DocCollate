from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..config import AppConfig
from .input_flow import (
    interactive_form_inputs,
    print_select,
    prompt_choice,
    prompt_date,
    prompt_text,
    resolve_contact_info,
    select_preset,
)
from .date_utils import parse_date
from ..io.io_utils import collect_inputs, ensure_output_dir, load_yaml_config

CONFIG_DIR = Path.home() / ".doccollate"
DEFAULT_CONFIG_FILE = CONFIG_DIR / "soft_copyright.yaml"


@dataclass
class FormContext:
    files: list[Path]
    output_dir: Path
    contact_info: dict
    company_profile: dict
    app_name: str | None
    app_version: str | None
    applicant_type: str | None
    dev_date: str
    completion_date: str


def _resolve_output_dir(args, output_dir_override: Path | None) -> Path:
    if output_dir_override:
        output_dir = output_dir_override.expanduser()
        ensure_output_dir(output_dir)
        return output_dir

    default_output_base = str(Path.cwd())
    output_base_input = prompt_text("Output base directory", default=default_output_base)
    output_base_path = Path(output_base_input).expanduser()
    if not output_base_path.exists() or not output_base_path.is_dir():
        raise ValueError(f"Output base directory not found: {output_base_path}")

    output_dir = output_base_path / (args.output_dir or "")
    ensure_output_dir(output_dir)
    return output_dir


def collect_form_context(
    args,
    app_config: AppConfig,
    output_dir_override: Path | None = None,
    prompt_applicant_type: bool = True,
) -> FormContext:
    config_path = Path(args.contact_info) if args.contact_info else (app_config.doccollate.contact_info or DEFAULT_CONFIG_FILE)
    config = load_yaml_config(config_path)
    presets = config.get("presets", []) if isinstance(config, dict) else []
    default_choice = args.preset_choice or app_config.doccollate.preset_choice or (config.get("preset_choice") if isinstance(config, dict) else None)
    prompted_preset = False

    if not args.input:
        if getattr(args, "spec", ""):
            args.input = [args.spec]
        else:
            selection = interactive_form_inputs(presets, default_choice, prompt_applicant_type=prompt_applicant_type)
            args.input = selection["inputs"]
            args.output_dir = selection["output_dir"]
            args.preset_choice = selection["preset_choice"] or args.preset_choice
            if selection["applicant_type"]:
                args.applicant_type = selection["applicant_type"]
            prompted_preset = True

    if presets and not prompted_preset:
        labels = [item.get("label", f"Preset {idx + 1}") for idx, item in enumerate(presets)]
        print_select("Contact preset", labels)
        default_index = "1"
        if default_choice and default_choice in labels:
            default_index = str(labels.index(default_choice) + 1)
        selected = prompt_choice("Contact preset", [str(i) for i in range(1, len(labels) + 1)], default=default_index)
        args.preset_choice = labels[int(selected) - 1]

    if prompt_applicant_type and not args.applicant_type:
        print_select("Applicant type", ["holder (personal)", "agent (proxy)"])
        args.applicant_type = prompt_choice("Applicant type", ["holder", "agent"], default="holder")

    output_dir = _resolve_output_dir(args, output_dir_override)

    while True:
        dev_date = prompt_date("Development date")
        completion_date = prompt_date("Completion date")
        dev = parse_date(dev_date)
        completion = parse_date(completion_date)
        if dev and completion and completion >= dev:
            break
        print("[Error] Completion date must be the same as or after development date.")

    files = collect_inputs(args.input or [])
    if not files:
        raise ValueError("No input files found.")

    preset_choice = args.preset_choice or app_config.doccollate.preset_choice or None
    preset = select_preset(config if isinstance(config, dict) else {}, preset_choice)
    contact_info = resolve_contact_info(config if isinstance(config, dict) else {}, preset)
    company_profile = preset if preset else (config if isinstance(config, dict) else {})

    return FormContext(
        files=files,
        output_dir=output_dir,
        contact_info=contact_info,
        company_profile=company_profile,
        app_name=args.app_name or None,
        app_version=args.app_version or None,
        applicant_type=args.applicant_type or None,
        dev_date=dev_date,
        completion_date=completion_date,
    )
