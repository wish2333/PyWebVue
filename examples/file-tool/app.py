"""File Tool API - file metadata display and simulated processing."""

from __future__ import annotations

import os
import stat
import time
import threading
from datetime import datetime
from typing import Any

from pywebvue import ApiBase, Result, ErrCode


class FileToolApi(ApiBase):
    """API for inspecting file metadata and simulating file processing."""

    def health_check(self) -> Result:
        """Return backend status information."""
        return Result.ok(data={"status": "running"})

    def on_file_drop(self, file_paths: list[str]) -> None:
        """Handle files dropped onto the window."""
        for path in file_paths:
            self.logger.info(f"File dropped: {path}")
            self.emit("file:dropped", {"path": path})

    def get_file_info(self, path: str) -> Result:
        """Get file metadata: size, extension, modified time, type."""
        if not os.path.isfile(path):
            return Result.fail(ErrCode.FILE_NOT_FOUND, detail=path)

        try:
            file_stat = os.stat(path)
        except OSError as e:
            return Result.fail(ErrCode.FILE_READ_ERROR, detail=str(e))

        _, ext = os.path.splitext(path)
        size_bytes = file_stat.st_size
        mtime = datetime.fromtimestamp(file_stat.st_mtime).isoformat()

        if size_bytes < 1024:
            size_display = f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            size_display = f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            size_display = f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            size_display = f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

        mode = file_stat.st_mode
        is_binary = False
        if stat.S_ISREG(mode):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    f.read(1024)
            except (UnicodeDecodeError, OSError):
                is_binary = True

        return Result.ok(data={
            "path": path,
            "name": os.path.basename(path),
            "extension": ext.lower() if ext else "(none)",
            "size_bytes": size_bytes,
            "size_display": size_display,
            "modified": mtime,
            "is_binary": is_binary,
        })

    def process_file(self, path: str) -> Result:
        """Start simulated file processing in a background thread.

        Emits progress:update events and file:process_complete when done.
        """
        if not os.path.isfile(path):
            return Result.fail(ErrCode.FILE_NOT_FOUND, detail=path)

        self.run_in_thread(self._simulate_processing, path)
        return Result.ok(data={"message": "Processing started"})

    def _simulate_processing(self, path: str) -> None:
        """Simulate a multi-step file processing pipeline."""
        total_steps = 10
        for i in range(1, total_steps + 1):
            time.sleep(0.5)
            self.emit("progress:update", {
                "current": i,
                "total": total_steps,
                "label": f"Step {i}/{total_steps}: {'Analyzing' if i <= 3 else 'Transforming' if i <= 7 else 'Optimizing'}",
            })
            self.logger.info(f"Processing [{i}/{total_steps}]: {os.path.basename(path)}")

        self.emit("progress:update", {"current": 0, "total": 0})
        self.emit("file:process_complete", {
            "path": path,
            "name": os.path.basename(path),
        })
        self.logger.info(f"Processing complete: {path}")
