from __future__ import annotations

import argparse
import json
from pathlib import Path


TEMPLATE = {
    "output_dir": "C:\\软著申请\\深圳市氢创时代科技有限公司项目\\氢能多式联运系统",
    "app_name": "氢能多式联运系统",
    "app_version": "V1.0",
    "assess_dev_date": "2025-09-08",
    "assess_completion_date": "2026-02-08",
    "assess_workload": "3人*3月",
    "spec_path": "C:\\软著申请\\深圳市氢创时代科技有限公司项目\\氢能多式联运系统\\氢能多式联运系统说明书.md"
}


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("init", help="Write minimal input JSON")
    parser.add_argument("--path", default="input_assessment.json")
    parser.set_defaults(func=handle)


def handle(args: argparse.Namespace) -> int:
    p = Path(args.path).expanduser().resolve()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(TEMPLATE, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0
