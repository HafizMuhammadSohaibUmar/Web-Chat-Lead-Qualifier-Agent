"""Logging helpers."""
import logging
import time
from typing import Any

from config import get_settings


def setup_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, get_settings().log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def log_event(logger: logging.Logger, message: str, **fields: Any) -> None:
    logger.info("%s %s", message, " ".join(f"{k}={v}" for k, v in fields.items()))


class Timer:
    def __enter__(self):
        self.started = time.perf_counter()
        return self

    def __exit__(self, *_):
        self.latency_ms = round((time.perf_counter() - self.started) * 1000, 2)
