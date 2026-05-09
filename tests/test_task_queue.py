"""Tests for run_on_bridge, run_on_main_thread (deprecated), and task queue."""

from __future__ import annotations

import threading
import time
import warnings

import pytest

from pywebvue.bridge import Bridge


def _start_tick_loop(bridge: Bridge, stop_event: threading.Event) -> threading.Thread:
    """Simulate the JS tick loop that drives task execution."""

    def _loop():
        while not stop_event.is_set():
            bridge._execute_next_task()
            time.sleep(0.02)

    t = threading.Thread(target=_loop, daemon=True)
    t.start()
    return t


class TestRunOnBridgeSuccess:
    def test_executes_handler(self):
        b = Bridge()
        b.register_handler("double", lambda args: args * 2)
        stop = threading.Event()
        tick = _start_tick_loop(b, stop)
        try:
            result = b.run_on_bridge("double", 21, timeout=2)
            assert result == 42
        finally:
            stop.set()
            tick.join(timeout=2)

    def test_handler_receives_none_when_no_args(self):
        b = Bridge()
        b.register_handler("check", lambda args: args is None)
        stop = threading.Event()
        tick = _start_tick_loop(b, stop)
        try:
            result = b.run_on_bridge("check", timeout=2)
            assert result is True
        finally:
            stop.set()
            tick.join(timeout=2)


class TestRunOnBridgeErrors:
    def test_unknown_handler_raises_runtime_error(self):
        b = Bridge()
        stop = threading.Event()
        tick = _start_tick_loop(b, stop)
        try:
            with pytest.raises(RuntimeError, match="Unknown handler"):
                b.run_on_bridge("nonexistent", timeout=1)
        finally:
            stop.set()
            tick.join(timeout=2)

    def test_handler_exception_propagates(self):
        b = Bridge()

        def _fail(args):
            raise ValueError("boom")

        b.register_handler("fail", _fail)
        stop = threading.Event()
        tick = _start_tick_loop(b, stop)
        try:
            with pytest.raises(RuntimeError, match="Task 'fail' failed"):
                b.run_on_bridge("fail", timeout=1)
        finally:
            stop.set()
            tick.join(timeout=2)


class TestRunOnBridgeTimeout:
    def test_timeout_raises_timeout_error(self):
        b = Bridge()
        b.register_handler("slow", lambda args: "done")
        # No tick loop running, so task never gets executed
        with pytest.raises(TimeoutError, match="timed out"):
            b.run_on_bridge("slow", timeout=0.2)


class TestRunOnMainThreadDeprecated:
    def test_deprecated_alias_works(self):
        b = Bridge()
        b.register_handler("add", lambda args: args + 1)
        stop = threading.Event()
        tick = _start_tick_loop(b, stop)
        try:
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                result = b.run_on_main_thread("add", 9, timeout=2)
            assert result == 10
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "run_on_bridge" in str(w[0].message)
        finally:
            stop.set()
            tick.join(timeout=2)

    def test_deprecated_alias_passes_timeout(self):
        b = Bridge()
        b.register_handler("echo", lambda args: args)
        stop = threading.Event()
        tick = _start_tick_loop(b, stop)
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                result = b.run_on_main_thread("echo", "hi", timeout=2)
            assert result == "hi"
        finally:
            stop.set()
            tick.join(timeout=2)


class TestConcurrentTasks:
    def test_multiple_threads_can_enqueue(self):
        b = Bridge()
        results = []
        errors = []

        b.register_handler("mul", lambda args: args * 10)
        stop = threading.Event()
        tick = _start_tick_loop(b, stop)

        def _worker(val):
            try:
                r = b.run_on_bridge("mul", val, timeout=2)
                results.append(r)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=_worker, args=(i,)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        stop.set()
        tick.join(timeout=2)

        assert not errors
        assert sorted(results) == [0, 10, 20, 30]
