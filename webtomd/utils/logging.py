from __future__ import annotations

import logging
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler


def setup_logger(level: str = "INFO") -> logging.Logger:
    level_name = level.upper()
    numeric_level = getattr(logging, level_name, logging.INFO)
    console = Console(stderr=True, highlight=False)
    handler = RichHandler(console=console, show_time=False, show_path=False, rich_tracebacks=True)
    fmt = "%(message)s"
    logging.basicConfig(level=numeric_level, format=fmt, handlers=[handler])
    logger = logging.getLogger("webtomd")
    logger.setLevel(numeric_level)
    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    return logging.getLogger(name or "webtomd")

