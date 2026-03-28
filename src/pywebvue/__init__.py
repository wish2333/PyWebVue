"""PyWebVue - Desktop rapid development framework for Python developers."""

from .constants import __version__
from .result import Result, ErrCode
from .config import AppConfig, load_config
from .logger import setup_logger, update_emit_callback
from .event_bus import EventBus, BRIDGE_JS
from .dialog import Dialog
from .singleton import SingletonLock
from .process import ProcessManager, ProcessState
from .api_base import ApiBase
from .app import App

__all__ = [
    "__version__",
    "App",
    "ApiBase",
    "Result",
    "ErrCode",
    "AppConfig",
    "load_config",
    "setup_logger",
    "update_emit_callback",
    "EventBus",
    "BRIDGE_JS",
    "Dialog",
    "SingletonLock",
    "ProcessManager",
    "ProcessState",
]
