from __future__ import annotations

import argparse
import json
import logging
from typing import Any

from proposal_app.core.input_flow import prompt_text
from proposal_app.proposal.inputs import prompt_schedule_dates

from .pipeline import run_pipeline


def _load_run_config(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("run-config JSON must be an object")
    return data


def _apply_overrides(args: Any, overrides: dict[str, Any]) -> Any:
    for key, value in overrides.items():
        if not isinstance(key, str):
            continue
        setattr(args, key, value)
    return args


def _extract_manual_inputs_from_run_config(cfg: dict[str, Any]) -> dict[str, Any] | None:
    manual_inputs = cfg.get("manual_inputs")
    if isinstance(manual_inputs, dict):
        return manual_inputs

    if not isinstance(cfg, dict):
        return None

    result: dict[str, Any] = {}

    start_date = str(cfg.get("start_date", "") or "").strip()
    end_date = str(cfg.get("end_date", "") or "").strip()
    if start_date:
        result["start_date"] = start_date
    if end_date:
        result["end_date"] = end_date

    positioning = str(cfg.get("positioning", "") or "").strip()
    if positioning:
        result["positioning"] = positioning

    return result or None


def _extract_run_config_overrides(cfg: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(cfg, dict):
        return {}
    # Keep run-config focused on project/doc fields; program config stays in .env or CLI flags.
    allowed = {
        "spec",
        "out",
        "company_name",
        "project_name",
        "positioning",
        "start_date",
        "end_date",
    }
    return {k: v for k, v in cfg.items() if k in allowed}


def _run(args: Any) -> int:
    result = run_pipeline(args)
    out_path = result.get("out_path", "")
    if out_path:
        logging.getLogger(__name__).info("[Output] Generated file: %s", out_path)
        return 0
    logging.getLogger(__name__).error("[Error] Missing output path")
    return 2


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(prog="proposal-cli")
    parser.add_argument("--version", action="store_true", help="Show version")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run the proposal pipeline")
    run_parser.add_argument("--run-config", required=True, help="Run config JSON path")

    args = parser.parse_args()

    if args.version:
        logging.getLogger(__name__).info("proposal-cli 0.1.0")
        return 0

    if args.command == "run":
        try:
            cfg = _load_run_config(args.run_config)
            manual_inputs = _extract_manual_inputs_from_run_config(cfg)
            if manual_inputs is not None:
                setattr(args, "manual_inputs", manual_inputs)
            args = _apply_overrides(args, _extract_run_config_overrides(cfg))
            if not getattr(args, "spec", ""):
                args.spec = prompt_text("Spec file path (.md/.docx/.pdf)").strip()
            if not getattr(args, "out", ""):
                args.out = prompt_text("Output directory path").strip()
            if not getattr(args, "project_name", ""):
                args.project_name = prompt_text("Project name").strip()
            if not getattr(args, "company_name", ""):
                args.company_name = prompt_text("Company name").strip()
            if not getattr(args, "start_date", "") or not getattr(args, "end_date", ""):
                start_date, end_date = prompt_schedule_dates()
                args.start_date = start_date
                args.end_date = end_date
            if not getattr(args, "spec", "") or not getattr(args, "out", ""):
                raise ValueError("Missing required args: spec/out (provide via run-config or prompt)")
            return _run(args)
        except Exception as exc:
            logging.getLogger(__name__).error("[Error] %s", exc)
            return 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
