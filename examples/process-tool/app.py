"""Process Tool API - demonstrates ProcessManager with start/pause/resume/stop."""

from __future__ import annotations

import os
import platform
import shlex
import sys
import time
from typing import Any

from pywebvue import ApiBase, Result, ErrCode, ProcessManager, ProcessState


# Platform-aware preset commands
def _get_presets() -> list[dict[str, str]]:
    is_win = sys.platform == "win32"

    presets = [
        {
            "name": "System Info",
            "description": "Display platform and Python version",
            "command": f"{sys.executable} -c \"import platform; print(f'OS: {platform.system()} {platform.release()}'); print(f'Arch: {platform.machine()}'); print(f'Python: {platform.python_version()}'); print(f'CPU count: {os.cpu_count()}')\"",
            "timeout": "10",
        },
        {
            "name": "Count to 20",
            "description": "Print numbers 1-20 with delays, good for pause/resume testing",
            "command": f"{sys.executable} -c \"for i in range(1, 21): print(f'line {{i}}'); import time; time.sleep(0.3)\"",
            "timeout": "30",
        },
        {
            "name": "Disk Usage",
            "description": "Show current directory disk usage summary",
            "command": "wmic logicaldisk get size,freespace,caption" if is_win else "df -h",
            "timeout": "10",
        },
        {
            "name": "Process List",
            "description": "List running processes (top 10)",
            "command": "tasklist /FI \"STATUS eq RUNNING\" /NH" if is_win else "ps aux | head -11",
            "timeout": "10",
        },
        {
            "name": "Network Interfaces",
            "description": "Display network adapter information",
            "command": "ipconfig" if is_win else "ifconfig 2>/dev/null || ip addr",
            "timeout": "10",
        },
        {
            "name": "Environment Variables",
            "description": "Print all environment variables",
            "command": f"{sys.executable} -c \"import os; [print(f'{{k}}={{v}}') for k, v in sorted(os.environ.items())]\"",
            "timeout": "10",
        },
    ]
    return presets


class ProcessToolApi(ApiBase):
    """API for managing subprocesses via the ProcessManager."""

    def __init__(self) -> None:
        super().__init__()
        self.pm = ProcessManager(self, name="worker")
        self._output_count = 0
        self._start_time: float | None = None

    def health_check(self) -> Result:
        """Return backend status information."""
        return Result.ok(data={"status": "running"})

    def get_presets(self) -> Result:
        """Return available preset commands."""
        return Result.ok(data={"presets": _get_presets()})

    def get_system_info(self) -> Result:
        """Return real system diagnostic information."""
        uname = platform.uname()
        info = {
            "system": uname.system,
            "release": uname.release,
            "version": uname.version,
            "machine": uname.machine,
            "python_version": platform.python_version(),
            "cpu_count": os.cpu_count(),
            "hostname": uname.node,
        }
        try:
            import psutil
            mem = psutil.virtual_memory()
            info["memory_total"] = mem.total
            info["memory_total_display"] = _format_size(mem.total)
            info["memory_used"] = mem.used
            info["memory_used_display"] = _format_size(mem.used)
            info["memory_percent"] = mem.percent
            info["cpu_percent"] = psutil.cpu_percent(interval=0.5)
        except ImportError:
            info["memory_total"] = None
            info["cpu_percent"] = None
        return Result.ok(data=info)

    def on_file_drop(self, file_paths: list[str]) -> None:
        """Handle files dropped onto the window."""
        for path in file_paths:
            self.logger.info(f"File dropped: {path}")

    def get_status(self) -> Result:
        """Return current process state, PID, and statistics."""
        elapsed = None
        if self._start_time is not None and (self.pm.is_running or self.pm.is_paused):
            elapsed = round(time.monotonic() - self._start_time, 1)

        return Result.ok(data={
            "state": self.pm.state.value,
            "pid": self.pm.pid,
            "timeout_remaining": self.pm.timeout_remaining,
            "output_count": self._output_count,
            "elapsed": elapsed,
        })

    def start_task(self, cmd: str, timeout: int | None = None) -> Result:
        """Start a subprocess with the given command string."""
        if self.pm.is_running or self.pm.is_paused:
            return Result.fail(
                ErrCode.PROCESS_ALREADY_RUNNING,
                detail=f"Process is {self.pm.state.value}",
            )

        try:
            parts = shlex.split(cmd, posix=(sys.platform != "win32"))
        except ValueError as e:
            return Result.fail(ErrCode.PARAM_INVALID, detail=str(e))

        if not parts:
            return Result.fail(ErrCode.PARAM_INVALID, detail="Empty command")

        self._output_count = 0
        self._start_time = time.monotonic()

        def on_output(line: str) -> None:
            self._output_count += 1
            self.logger.info(f"[worker] {line}")

        def on_complete(rc: int) -> None:
            self.logger.info(f"Process exited with code {rc}")
            self.emit("process:state_changed", {"state": "stopped"})

        result = self.pm.start(
            cmd=parts,
            on_output=on_output,
            on_complete=on_complete,
            timeout=timeout,
        )
        if result.is_ok:
            self.emit("process:state_changed", {"state": "running", "pid": self.pm.pid})
        return result

    def pause_task(self) -> Result:
        """Pause the running subprocess."""
        result = self.pm.pause()
        if result.is_ok:
            self.emit("process:state_changed", {"state": "paused"})
        return result

    def resume_task(self) -> Result:
        """Resume a paused subprocess."""
        result = self.pm.resume()
        if result.is_ok:
            self.emit("process:state_changed", {"state": "running"})
        return result

    def stop_task(self) -> Result:
        """Stop the subprocess."""
        result = self.pm.stop()
        if result.is_ok:
            self.emit("process:state_changed", {"state": "stopped"})
        return result

    def reset_task(self) -> Result:
        """Reset process to IDLE state."""
        result = self.pm.reset()
        if result.is_ok:
            self._output_count = 0
            self._start_time = None
            self.emit("process:state_changed", {"state": "idle"})
        return result


def _format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    if size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
