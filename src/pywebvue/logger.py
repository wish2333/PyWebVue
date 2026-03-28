"""Loguru-based dual-channel logging system."""

from __future__ import annotations

import sys
from typing import Any, Callable

from loguru import logger

from .config import LoggingConfig


# Module-level reference to the current emit callback.
# Updated later by App when the window is ready.
_emit_callback: Callable[[str, Any], None] | None = None


def _frontend_sink(message: str) -> None:
    """Custom loguru sink that pushes log entries to the frontend via emit_callback."""
    if _emit_callback is None:
        return
    try:
        record = message.record
        payload = {
            "level": record["level"].name,
            "message": record["message"],
            "time": record["time"].strftime("%H:%M:%S"),
        }
        _emit_callback("log:add", payload)
    except Exception:
        # Never let the frontend sink crash the app
        pass


def setup_logger(config: LoggingConfig, emit_callback: Callable[[str, Any], None] | None = None) -> None:
    """Configure loguru with console, frontend, and optional file sinks.

    Args:
        config: Logging configuration from config.yaml.
        emit_callback: Function to call for frontend log delivery.
                        Updated later via update_emit_callback().
    """
    global _emit_callback
    _emit_callback = emit_callback

    logger.remove()

    if config.console:
        logger.add(
            sys.stderr,
            level=config.level,
            format=(
                "<green>{time:HH:mm:ss}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan> - "
                "<level>{message}</level>"
            ),
            colorize=True,
        )

    if config.to_frontend:
        logger.add(
            _frontend_sink,
            level=config.level,
            format="{message}",
        )

    if config.file:
        logger.add(
            config.file,
            level=config.level,
            rotation="10 MB",
            retention="7 days",
            encoding="utf-8",
        )


def update_emit_callback(callback: Callable[[str, Any], None] | None) -> None:
    """Update the frontend emit callback after the window is ready."""
    global _emit_callback
    _emit_callback = callback
