"""JSON-formatted logging for the pipeline package.

Every module in src/pipeline/ shares one logger:
    from .logging_config import get_logger
    log = get_logger()
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path


class JsonFormatter(logging.Formatter):
    """Emit one JSON record per log line — machine-readable and grep-friendly."""

    def format(self, record: logging.LogRecord) -> str:
        return json.dumps({
            "ts":     round(time.time(), 3),
            "level":  record.levelname,
            "msg":    record.getMessage(),
            "logger": record.name,
        })


def get_logger(
    name: str = "pipeline",
    log_path: str | Path = "logs/pipeline.log",
) -> logging.Logger:
    """Return a logger that writes JSON lines to ``log_path``.

    Safe to call many times: handlers are attached only once.
    """
    log = logging.getLogger(name)
    log.setLevel(logging.INFO)

    if log.handlers:                      # already configured — don't double-attach
        return log

    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(log_path)
    handler.setFormatter(JsonFormatter())
    log.addHandler(handler)
    return log
