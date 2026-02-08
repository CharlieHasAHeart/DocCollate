#!/usr/bin/env bash
set -euo pipefail

python3 -m compileall src/doccollate_copyright src/main.py src/scripts/test_llm_connect.py
