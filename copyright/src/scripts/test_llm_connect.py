from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from doccollate_copyright.core.config import load_config
from doccollate_copyright.infra.http import init_llm


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="test-llm-connect")
    parser.add_argument("--config", default="pyproject.toml", help="Config TOML path")
    parser.add_argument("--timeout", type=float, default=20.0, help="Request timeout in seconds")
    parser.add_argument("--model", default="", help="Model override")
    parser.add_argument("--base-url", default="", help="Base URL override")
    parser.add_argument("--api-key", default="", help="API key override")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    config_path = Path(args.config).expanduser()

    try:
        app_config = load_config(str(config_path))
        runtime = init_llm(
            app_config.llm,
            api_key=args.api_key or None,
            base_url=args.base_url or None,
            model=args.model or None,
        )
    except Exception as exc:
        print(f"[FAIL] Config/init error: {exc}")
        return 2

    print(f"[Info] model={runtime.model}")
    print(f"[Info] base_url={runtime.client.base_url}")
    start = time.time()

    try:
        client = runtime.client.with_options(timeout=args.timeout)
        resp = client.chat.completions.create(
            model=runtime.model,
            messages=[
                {"role": "system", "content": "You are a connectivity test assistant."},
                {"role": "user", "content": "Reply with just: OK"},
            ],
            temperature=0,
            max_tokens=8,
        )
        elapsed = time.time() - start
        text = (resp.choices[0].message.content or "").strip()
        print(f"[PASS] connected in {elapsed:.2f}s")
        print(f"[PASS] response={text!r}")
        return 0
    except Exception as exc:
        elapsed = time.time() - start
        print(f"[FAIL] request error after {elapsed:.2f}s: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
