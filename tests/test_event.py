"""Tests for event name validation and _flush_events serialization."""

from __future__ import annotations

import json

import pytest

from pywebvue.bridge import Bridge


class TestEmitValidation:
    """Event names must match _EVENT_RE: ^[A-Za-z0-9_.:-]{1,128}$"""

    @pytest.mark.parametrize(
        "name",
        ["tick", "status-update", "my.event", "ns:event", "v2_update", "a" * 128],
    )
    def test_valid_event_names(self, name):
        b = Bridge()
        b._emit(name)  # should not raise
        assert b._event_queue.qsize() == 1

    @pytest.mark.parametrize(
        "name",
        [
            "",          # empty
            "a" * 129,   # too long
            "bad name",  # space
            "bad!name",  # special char
            "name'x",    # quote injection
            "name;x",    # semicolon
        ],
    )
    def test_invalid_event_names(self, name):
        b = Bridge()
        with pytest.raises(ValueError, match="Invalid event name"):
            b._emit(name)


class TestFlushEventsNoWindow:
    """When no window is set, _flush_events drains the queue silently."""

    def test_drains_queue(self):
        b = Bridge()
        b._emit("a", 1)
        b._emit("b", 2)
        assert b._event_queue.qsize() == 2
        b._flush_events()
        assert b._event_queue.qsize() == 0


class TestFlushEventsSerialization:
    """Verify that _flush_events produces safe JS via json.dumps."""

    def test_event_name_is_json_encoded(self):
        b = Bridge()
        b._window = _FakeWindow(capture_js=True)
        b._emit("tick", {"count": 1})
        b._flush_events()
        js = b._window.captured_js[0]
        # event name should be json.dumps'd, not raw string
        assert 'new CustomEvent("pywebvue:tick"' in js

    def test_payload_is_json_encoded(self):
        b = Bridge()
        b._window = _FakeWindow(capture_js=True)
        b._emit("data", {"key": "val"})
        b._flush_events()
        js = b._window.captured_js[0]
        assert '"key": "val"' in js or '"key":"val"' in js

    def test_null_payload(self):
        b = Bridge()
        b._window = _FakeWindow(capture_js=True)
        b._emit("ping")
        b._flush_events()
        js = b._window.captured_js[0]
        assert "null" in js

    def test_window_closed_on_evaluate_failure(self):
        b = Bridge()
        b._window = _FakeWindow(raise_on_eval=True)
        b._emit("tick", {})
        b._flush_events()
        assert b._window is None


class _FakeWindow:
    """Minimal window mock that captures or rejects evaluate_js calls."""

    def __init__(self, capture_js=False, raise_on_eval=False):
        self.capture_js = capture_js
        self.raise_on_eval = raise_on_eval
        self.captured_js: list[str] = []

    def evaluate_js(self, js: str):
        if self.raise_on_eval:
            raise RuntimeError("window closed")
        if self.capture_js:
            self.captured_js.append(js)
