from __future__ import annotations

from typing import Iterable

from .date_utils import format_date, parse_date


def print_select(title: str, options: Iterable[str]) -> None:
    print(f"[Select] {title}:")
    for idx, label in enumerate(options, start=1):
        print(f"  {idx}) {label}")


def prompt_choice(prompt: str, options: Iterable[str], default: str | None = None) -> str:
    options_list = list(options)
    options_set = set(options_list)
    while True:
        value = input(f"Enter choice [{default}]: ").strip() if default else input("Enter choice: ").strip()
        if not value and default:
            return default
        if value.isdigit():
            index = int(value)
            if 1 <= index <= len(options_list):
                return options_list[index - 1]
        if value in options_set:
            return value


def prompt_text(prompt: str, default: str | None = None) -> str:
    value = input(f"[Input] {prompt} [{default}]: ").strip() if default else input(f"[Input] {prompt}: ").strip()
    return value or (default or "")


def prompt_date(prompt: str) -> str:
    while True:
        value = prompt_text(f"{prompt} (YYYY/MM/DD)")
        parsed = parse_date(value)
        if parsed:
            return format_date(parsed)


def interactive_form_inputs(
    presets: list[dict],
    default_choice: str | None,
    prompt_applicant_type: bool = True,
) -> dict:
    preset_choice = None
    if presets:
        labels = [item.get("label", f"Preset {idx + 1}") for idx, item in enumerate(presets)]
        print_select("Contact preset", labels)
        selected = prompt_choice("Contact preset", [str(i) for i in range(1, len(labels) + 1)], default="1")
        preset_choice = labels[int(selected) - 1]
    elif default_choice:
        preset_choice = default_choice

    applicant_type = None
    if prompt_applicant_type:
        print_select("Applicant type", ["holder (personal)", "agent (proxy)"])
        applicant_type = prompt_choice("Applicant type", ["holder", "agent"], default="holder")

    inputs_raw = prompt_text("Input path(s), space-separated")
    output_dir = prompt_text("Output directory (relative to base)", default="")

    return {
        "inputs": inputs_raw.split() if inputs_raw else [],
        "output_dir": output_dir,
        "preset_choice": preset_choice,
        "applicant_type": applicant_type or "",
    }


def select_preset(config: dict, choice: str | None) -> dict:
    presets = config.get("presets", [])
    if not presets:
        return {}
    if choice:
        for item in presets:
            if item.get("label") == choice:
                return item
    default_label = config.get("preset_choice")
    if default_label:
        for item in presets:
            if item.get("label") == default_label:
                return item
    return presets[0]


def resolve_contact_info(config: dict, preset: dict) -> dict:
    if preset and preset.get("contact_info"):
        return preset["contact_info"]
    return config.get("contact_info", {})
