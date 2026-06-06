"""Centralized logging for Project Sentinel evaluation pipeline."""

from __future__ import annotations

import logging
import sys
import time
from contextlib import contextmanager
from typing import Any, Generator

LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    if root.handlers:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(name)


@contextmanager
def timed_operation(
    logger: logging.Logger,
    label: str,
    *,
    project_id: str = "",
    model: str = "",
    extra: dict[str, Any] | None = None,
) -> Generator[dict[str, Any], None, None]:
    """Context manager that logs start/end and elapsed time for an operation."""
    ctx: dict[str, Any] = {"label": label, "project_id": project_id, "model": model}
    if extra:
        ctx.update(extra)
    prefix = f"[{project_id[:8]}]" if project_id else ""
    model_tag = f" model={model}" if model else ""
    logger.info("%s START %s%s", prefix, label, model_tag)
    start = time.perf_counter()
    try:
        yield ctx
        elapsed = time.perf_counter() - start
        ctx["elapsed_sec"] = round(elapsed, 2)
        logger.info(
            "%s DONE %s in %.2fs%s",
            prefix,
            label,
            elapsed,
            model_tag,
        )
    except Exception as exc:
        elapsed = time.perf_counter() - start
        ctx["elapsed_sec"] = round(elapsed, 2)
        ctx["error"] = str(exc)
        logger.exception(
            "%s FAIL %s after %.2fs — %s",
            prefix,
            label,
            elapsed,
            exc,
        )
        raise
