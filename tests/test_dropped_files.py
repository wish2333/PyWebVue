"""Tests for drag-and-drop file handling."""

from __future__ import annotations

import threading

from pywebvue.bridge import Bridge


class TestGetDroppedFilesEmpty:
    def test_returns_empty_when_no_drops(self):
        b = Bridge()
        result = b.get_dropped_files()
        assert result == {"success": True, "data": []}


class TestOnDrop:
    def test_parses_file_paths(self):
        b = Bridge()
        b._on_drop({
            "dataTransfer": {
                "files": [
                    {"pywebviewFullPath": "/tmp/a.txt"},
                    {"pywebviewFullPath": "/tmp/b.csv"},
                ]
            }
        })
        result = b.get_dropped_files()
        assert result["data"] == ["/tmp/a.txt", "/tmp/b.csv"]

    def test_ignores_files_without_path(self):
        b = Bridge()
        b._on_drop({
            "dataTransfer": {
                "files": [
                    {"pywebviewFullPath": "/tmp/real.txt"},
                    {"name": "no_path.txt"},
                    {"pywebviewFullPath": None},
                ]
            }
        })
        result = b.get_dropped_files()
        assert result["data"] == ["/tmp/real.txt"]

    def test_empty_event(self):
        b = Bridge()
        b._on_drop({"dataTransfer": {"files": []}})
        result = b.get_dropped_files()
        assert result["data"] == []

    def test_malformed_event(self):
        b = Bridge()
        b._on_drop({})
        result = b.get_dropped_files()
        assert result["data"] == []


class TestGetDroppedFilesClearsBuffer:
    def test_second_call_returns_empty(self):
        b = Bridge()
        b._on_drop({
            "dataTransfer": {
                "files": [{"pywebviewFullPath": "/tmp/file.txt"}]
            }
        })
        first = b.get_dropped_files()
        assert first["data"] == ["/tmp/file.txt"]
        second = b.get_dropped_files()
        assert second["data"] == []


class TestDroppedFilesThreadSafety:
    def test_concurrent_drops_and_reads(self):
        b = Bridge()
        errors = []

        def _dropper(n):
            try:
                for i in range(50):
                    b._on_drop({
                        "dataTransfer": {
                            "files": [{"pywebviewFullPath": f"/tmp/{n}_{i}.txt"}]
                        }
                    })
            except Exception as e:
                errors.append(e)

        def _reader():
            try:
                for _ in range(50):
                    b.get_dropped_files()
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=_dropper, args=(0,)),
            threading.Thread(target=_dropper, args=(1,)),
            threading.Thread(target=_reader),
            threading.Thread(target=_reader),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert not errors
