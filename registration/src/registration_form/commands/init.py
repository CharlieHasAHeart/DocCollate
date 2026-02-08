from __future__ import annotations

import argparse
import json
from pathlib import Path


TEMPLATE = {
    "output_dir": "./out",
    "app_type": "B/S业务系统",
    "company": "深圳市氢创时代科技有限公司",
    "app_name": "示例系统",
    "app_version": "V1.0",
    "spec_path": "./spec.md"
}


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("init", help="Write minimal input JSON")
    parser.add_argument("--path", default="input_registration.json")
    parser.set_defaults(func=handle)


def handle(args: argparse.Namespace) -> int:
    p = Path(args.path).expanduser().resolve()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(TEMPLATE, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0
