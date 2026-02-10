from __future__ import annotations

import logging
import os


def setup_logging(debug: bool = False) -> None:
    level_name = "DEBUG" if debug else (os.getenv("DOCCOLLATE_LOG_LEVEL", "INFO").strip().upper() or "INFO")
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(level=level, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    logging.getLogger().setLevel(level)
