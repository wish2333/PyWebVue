"""Bridge base class and @expose decorator."""

from __future__ import annotations

import functools
import threading
from typing import Any, Callable


def expose(func: Callable[..., Any]) -> Callable[..., Any]:
    """Wrap a bridge method with try/except error handling.

    Exposed methods should return ``{"success": True, "data": ...}``.
    On unhandled exception, the decorator returns
    ``{"success": False, "error": "..."}`` instead of crashing.
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    return wrapper


class Bridge:
    """Base class for Python APIs exposed to the frontend.

    Subclass this and decorate public methods with ``@expose``.
    Use ``self._emit(event_name, data)`` to push events to the frontend.
    """

    def __init__(self) -> None:
        self._window = None
        self._drop_lock = threading.Lock()
        self._dropped_paths: list[str] = []

    def _emit(self, event: str, data: Any = None) -> None:
        """Dispatch a ``CustomEvent`` named ``pywebvue:{event}`` to the frontend."""
        import json

        if self._window is None:
            return

        payload = json.dumps(data, ensure_ascii=False) if data is not None else "null"
        js = f"document.dispatchEvent(new CustomEvent('pywebvue:{event}', {{detail: {payload}, bubbles:       
         + true}}))"
        try:
            self._window.evaluate_js(js)
        except Exception:
            pass

    def _on_drop(self, event: dict) -> None:
        """Handle native file drag-and-drop events from pywebview."""
        files = event.get("dataTransfer", {}).get("files", [])
        paths = [
            f.get("pywebviewFullPath")
            for f in files
            if f.get("pywebviewFullPath")
        ]
        if paths:
            with self._drop_lock:
                self._dropped_paths.extend(paths)

    def get_dropped_files(self) -> dict[str, Any]:
        """Return file paths from the most recent drop event and clear the buffer."""
        with self._drop_lock:
            paths = list(self._dropped_paths)
            self._dropped_paths.clear()
        return {"success": True, "data": paths}
