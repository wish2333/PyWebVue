"""File Tool API - file metadata display and hash computation."""

from __future__ import annotations

import hashlib
import os
import stat
import sys
from datetime import datetime
from typing import Any

from pywebvue import ApiBase, Result, ErrCode


# Common file extension categories for display
_EXT_CATEGORIES = {
    "code": {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cpp", ".h", ".go", ".rs", ".rb", ".php", ".swift", ".kt"},
    "data": {".json", ".xml", ".yaml", ".yml", ".toml", ".csv", ".tsv", ".ini", ".cfg"},
    "doc": {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".md", ".rst"},
    "image": {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg", ".webp", ".ico", ".tiff"},
    "archive": {".zip", ".tar", ".gz", ".rar", ".7z", ".bz2", ".xz"},
    "executable": {".exe", ".msi", ".bat", ".sh", ".dll", ".so", ".dylib"},
    "media": {".mp3", ".mp4", ".wav", ".avi", ".mkv", ".flac", ".ogg", ".webm"},
}


def _categorize(ext: str) -> str:
    for category, exts in _EXT_CATEGORIES.items():
        if ext in exts:
            return category
    return "other"


def _format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    if size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


class FileToolApi(ApiBase):
    """API for inspecting file metadata and computing file hashes."""

    def health_check(self) -> Result:
        """Return backend status information."""
        return Result.ok(data={"status": "running"})

    def on_file_drop(self, file_paths: list[str]) -> None:
        """Handle files dropped onto the window."""
        for path in file_paths:
            self.logger.info(f"File dropped: {path}")
            self.emit("file:dropped", {"path": path})

    def browse_files(self) -> Result:
        """Open a native file dialog to select files."""
        paths = self.dialog.open_file(title="Select Files", multiple=True)
        if paths is None:
            return Result.fail(ErrCode.PARAM_INVALID, detail="Selection cancelled")
        for path in paths:
            self.emit("file:dropped", {"path": path})
        return Result.ok(data={"count": len(paths), "paths": paths})

    def get_file_info(self, path: str) -> Result:
        """Get file metadata: name, size, extension, modified time, type category."""
        if not os.path.isfile(path):
            return Result.fail(ErrCode.FILE_NOT_FOUND, detail=path)

        try:
            file_stat = os.stat(path)
        except OSError as e:
            return Result.fail(ErrCode.FILE_READ_ERROR, detail=str(e))

        _, ext = os.path.splitext(path)
        size_bytes = file_stat.st_size
        mtime = datetime.fromtimestamp(file_stat.st_mtime).isoformat()

        mode = file_stat.st_mode
        is_binary = False
        if stat.S_ISREG(mode):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    f.read(1024)
            except (UnicodeDecodeError, OSError):
                is_binary = True

        ext_lower = ext.lower() if ext else ""
        category = _categorize(ext_lower)

        return Result.ok(data={
            "path": path,
            "name": os.path.basename(path),
            "extension": ext_lower if ext_lower else "(none)",
            "size_bytes": size_bytes,
            "size_display": _format_size(size_bytes),
            "modified": mtime,
            "is_binary": is_binary,
            "category": category,
        })

    def compute_hash(self, path: str) -> Result:
        """Compute MD5 and SHA-256 hashes for a file, with progress events."""
        if not os.path.isfile(path):
            return Result.fail(ErrCode.FILE_NOT_FOUND, detail=path)

        file_size = os.path.getsize(path)
        self.run_in_thread(self._compute_hash, path, file_size)
        return Result.ok(data={"message": "Hash computation started"})

    def _compute_hash(self, path: str, file_size: int) -> None:
        """Compute file hashes in chunks, emitting progress updates."""
        md5 = hashlib.md5()
        sha256 = hashlib.sha256()
        chunk_size = 65536  # 64KB chunks
        processed = 0
        report_interval = max(1, file_size // 20)  # ~20 progress updates

        self.emit("progress:update", {
            "current": 0,
            "total": file_size,
            "label": "Reading file...",
        })

        try:
            with open(path, "rb") as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    md5.update(chunk)
                    sha256.update(chunk)
                    processed += len(chunk)
                    if report_interval > 0 and processed % report_interval < chunk_size:
                        pct = processed * 100 // file_size
                        self.emit("progress:update", {
                            "current": processed,
                            "total": file_size,
                            "label": f"Computing hashes... {pct}%",
                        })
        except OSError as e:
            self.emit("progress:update", {"current": 0, "total": 0})
            self.emit("hash:error", {"path": path, "message": str(e)})
            return

        self.emit("progress:update", {"current": 0, "total": 0})
        self.emit("hash:complete", {
            "path": path,
            "name": os.path.basename(path),
            "md5": md5.hexdigest(),
            "sha256": sha256.hexdigest(),
            "size": _format_size(file_size),
        })
        self.logger.info(f"Hash complete: {path}")
