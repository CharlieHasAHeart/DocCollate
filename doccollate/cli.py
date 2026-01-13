from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .config import load_config
from .builders.copyright import TARGET_COPYRIGHT, generate_copyright
from .core.form_context import collect_form_context
from .core.input_flow import print_select, prompt_choice, prompt_text
from .llm.client import init_llm
from .builders.proposal import add_proposal_args, generate_proposal
from .builders.test_forms import TARGET_TEST_FORMS, generate_test_forms

DOCCOLLATE_TARGETS = {**TARGET_TEST_FORMS, **TARGET_COPYRIGHT}
TARGETS = ["proposal", *DOCCOLLATE_TARGETS.keys(), "all"]


def _prompt_target() -> str:
    labels = ["proposal (Project proposal)"]
    for key in DOCCOLLATE_TARGETS.keys():
        labels.append(f"{key} ({DOCCOLLATE_TARGETS[key]})")
    labels.append("all (Generate all)")
    print_select("Output", labels)
    selection = prompt_choice("Output", [str(i) for i in range(1, len(labels) + 1)], default="1")
    try:
        index = int(selection)
    except ValueError:
        return "proposal"
    if index == 1:
        return "proposal"
    keys = list(DOCCOLLATE_TARGETS.keys())
    if 0 <= index - 2 < len(keys):
        return keys[index - 2]
    if index == len(DOCCOLLATE_TARGETS) + 2:
        return "all"
    return "proposal"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="doccollate")
    parser.add_argument("--config", default="pyproject.toml", help="Config TOML path")
    parser.add_argument("--target", choices=TARGETS, help="Output to generate")
    parser.add_argument("--api-key", default="", help="LLM API key (overrides config)")
    parser.add_argument("--base-url", default="", help="LLM base URL (overrides config)")
    parser.add_argument("--model", default="", help="LLM model (overrides config)")
    add_proposal_args(parser)
    _add_form_args(parser)
    return parser


def _add_form_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--input", "-i", nargs="*", help="Input MD file(s) or directories")
    parser.add_argument("--output-dir", "-o", default=None, help="Output directory")
    parser.add_argument("--contact-info", default="", help="Config file (yaml or json)")
    parser.add_argument("--preset-choice", default="", help="Preset label to use")
    parser.add_argument("--applicant-type", default="", help="Applicant type: holder or agent")
    parser.add_argument("--app-name", default="", help="Software name (manual input)")
    parser.add_argument("--app-version", default="", help="Software version (manual input)")


def _ensure_shared_inputs(args) -> None:
    if not args.out:
        args.out = prompt_text("Output directory", default=str(Path.cwd()))
    if not args.spec:
        args.spec = prompt_text("Spec file path")


def _ensure_app_metadata(args) -> None:
    if not args.app_name:
        args.app_name = prompt_text("Software name")
    if not args.app_version:
        args.app_version = prompt_text("Software version")


def main(argv: list[str] | None = None) -> int:
    logging.getLogger("jieba").setLevel(logging.WARNING)
    parser = _build_parser()
    args = parser.parse_args(argv or sys.argv[1:])
    target = args.target or _prompt_target()
    _ensure_shared_inputs(args)
    _ensure_app_metadata(args)

    app_config = load_config(args.config)
    runtime = init_llm(
        app_config.llm,
        api_key=args.api_key or None,
        base_url=args.base_url or None,
        model=args.model or None,
    )

    output_dir = Path(args.out).expanduser()

    if target == "proposal":
        return generate_proposal(args, app_config, runtime)
    if target == "test_forms":
        form_context = collect_form_context(
            args,
            app_config,
            output_dir_override=output_dir,
            prompt_applicant_type=False,
        )
        return generate_test_forms(args, app_config, runtime, context=form_context)
    if target == "copyright":
        form_context = collect_form_context(args, app_config, output_dir_override=output_dir)
        return generate_copyright(args, app_config, runtime, context=form_context)
    if target == "all":
        try:
            form_context = collect_form_context(
                args,
                app_config,
                output_dir_override=output_dir,
                prompt_applicant_type=True,
            )
        except ValueError as exc:
            print(f"[Error] {exc}")
            return 2
        company_name = ""
        if form_context.company_profile:
            company_name = str(
                form_context.company_profile.get("label")
                or form_context.contact_info.get("owner", "")
            ).strip()
        cover_overrides = {
            "company_name": company_name,
            "project_name": args.app_name or "",
        }
        proposal_status = generate_proposal(
            args,
            app_config,
            runtime,
            cover_overrides=cover_overrides,
        )
        test_status = generate_test_forms(args, app_config, runtime, context=form_context)
        copy_status = generate_copyright(args, app_config, runtime, context=form_context)
        return max(proposal_status, test_status, copy_status)
    print(f"[Error] Unknown target: {target}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
