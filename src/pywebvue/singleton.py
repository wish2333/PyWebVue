"""Cross-platform singleton lock to prevent multiple app instances."""

from __future__ import annotations

import os
import sys
import tempfile

from loguru import logger


class SingletonLock:
    """File-based singleton lock using platform-native primitives.

    Usage::

        lock = SingletonLock("my_app")
        if lock.acquire():
            try:
                app.run()
            finally:
                lock.release()
        else:
            print("Already running")
    """

    def __init__(self, app_name: str) -> None:
        self._app_name = app_name
        self._lock_path = os.path.join(tempfile.gettempdir(), f"{app_name}.lock")
        self._fd: int | None = None

    @property
    def lock_path(self) -> str:
        return self._lock_path

    def acquire(self) -> bool:
        """Try to acquire the lock. Returns True on success."""
        # Check if a previous instance is still alive
        if os.path.exists(self._lock_path):
            old_pid = self._read_pid()
            if old_pid is not None and self._is_process_alive(old_pid):
                logger.info(
                    f"Another instance of '{self._app_name}' is already running (PID {old_pid})"
                )
                return False
            # Stale lock file, remove it
            try:
                os.unlink(self._lock_path)
            except OSError:
                pass

        try:
            if sys.platform == "win32":
                import msvcrt
                self._fd = os.open(self._lock_path, os.O_CREAT | os.O_WRONLY)
                msvcrt.locking(self._fd, msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                self._fd = os.open(self._lock_path, os.O_CREAT | os.O_WRONLY)
                fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

            # Write current PID
            os.write(self._fd, str(os.getpid()).encode())
            os.ftruncate(self._fd, len(str(os.getpid())))
            return True

        except (OSError, IOError):
            self._fd = None
            return False

    def release(self) -> None:
        """Release the lock."""
        if self._fd is None:
            return
        try:
            if sys.platform == "win32":
                import msvcrt
                msvcrt.locking(self._fd, msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self._fd, fcntl.LOCK_UN)
            os.close(self._fd)
        except (OSError, IOError):
            pass
        finally:
            self._fd = None
            try:
                os.unlink(self._lock_path)
            except OSError:
                pass

    def _read_pid(self) -> int | None:
        """Read PID from an existing lock file."""
        try:
            with open(self._lock_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    return int(content)
        except (OSError, ValueError):
            pass
        return None

    @staticmethod
    def _is_process_alive(pid: int) -> bool:
        """Check whether a process with the given PID is running."""
        try:
            os.kill(pid, 0)
            return True
        except (OSError, PermissionError):
            return False

    def __enter__(self) -> bool:
        acquired = self.acquire()
        if not acquired:
            raise RuntimeError(
                f"Cannot acquire singleton lock for '{self._app_name}'. "
                f"Another instance may be running."
            )
        return True

    def __exit__(self, *args: object) -> None:
        self.release()
