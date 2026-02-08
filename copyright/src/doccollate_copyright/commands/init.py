from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


_MINIMAL_INPUT = {
    "output_dir": "./out",
    "spec_path": "./spec.md",
    "app_name": "示例系统",
    "app_version": "V1.0",
    "completion_date": "2026/02/08"
}


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("init", help="Write a minimal JSON input template")
    parser.add_argument("--path", default="input_copyright.json", help="Output JSON path")
    parser.set_defaults(func=handle)


def handle(args: argparse.Namespace) -> int:
    out_path = Path(args.path).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(_MINIMAL_INPUT, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    logger.info("[init] wrote template=%s", out_path)
    return 0
