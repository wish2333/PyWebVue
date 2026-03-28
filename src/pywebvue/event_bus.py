"""Event bus for Python-to-frontend communication."""

from __future__ import annotations

import json
from typing import Any

from loguru import logger

from .constants import DISPATCH_FN


BRIDGE_JS = """\
window.__pywebvue_event_listeners = {};
window.__pywebvue_dispatch = function(eventName, payload) {
    var listeners = window.__pywebvue_event_listeners[eventName];
    if (listeners) {
        for (var i = 0; i < listeners.length; i++) {
            try { listeners[i](payload); } catch(e) { console.error(e); }
        }
    }
};
window.pywebvue = window.pywebvue || {};
window.pywebvue.event = {
    on: function(name, callback) {
        if (!window.__pywebvue_event_listeners[name]) {
            window.__pywebvue_event_listeners[name] = [];
        }
        window.__pywebvue_event_listeners[name].push(callback);
    },
    off: function(name, callback) {
        var list = window.__pywebvue_event_listeners[name];
        if (!list) return;
        window.__pywebvue_event_listeners[name] = list.filter(function(cb) { return cb !== callback; });
    }
};
"""


class EventBus:
    """Push events from Python to frontend via pywebview evaluate_js.

    The bridge JS (BRIDGE_JS) must be injected into the page before events
    can be dispatched. This is typically done in App._on_window_loaded().
    """

    def __init__(self) -> None:
        self._window: Any = None

    def bind(self, window: Any) -> None:
        """Bind a pywebview window reference."""
        self._window = window

    @property
    def is_bound(self) -> bool:
        return self._window is not None

    def emit(self, event_name: str, data: Any = None) -> None:
        """Dispatch an event to the frontend.

        Args:
            event_name: Event name in 'module:action' format (e.g. 'log:add').
            data: JSON-serializable payload.
        """
        if self._window is None:
            logger.debug(f"EventBus.emit skipped (window not bound): {event_name}")
            return
        try:
            json_str = json.dumps(data if data is not None else {}, ensure_ascii=False)
            self._window.evaluate_js(
                f'{DISPATCH_FN}("{event_name}", {json_str})'
            )
        except Exception as e:
            logger.warning(f"EventBus.emit failed for '{event_name}': {e}")
