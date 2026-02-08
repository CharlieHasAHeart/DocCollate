from __future__ import annotations

import argparse
import sys

from .utils.logging import setup_logging


def _build_parser() -> argparse.ArgumentParser:
    from .commands import init as init_cmd
    from .commands import run as run_cmd

    parser = argparse.ArgumentParser(prog="registration-form")
    subparsers = parser.add_subparsers(dest="command")
    run_cmd.register(subparsers)
    init_cmd.register(subparsers)
    return parser


def main(argv: list[str] | None = None) -> int:
    setup_logging()
    args_list = list(argv or sys.argv[1:])
    if args_list and args_list[0].startswith("-") and args_list[0] not in {"-h", "--help"}:
        args_list = ["run", *args_list]

    parser = _build_parser()
    args = parser.parse_args(args_list)
    if not hasattr(args, "func"):
        parser.print_help()
        return 2
    return int(args.func(args))
