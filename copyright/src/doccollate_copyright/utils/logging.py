from __future__ import annotations

import logging
import os
import warnings


def setup_logging() -> None:
    level_name = os.getenv("DOCCOLLATE_LOG_LEVEL", "INFO").strip().upper() or "INFO"
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    jieba_logger = logging.getLogger("jieba")
    jieba_logger.setLevel(logging.WARNING)
    jieba_logger.propagate = False

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)

    # Keep runtime logs focused on business flow instead of third-party warnings.
    try:
        import jieba

        jieba.setLogLevel(logging.WARNING)
    except Exception:
        pass

    warnings.filterwarnings("ignore", category=SyntaxWarning, module="jieba")
    warnings.filterwarnings(
        "ignore",
        message=r'Field name "copy" in "RightsPartialRightsSchema" shadows an attribute.*',
        category=UserWarning,
    )
