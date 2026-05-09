"""Tests for the @expose decorator."""

from __future__ import annotations

from pywebvue.bridge import Bridge, expose


class _StubBridge(Bridge):
    """Minimal Bridge subclass for testing @expose in isolation."""

    @expose
    def ok(self) -> dict:
        return {"success": True, "data": 42}

    @expose
    def boom(self) -> dict:
        raise RuntimeError("something broke")

    @expose
    def boom_with_path(self) -> dict:
        raise FileNotFoundError("/secret/path/to/file.txt")


class TestExposeSuccess:
    def test_returns_dict_with_success_true(self):
        b = _StubBridge()
        result = b.ok()
        assert result == {"success": True, "data": 42}


class TestExposeExceptionProdMode:
    """debug=False (default): error details must be hidden."""

    def test_error_message_is_generic(self):
        b = _StubBridge()
        result = b.boom()
        assert result["success"] is False
        assert result["error"] == "Internal error"
        assert result["code"] == "INTERNAL_ERROR"

    def test_no_path_leak_in_error(self):
        b = _StubBridge()
        result = b.boom_with_path()
        assert "/secret/path" not in result["error"]


class TestExposeExceptionDebugMode:
    """debug=True: full exception string is returned."""

    def test_error_message_contains_detail(self):
        b = _StubBridge(debug=True)
        result = b.boom()
        assert result["success"] is False
        assert "something broke" in result["error"]
        assert result["code"] == "INTERNAL_ERROR"

    def test_error_message_contains_path(self):
        b = _StubBridge(debug=True)
        result = b.boom_with_path()
        assert "/secret/path/to/file.txt" in result["error"]


class TestExposeStandalone:
    """@expose on a plain function (not a Bridge method)."""

    def test_standalone_function_exception(self):
        @expose
        def standalone():
            raise ValueError("oops")

        result = standalone()
        assert result["success"] is False
        assert result["error"] == "Internal error"
        assert result["code"] == "INTERNAL_ERROR"
