from __future__ import annotations

from doccollate.cli import main as doccollate_main


def main(argv: list[str] | None = None) -> int:
    return doccollate_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
