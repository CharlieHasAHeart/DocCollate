from __future__ import annotations

import argparse

from ..core.services import run_from_args


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("run", help="Generate test function form")
    parser.add_argument("--config", default="pyproject.toml", help="Config TOML path")
    parser.add_argument("--input-json", required=True, help="Input JSON path")
    parser.set_defaults(func=handle)


def handle(args: argparse.Namespace) -> int:
    return run_from_args(args)
