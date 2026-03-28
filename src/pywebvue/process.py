"""Subprocess manager with thread-safe state machine and cross-platform pause/resume."""

from __future__ import annotations

import enum
import os
import signal
import subprocess
import sys
import threading
import time
from typing import Any, Callable

from loguru import logger

from .result import ErrCode, Result


class ProcessState(enum.Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"


class ProcessManager:
    """Manage a subprocess with real-time output streaming and pause/resume.

    Usage::

        pm = ProcessManager(api_instance, name="encode")
        pm.start(cmd=["python", "task.py"], cwd=".", on_output=handle_line)
        pm.pause()
        pm.resume()
        pm.stop()

    Events emitted (via ApiBase.emit):
        - process:{name}:output   {"line": "..."}
        - process:{name}:complete {"returncode": int}
        - process:{name}:timeout  {"timeout": int}
    """

    def __init__(self, api_base: Any, name: str = "default") -> None:
        self._api = api_base
        self._name = name
        self._process: subprocess.Popen[str] | None = None
        self._state = ProcessState.IDLE
        self._lock = threading.Lock()
        self._reader_thread: threading.Thread | None = None
        self._on_output: Callable[[str], None] | None = None
        self._on_complete: Callable[[int], None] | None = None
        self._timeout_event: threading.Event | None = None
        self._timeout_start_time: float | None = None
        self._timeout_duration: int | None = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def state(self) -> ProcessState:
        with self._lock:
            return self._state

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._state == ProcessState.RUNNING

    @property
    def is_paused(self) -> bool:
        with self._lock:
            return self._state == ProcessState.PAUSED

    @property
    def pid(self) -> int | None:
        with self._lock:
            if self._process:
                return self._process.pid
            return None

    @property
    def timeout_remaining(self) -> int | None:
        """Approximate seconds remaining before timeout (None if no timeout set)."""
        with self._lock:
            if self._timeout_start_time is None or self._timeout_duration is None:
                return None
            if self._timeout_event is not None and self._timeout_event.is_set():
                return None
            elapsed = time.monotonic() - self._timeout_start_time
            return max(0, self._timeout_duration - int(elapsed))

    def start(
        self,
        cmd: list[str],
        cwd: str = ".",
        on_output: Callable[[str], None] | None = None,
        on_complete: Callable[[int], None] | None = None,
        timeout: int | None = None,
    ) -> Result:
        """Start a subprocess.

        Args:
            cmd: Command and arguments.
            cwd: Working directory for the subprocess.
            on_output: Callback invoked for each line of stdout/stderr.
            on_complete: Callback invoked when the process exits.
            timeout: Auto-stop after this many seconds. If None, attempts
                     to read ``process.default_timeout`` from config.
        """
        with self._lock:
            # Auto-reset from STOPPED to IDLE for convenience
            if self._state == ProcessState.STOPPED:
                self._state = ProcessState.IDLE
                self._process = None

            if self._state != ProcessState.IDLE:
                return Result.fail(
                    ErrCode.PROCESS_ALREADY_RUNNING,
                    detail=f"Process '{self._name}' state: {self._state.value}",
                )

            self._on_output = on_output
            self._on_complete = on_complete

            try:
                kwargs: dict[str, Any] = {
                    "args": cmd,
                    "cwd": cwd,
                    "stdout": subprocess.PIPE,
                    "stderr": subprocess.STDOUT,
                    "text": True,
                    "bufsize": 1,
                }
                if sys.platform == "win32":
                    kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]

                self._process = subprocess.Popen(**kwargs)
                self._state = ProcessState.RUNNING
            except OSError as e:
                self._state = ProcessState.IDLE
                return Result.fail(ErrCode.PROCESS_START_FAILED, detail=str(e))

        self._reader_thread = threading.Thread(
            target=self._read_output, daemon=True
        )
        self._reader_thread.start()

        # Resolve timeout: explicit param > config > None
        resolved_timeout = timeout
        if resolved_timeout is None and self._api is not None:
            cfg = getattr(self._api, "_config", None)
            if cfg is not None:
                resolved_timeout = getattr(cfg, "process", None)
                if resolved_timeout is not None:
                    resolved_timeout = getattr(resolved_timeout, "default_timeout", None)

        if resolved_timeout is not None and resolved_timeout > 0:
            self._start_timeout_thread(resolved_timeout)

        return Result.ok()

    def reset(self) -> Result:
        """Reset to IDLE state, allowing a new start()."""
        with self._lock:
            if self._state == ProcessState.IDLE:
                return Result.fail(ErrCode.PROCESS_NOT_RUNNING, detail="Already idle")
            if self._state in (ProcessState.RUNNING, ProcessState.PAUSED):
                return Result.fail(
                    ErrCode.PROCESS_ALREADY_RUNNING,
                    detail="Stop the process before resetting",
                )
            self._state = ProcessState.IDLE
            self._process = None
        return Result.ok()

    def _start_timeout_thread(self, timeout: int) -> None:
        """Start a daemon timer that auto-stops the process after *timeout* seconds."""

        def _timer() -> None:
            if self._timeout_event is None:
                return
            triggered = self._timeout_event.wait(timeout)
            if not triggered and self.is_running:
                self._emit("timeout", {"timeout": timeout})
                logger.warning(f"Process '{self._name}' timed out after {timeout}s")
                self.stop()

        self._timeout_event = threading.Event()
        self._timeout_start_time = time.monotonic()
        self._timeout_duration = timeout
        threading.Thread(target=_timer, daemon=True).start()

    def _cancel_timeout(self) -> None:
        """Signal the timeout thread to stop waiting."""
        if self._timeout_event is not None:
            self._timeout_event.set()
            self._timeout_event = None
            self._timeout_start_time = None
            self._timeout_duration = None

    def _read_output(self) -> None:
        """Read process stdout/stderr line by line in a background thread."""
        process = self._process
        if process is None or process.stdout is None:
            return

        try:
            for line in process.stdout:
                stripped = line.rstrip("\n\r")
                self._emit("output", {"line": stripped})
                if self._on_output:
                    self._on_output(stripped)
        except Exception:
            pass
        finally:
            returncode = process.wait()
            self._cancel_timeout()
            with self._lock:
                self._state = ProcessState.STOPPED
            self._emit("complete", {"returncode": returncode})
            if self._on_complete:
                self._on_complete(returncode)

    def pause(self) -> Result:
        """Pause the subprocess."""
        with self._lock:
            if self._state != ProcessState.RUNNING or self._process is None:
                return Result.fail(
                    ErrCode.PROCESS_NOT_RUNNING,
                    detail=f"Cannot pause, state: {self._state.value}",
                )

            if sys.platform == "win32":
                _suspend_process(self._process.pid)
            else:
                os.kill(self._process.pid, signal.SIGSTOP)

            self._state = ProcessState.PAUSED
            return Result.ok()

    def resume(self) -> Result:
        """Resume a paused subprocess."""
        with self._lock:
            if self._state != ProcessState.PAUSED or self._process is None:
                return Result.fail(
                    ErrCode.PROCESS_NOT_RUNNING,
                    detail=f"Cannot resume, state: {self._state.value}",
                )

            if sys.platform == "win32":
                _resume_process(self._process.pid)
            else:
                os.kill(self._process.pid, signal.SIGCONT)

            self._state = ProcessState.RUNNING
            return Result.ok()

    def stop(self) -> Result:
        """Terminate the subprocess. Force-kills after 5 seconds."""
        with self._lock:
            if self._state not in (ProcessState.RUNNING, ProcessState.PAUSED) or self._process is None:
                return Result.fail(
                    ErrCode.PROCESS_NOT_RUNNING,
                    detail=f"Cannot stop, state: {self._state.value}",
                )

            self._state = ProcessState.STOPPED
            self._cancel_timeout()
            try:
                self._process.terminate()
            except OSError:
                pass

        # Wait outside the lock
        try:
            self._process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                self._process.kill()
            except OSError:
                pass

        return Result.ok()

    def _emit(self, action: str, data: dict[str, Any]) -> None:
        """Emit a process event via the API instance."""
        if self._api is not None:
            self._api.emit(f"process:{self._name}:{action}", data)


# ---------------------------------------------------------------------------
# Windows process suspend / resume via Win32 API
# ---------------------------------------------------------------------------

if sys.platform == "win32":
    import ctypes

    _kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]

    PROCESS_SUSPEND_RESUME = 0x0800
    THREAD_SUSPEND_RESUME = 0x0002
    TH32CS_SNAPTHREAD = 0x00000004

    class _THREADENTRY32(ctypes.Structure):  # type: ignore[misc]
        _fields_ = [
            ("dwSize", ctypes.c_ulong),
            ("cntUsage", ctypes.c_ulong),
            ("th32ThreadID", ctypes.c_ulong),
            ("th32OwnerProcessID", ctypes.c_ulong),
            ("tpBasePri", ctypes.c_long),
            ("tpDeltaPri", ctypes.c_long),
            ("dwFlags", ctypes.c_ulong),
        ]

    def _enum_threads(pid: int) -> list[int]:
        """Enumerate thread IDs belonging to a process on Windows."""
        threads: list[int] = []
        snapshot = _kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, pid)
        if snapshot == -1 or snapshot == 0xFFFFFFFF:
            return threads
        try:
            te = _THREADENTRY32()
            te.dwSize = ctypes.sizeof(_THREADENTRY32)
            if _kernel32.Thread32First(snapshot, ctypes.byref(te)):
                while True:
                    if te.th32OwnerProcessID == pid:
                        threads.append(te.th32ThreadID)
                    if not _kernel32.Thread32Next(snapshot, ctypes.byref(te)):
                        break
        finally:
            _kernel32.CloseHandle(snapshot)
        return threads

    def _suspend_process(pid: int) -> None:
        """Suspend all threads of a Windows process (NtSuspendProcess preferred)."""
        handle = _kernel32.OpenProcess(PROCESS_SUSPEND_RESUME, False, pid)
        if not handle:
            logger.warning(f"Failed to open process {pid} for suspend")
            return
        try:
            ntdll = ctypes.windll.ntdll  # type: ignore[attr-defined]
            ntdll.NtSuspendProcess(handle)
        except (AttributeError, OSError):
            for tid in _enum_threads(pid):
                h_thread = _kernel32.OpenThread(THREAD_SUSPEND_RESUME, False, tid)
                if h_thread:
                    _kernel32.SuspendThread(h_thread)
                    _kernel32.CloseHandle(h_thread)
        finally:
            _kernel32.CloseHandle(handle)

    def _resume_process(pid: int) -> None:
        """Resume all threads of a Windows process (NtResumeProcess preferred)."""
        handle = _kernel32.OpenProcess(PROCESS_SUSPEND_RESUME, False, pid)
        if not handle:
            logger.warning(f"Failed to open process {pid} for resume")
            return
        try:
            ntdll = ctypes.windll.ntdll  # type: ignore[attr-defined]
            ntdll.NtResumeProcess(handle)
        except (AttributeError, OSError):
            for tid in _enum_threads(pid):
                h_thread = _kernel32.OpenThread(THREAD_SUSPEND_RESUME, False, tid)
                if h_thread:
                    _kernel32.ResumeThread(h_thread)
                    _kernel32.CloseHandle(h_thread)
        finally:
            _kernel32.CloseHandle(handle)

else:
    # Unix: signals used directly in ProcessManager
    def _suspend_process(pid: int) -> None:  # noqa: D401
        pass

    def _resume_process(pid: int) -> None:  # noqa: D401
        pass
