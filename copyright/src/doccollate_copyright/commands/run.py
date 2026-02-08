from __future__ import annotations

import argparse

from ..core.services import run_from_args


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("run", help="Generate copyright application docx")
    parser.add_argument("--config", default="pyproject.toml", help="Config TOML path")
    parser.add_argument("--input-json", default="", help="JSON file as input values")
    parser.add_argument("--spec", default="", help="Spec path (.md/.docx/.pdf)")
    parser.add_argument("--out", default="", help="Output directory path")
    parser.add_argument("--app-name", default="", help="Software name override")
    parser.add_argument("--app-version", default="", help="Software version override")
    parser.add_argument("--company-label", default="", help="Preset label in soft_copyright.yaml")
    parser.add_argument("--contact-info", default="", help="Path to soft_copyright.yaml")
    parser.add_argument("--debug", action="store_true", help="Write debug output to debug/")
    parser.set_defaults(func=handle)


def handle(args: argparse.Namespace) -> int:
    return run_from_args(args)
