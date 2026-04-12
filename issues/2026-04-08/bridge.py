"""Bridge base class and @expose decorator."""

from __future__ import annotations

import functools
import json
import logging
import queue
import threading
from typing import Any, Callable

logger = logging.getLogger(__name__)


def expose(func: Callable[..., Any]) -> Callable[..., Any]:
    """Wrap a bridge method with try/except error handling.

    Exposed methods should return ``{"success": True, "data": ...}``.
    On unhandled exception, the decorator returns
    ``{"success": False, "error": "..."}`` instead of crashing.
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    return wrapper


class Bridge:
    """Base class for Python APIs exposed to the frontend.

    Subclass this and decorate public methods with ``@expose``.
    Use ``self._emit(event_name, data)`` to push events to the frontend.

    Thread safety: ``_emit`` can be called from any thread (background
    threads for long-running work). Events are queued and flushed to
    the WebView via a periodic JS timer that calls ``_pywebvue_flush``.
    This avoids calling ``evaluate_js`` from non-main threads, which
    crashes on Windows due to COM/WebView2 threading requirements.
    """

    def __init__(self) -> None:
        self._window = None
        self._drop_lock = threading.Lock()
        self._dropped_paths: list[str] = []
        self._event_queue: queue.Queue[tuple[str, Any]] = queue.Queue()

        # Task execution system: background threads can schedule work
        # to run on the main thread via _execute_task (called by JS).
        # Maps task_id -> (result_queue, command, args)
        self._task_queue: queue.Queue[tuple[str, str, Any]] = queue.Queue()
        self._pending_results: dict[str, queue.Queue[tuple[bool, Any]]] = {}
        self._task_lock = threading.Lock()

    def _emit(self, event: str, data: Any = None) -> None:
        """Thread-safe: queue an event for main-thread delivery."""
        self._event_queue.put((event, data))

    @expose
    def flush_events(self) -> dict[str, Any]:
        """Process all queued events via evaluate_js on the main thread.

        Called periodically by a JS timer (``setInterval``) set up
        in ``pywebvue.app.App._setup_drag_drop``.
        """
        # If window is already closed/destroyed, drop all events and mark
        # the bridge as dead to avoid further evaluate_js calls.
        if self._window is None:
            # Clear the queue to avoid memory growth
            while True:
                try:
                    self._event_queue.get_nowait()
                except queue.Empty:
                    break
            return {"success": False, "error": "window not available"}

        while True:
            try:
                event, data = self._event_queue.get_nowait()
            except queue.Empty:
                break

            payload = json.dumps(data, ensure_ascii=False) if data is not None else "null"
            js = (
                f"document.dispatchEvent(new CustomEvent('pywebvue:{event}', "
                f"{{detail: {payload}, bubbles: true}}))"
            )
            try:
                self._window.evaluate_js(js)
            except Exception as e:
                # Window might be closing or already destroyed.
                # Clear remaining events and mark window as None.
                logger.debug("evaluate_js failed for event %s: %s", event, e)
                # Drain the queue to avoid repeated failures
                while True:
                    try:
                        self._event_queue.get_nowait()
                    except queue.Empty:
                        break
                # Mark window as unavailable to stop further calls
                self._window = None
                break

        return {"success": True}

    @expose
    def execute_task(self) -> dict[str, Any]:
        """Execute pending tasks on the main thread.

        Called periodically by JS timer alongside flush_events.
        Processes tasks from _task_queue and stores results in _pending_results.
        """
        try:
            task_id, command, args = self._task_queue.get_nowait()
            logger.info("execute_task: executing task %s (command: %s, args: %s)", task_id, command, args)
        except queue.Empty:
            # No tasks - this is normal, don't spam logs
            return {"success": True, "data": None}

        try:
            # Dispatch to registered command handlers
            result = self.dispatch_task(command, args)
            logger.debug("execute_task: task %s completed, storing result", task_id)
            # Store result for the waiting thread to retrieve
            with self._task_lock:
                if task_id in self._pending_results:
                    self._pending_results[task_id].put((True, result))
                else:
                    logger.warning("Task %s result queue not found (may have timed out)", task_id)
            return {"success": True, "data": True}
        except Exception as e:
            logger.error("_execute_task: task %s failed: %s", task_id, e, exc_info=True)
            with self._task_lock:
                if task_id in self._pending_results:
                    self._pending_results[task_id].put((False, str(e)))
            return {"success": False, "error": str(e)}

    def dispatch_task(self, command: str, args: Any) -> Any:
        """Dispatch task command to appropriate handler.

        Override this method in subclasses to add custom commands.
        Base class raises error for unknown commands.
        """
        raise ValueError(f"Unknown task command: {command}")

    def run_on_main_thread(self, command: str, args: Any = None, timeout: float = 60.0) -> Any:
        """Schedule a task to run on the main thread and wait for result.

        Thread-safe: can be called from any background thread.
        The task is executed on the main thread via execute_task JS bridge.

        Args:
            command: String command identifier (must be registered in dispatch_task).
            args: Arguments to pass to the command handler (must be JSON-serializable).
            timeout: Maximum seconds to wait for completion.

        Returns:
            The result of the command handler.

        Raises:
            TimeoutError: If task takes longer than timeout.
            RuntimeError: If task fails.
        """
        import uuid
        task_id = str(uuid.uuid4())
        logger.info("run_on_main_thread: queuing task %s (command: %s, args: %s)", task_id, command, args)

        # Create a queue for the result
        result_queue: queue.Queue[tuple[bool, Any]] = queue.Queue()

        with self._task_lock:
            self._pending_results[task_id] = result_queue

        # Queue the task (command string + args, not a callable)
        logger.info("Queuing task %s (command: %s)", task_id, command)
        try:
            self._task_queue.put((task_id, command, args))
            logger.debug("Task %s queued, queue size: %d", task_id, self._task_queue.qsize())
        except Exception as e:
            logger.error("Failed to queue task %s: %s", task_id, e, exc_info=True)
            raise

        try:
            # Wait for result with timeout
            logger.info("Waiting for task %s result (timeout: %s)...", task_id, timeout)
            success, result = result_queue.get(timeout=timeout)
            logger.info("Task %s completed: success=%s", task_id, success)
            if not success:
                raise RuntimeError(f"Task '{command}' failed: {result}")
            return result
        except queue.Empty:
            logger.error("Task %s (%s) timed out after %s seconds", task_id, command, timeout)
            logger.error("Queue size at timeout: %d", self._task_queue.qsize())
            logger.error("Pending results keys: %s", list(self._pending_results.keys()))
            raise TimeoutError(f"Task '{command}' (id={task_id}) timed out after {timeout}s")
        finally:
            # Cleanup
            with self._task_lock:
                if task_id in self._pending_results:
                    del self._pending_results[task_id]
                    logger.info("Cleaned up pending result for task %s", task_id)

    def _on_drop(self, event: dict) -> None:
        """Handle native file drag-and-drop events from pywebview."""
        files = event.get("dataTransfer", {}).get("files", [])
        paths = [
            f.get("pywebviewFullPath")
            for f in files
            if f.get("pywebviewFullPath")
        ]
        if paths:
            with self._drop_lock:
                self._dropped_paths.extend(paths)

    @expose
    def get_dropped_files(self) -> dict[str, Any]:
        """Return file paths from the most recent drop event and clear the buffer."""
        with self._drop_lock:
            paths = list(self._dropped_paths)
            self._dropped_paths.clear()
        return {"success": True, "data": paths}
