"""Business API base class - the primary interface for user code."""

from __future__ import annotations

import threading
from typing import Any

from loguru import logger

from .dialog import Dialog
from .event_bus import BRIDGE_JS, EventBus


class ApiBase:
    """Base class for all user-facing API classes.

    Subclass this and define public methods. All public methods (not prefixed
    with _) are automatically exposed to the frontend via pywebview's js_api.
    Methods must return a ``Result`` object.

    Example::

        class MyApi(ApiBase):
            def health_check(self) -> Result:
                return Result.ok(data={"version": "1.0"})

            def on_file_drop(self, file_paths: list[str]):
                for path in file_paths:
                    self.emit("file:processed", {"path": path})
    """

    def __init__(self) -> None:
        self._window: Any = None
        self._config: Any = None
        self._event_bus = EventBus()
        self._dialog = Dialog()
        self._class_name = self.__class__.__name__
        self._logger = logger.bind(class_name=self._class_name)

    # -- Properties exposed to user code -------------------------------------

    @property
    def window(self) -> Any:
        """The pywebview window instance (available after bind_window is called)."""
        return self._window

    @property
    def config(self) -> Any:
        """Application config (AppConfig dataclass, available after bind_config)."""
        return self._config

    @property
    def logger(self) -> Any:
        """A loguru logger bound with the class name."""
        return self._logger

    @property
    def dialog(self) -> Dialog:
        """Native system dialog wrapper."""
        return self._dialog

    # -- Framework lifecycle hooks (called by App) --------------------------

    def bind_window(self, window: Any) -> None:
        """Called by the framework to bind the pywebview window.

        Injects the JS bridge code and connects the event bus.
        """
        self._window = window
        self._event_bus.bind(window)
        self._dialog.bind(window)
        try:
            window.evaluate_js(BRIDGE_JS)
        except Exception as e:
            self._logger.warning(f"Failed to inject bridge JS: {e}")

    def bind_config(self, config: Any) -> None:
        """Called by the framework to bind the application config."""
        self._config = config

    # -- Public utilities for user code -------------------------------------

    def emit(self, event_name: str, data: Any = None) -> None:
        """Push an event to the frontend.

        Args:
            event_name: Event name in 'module:action' format (e.g. 'log:add').
            data: JSON-serializable payload.
        """
        self._event_bus.emit(event_name, data)

    def run_in_thread(self, func: Any, *args: Any, **kwargs: Any) -> threading.Thread:
        """Run a function in a background daemon thread.

        Returns:
            The started Thread instance.
        """
        t = threading.Thread(target=func, args=args, kwargs=kwargs, daemon=True)
        t.start()
        return t

    def on_file_drop(self, file_paths: list[str]) -> None:
        """Called when files are dropped onto the window. Override as needed."""
        self._logger.info(f"Files dropped: {file_paths}")
