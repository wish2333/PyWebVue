"""Process Tool API - demonstrates ProcessManager with start/pause/resume/stop."""

from __future__ import annotations

import shlex
from typing import Any

from pywebvue import ApiBase, Result, ErrCode, ProcessManager, ProcessState


class ProcessToolApi(ApiBase):
    """API for managing subprocesses via the ProcessManager."""

    def __init__(self) -> None:
        super().__init__()
        self.pm = ProcessManager(self, name="worker")

    def health_check(self) -> Result:
        """Return backend status information."""
        return Result.ok(data={"status": "running"})

    def on_file_drop(self, file_paths: list[str]) -> None:
        """Handle files dropped onto the window."""
        for path in file_paths:
            self.logger.info(f"File dropped: {path}")
            self.emit("file:dropped", {"path": path})

    def get_status(self) -> Result:
        """Return current process state and PID."""
        return Result.ok(data={
            "state": self.pm.state.value,
            "pid": self.pm.pid,
            "timeout_remaining": self.pm.timeout_remaining,
        })

    def start_task(self, cmd: str, timeout: int | None = None) -> Result:
        """Start a subprocess with the given command string."""
        if self.pm.is_running or self.pm.is_paused:
            return Result.fail(
                ErrCode.PROCESS_ALREADY_RUNNING,
                detail=f"Process is {self.pm.state.value}",
            )

        try:
            parts = shlex.split(cmd, posix=False if self.pm is not None else True)
        except ValueError as e:
            return Result.fail(ErrCode.PARAM_INVALID, detail=str(e))

        if not parts:
            return Result.fail(ErrCode.PARAM_INVALID, detail="Empty command")

        result = self.pm.start(
            cmd=parts,
            on_output=lambda line: self.logger.info(f"[worker] {line}"),
            on_complete=lambda rc: self.logger.info(f"Process exited with code {rc}"),
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
            self.emit("process:state_changed", {"state": "idle"})
        return result
