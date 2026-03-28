"""Configuration loading from YAML files."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from loguru import logger


@dataclass
class DevConfig:
    enabled: bool = True
    vite_port: int = 5173
    debug: bool = True


@dataclass
class LoggingConfig:
    level: str = "INFO"
    console: bool = True
    to_frontend: bool = True
    file: str = ""
    max_lines: int = 1000


@dataclass
class ProcessConfig:
    default_timeout: int = 300


@dataclass
class AppConfig:
    name: str = "my_app"
    title: str = "My App"
    width: int = 900
    height: int = 650
    min_size: tuple[int, int] = (600, 400)
    max_size: tuple[int, int] = (1920, 1080)
    resizable: bool = True
    icon: str = "assets/icon.ico"
    singleton: bool = False
    centered: bool = True
    theme: str = "light"
    dev: DevConfig = field(default_factory=DevConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    process: ProcessConfig = field(default_factory=ProcessConfig)
    business: dict[str, Any] = field(default_factory=dict)


def _parse_dev(raw: dict[str, Any] | None) -> DevConfig:
    if not raw:
        return DevConfig()
    return DevConfig(
        enabled=raw.get("enabled", True),
        vite_port=int(raw.get("vite_port", 5173)),
        debug=raw.get("debug", True),
    )


def _parse_logging(raw: dict[str, Any] | None) -> LoggingConfig:
    if not raw:
        return LoggingConfig()
    return LoggingConfig(
        level=raw.get("level", "INFO").upper(),
        console=raw.get("console", True),
        to_frontend=raw.get("to_frontend", True),
        file=raw.get("file", ""),
        max_lines=int(raw.get("max_lines", 1000)),
    )


def _parse_process(raw: dict[str, Any] | None) -> ProcessConfig:
    if not raw:
        return ProcessConfig()
    return ProcessConfig(
        default_timeout=int(raw.get("default_timeout", 300)),
    )


def _parse_tuple(value: Any) -> tuple[int, int]:
    """Parse a YAML list like [600, 400] into a tuple."""
    if isinstance(value, (list, tuple)) and len(value) == 2:
        return (int(value[0]), int(value[1]))
    return (600, 400)


def load_config(path: str = "config.yaml") -> AppConfig:
    """Load configuration from a YAML file.

    If the file does not exist, returns default configuration and logs a warning.
    """
    config_path = Path(path)

    if not config_path.exists():
        logger.warning(f"Config file not found: {config_path}, using defaults")
        return AppConfig()

    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if not isinstance(raw, dict):
        logger.warning(f"Invalid config file: {config_path}, using defaults")
        return AppConfig()

    app_raw = raw.get("app", {})
    return AppConfig(
        name=app_raw.get("name", "my_app"),
        title=app_raw.get("title", "My App"),
        width=int(app_raw.get("width", 900)),
        height=int(app_raw.get("height", 650)),
        min_size=_parse_tuple(app_raw.get("min_size")),
        max_size=_parse_tuple(app_raw.get("max_size")),
        resizable=app_raw.get("resizable", True),
        icon=app_raw.get("icon", "assets/icon.ico"),
        singleton=app_raw.get("singleton", False),
        centered=app_raw.get("centered", True),
        theme=app_raw.get("theme", "light"),
        dev=_parse_dev(app_raw.get("dev")),
        logging=_parse_logging(raw.get("logging")),
        process=_parse_process(raw.get("process")),
        business=raw.get("business", {}),
    )
