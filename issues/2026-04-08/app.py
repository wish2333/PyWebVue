"""App class - creates pywebview window and manages the bridge lifecycle."""

from __future__ import annotations

import sys
from pathlib import Path

import webview

from pywebvue.bridge import Bridge


def _resolve_frontend_path(frontend_dir: str) -> Path:
    """Resolve the absolute path to the frontend directory.

    Handles three environments:

    * **PyInstaller --onefile**: resources live in ``sys._MEIPASS``.
    * **PyInstaller --onedir**: resources live beside the executable.
    * **Development**: uses the given ``frontend_dir`` relative to CWD.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        # --onefile bundle
        return Path(sys._MEIPASS) / frontend_dir
    if getattr(sys, "frozen", False):
        # --onedir bundle
        return Path(sys.executable).parent / frontend_dir
    return Path(frontend_dir)


class App:
    """Create a pywebview window wired to a :class:`Bridge` instance.

    Usage::

        from pywebvue import App, Bridge, expose

        class MyApi(Bridge):
            @expose
            def greet(self, name: str) -> dict:
                return {"success": True, "data": f"Hello, {name}!"}

        App(MyApi(), title="Demo", width=800, height=600,
            frontend_dir=".").run(dev=True)
    """

    def __init__(
        self,
        bridge: Bridge,
        *,
        title: str = "App",
        width: int = 1200,
        height: int = 960,
        min_size: tuple[int, int] = (600, 400),
        frontend_dir: str = "frontend_dist",
        dev_url: str = "http://localhost:5173",
    ) -> None:
        self._bridge = bridge
        self._title = title
        self._width = width
        self._height = height
        self._min_size = min_size
        self._frontend_dir = frontend_dir
        self._dev_url = dev_url

    @property
    def dev(self) -> bool:
        """True when running inside PyInstaller bundle."""
        return not getattr(sys, "frozen", False)

    def emit(self, event: str, data=None) -> None:
        """Push an event to the frontend. See :meth:`Bridge._emit`."""
        self._bridge._emit(event, data)

    def run(self, dev: bool | None = None, *, debug: bool | None = None) -> None:
        """Create the window and start the event loop.

        Args:
            dev:   URL source. ``True`` = Vite dev server, ``False`` = disk,
                   ``None`` = auto-detect (dev when not frozen).
            debug: Open developer tools. ``True`` / ``False`` / ``None``
                   (default: True when not frozen).
        """
        is_dev = dev if dev is not None else self.dev
        show_debug = debug if debug is not None else self.dev

        if is_dev:
            url = self._dev_url
        else:
            base = _resolve_frontend_path(self._frontend_dir)
            url = str(base / "index.html")

        window = webview.create_window(
            self._title,
            url,
            width=self._width,
            height=self._height,
            min_size=self._min_size,
            js_api=self._bridge,
        )

        self._bridge._window = window

        # Set up native file drag-and-drop.
        self._setup_drag_drop(window)

        webview.start(debug=show_debug)

    def _setup_drag_drop(self, window) -> None:
        """Register a drop handler and start the event flush timer."""

        def on_loaded() -> None:
            from webview.dom import DOMEventHandler

            doc = window.dom.document
            handler = DOMEventHandler(self._bridge._on_drop, prevent_default=True)
            doc.on("drop", handler)

            # Start a periodic timer that flushes queued events from
            # background threads to the frontend via evaluate_js.
            # This keeps evaluate_js on the main thread (required by
            # WebView2/COM on Windows).
            window.evaluate_js(
                "setInterval(function() {"
                "  try { window.pywebview.api.flush_events(); }"
                "  catch(e) { console.error('flush_events error:', e); }"
                "}, 50);"
            )

            # Also start task executor that runs functions on the main thread
            # (required for thread-unsafe C++ extensions like ONNX Runtime).
            # Run less frequently (100ms) to reduce log spam.
            window.evaluate_js(
                "setInterval(function() {"
                "  try { window.pywebview.api.execute_task(); }"
                "  catch(e) { console.error('execute_task exception:', e); }"
                "}, 100);"
            )
            print("DEBUG: Task executor timers started")  # This goes to server console

        window.events.loaded += on_loaded
