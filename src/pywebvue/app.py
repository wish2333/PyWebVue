"""Application entry class - window lifecycle, configuration, and startup."""

from __future__ import annotations

import importlib.util
import inspect
import os
import sys
import threading
import types
import urllib.parse
import urllib.request
import urllib.error
from typing import Any

import webview
from loguru import logger

from .api_base import ApiBase
from .config import AppConfig, load_config
from .constants import DEFAULT_CONFIG_FILE, DEV_SERVER_HOST, DEFAULT_VITE_PORT, DIST_DIR, FRONTEND_ENTRY
from .logger import setup_logger, update_emit_callback
from .result import ErrCode, Result
from .singleton import SingletonLock


class ApiProxy:
    """Wraps an ApiBase instance to intercept all method calls for global exception handling.

    When a Python method raises an uncaught exception, pywebview propagates it
    as a rejected Promise to JavaScript. This proxy catches exceptions and
    returns a standard Result.fail() instead.
    """

    def __init__(self, api_instance: ApiBase) -> None:
        object.__setattr__(self, "_api", api_instance)

    def __dir__(self) -> list[str]:
        """Expose wrapped object's public methods so pywebview can discover them.

        pywebview 6.x uses dir() on the js_api object to enumerate methods
        for the JavaScript bridge.  Without __dir__, only the proxy's own
        dunders are returned and no API methods are visible to the frontend.
        """
        api = object.__getattribute__(self, "_api")
        own = [n for n in dir(type(self)) if not n.startswith("_")]
        delegated = [n for n in dir(api) if not n.startswith("_")]
        return sorted(set(own) | set(delegated))

    def __getattr__(self, name: str) -> Any:
        api = object.__getattribute__(self, "_api")
        attr = getattr(api, name)
        if not callable(attr):
            return attr

        def wrapper(self_bound: Any, *args: Any, **kwargs: Any) -> Any:
            try:
                result = attr(*args, **kwargs)
                # If the result is a Result dataclass, convert to dict for JSON serialization
                if isinstance(result, Result):
                    return result.to_dict()
                return result
            except Exception as e:
                api.logger.opt(exception=True).error(f"Uncaught exception in {name}: {e}")
                return Result.fail(ErrCode.INTERNAL_ERROR, detail=str(e)).to_dict()

        # Return as a bound method so that pywebview's inspect.ismethod() check passes.
        # pywebview 6.x uses inspect.ismethod(attr) to detect API functions;
        # plain functions returned from __getattr__ are skipped.
        # The first param (self_bound) receives the proxy instance from MethodType binding.
        return types.MethodType(wrapper, self)

    def __setattr__(self, name: str, value: Any) -> None:
        api = object.__getattribute__(self, "_api")
        setattr(api, name, value)


class App:
    """Main application class that manages the pywebview window lifecycle.

    Usage in user's main.py::

        from pywebvue import App

        app = App(config="config.yaml")
        app.run()
    """

    def __init__(
        self,
        config: str = DEFAULT_CONFIG_FILE,
        api_instance: ApiBase | None = None,
    ) -> None:
        # Load configuration
        self._config = load_config(config)

        # Setup logging
        setup_logger(self._config.logging, emit_callback=self._emit_callback)
        logger.info(f"PyWebVue app '{self._config.title}' starting")

        # Singleton lock
        if self._config.singleton:
            lock = SingletonLock(self._config.name)
            if not lock.acquire():
                logger.error(f"Another instance of '{self._config.name}' is already running")
                sys.exit(1)

        # Discover or use provided ApiBase
        self._api_instance = api_instance or self._discover_api()
        self._api_instance.bind_config(self._config)

        # Internal state
        self._window: Any = None
        self._vite_process: Any = None
        self._with_vite = "--with-vite" in sys.argv

    @property
    def config(self) -> AppConfig:
        return self._config

    def run(self) -> None:
        """Create the window and start the pywebview event loop."""
        url = self._determine_url()

        window_args: dict[str, Any] = {
            "title": self._config.title,
            "url": url,
            "width": self._config.width,
            "height": self._config.height,
            "resizable": self._config.resizable,
            "min_size": self._config.min_size,
            "js_api": ApiProxy(self._api_instance),
            "text_select": False,
        }

        self._window = webview.create_window(**window_args)

        # Patch pywebview's Element.on() to use run_js instead of evaluate_js.
        # In pywebview 6.x (EdgeChromium), evaluate_js silently fails for scripts
        # that return undefined, breaking all DOM event registration (drag, drop,
        # click, etc.). run_js avoids this by setting parse_json=False internally.
        self._patch_element_on()

        # Register lifecycle events
        self._window.events.loaded += self._on_window_loaded
        self._window.events.closing += self._on_window_closing

        # Start pywebview GUI loop (blocks until window is closed)
        webview.start(debug=self._config.dev.debug)

    def _determine_url(self) -> str:
        """Determine whether to use Vite Dev Server or production build."""
        # Auto-start Vite if --with-vite flag is passed
        if self._with_vite:
            self._start_vite_dev_server()

        if self._config.dev.enabled:
            vite_url = f"http://{DEV_SERVER_HOST}:{self._config.dev.vite_port}"
            if self._is_server_reachable(vite_url):
                logger.info(f"Dev mode: connecting to Vite at {vite_url}")
                return vite_url
            else:
                logger.warning(
                    f"Vite Dev Server not reachable at {vite_url}, falling back to production build"
                )

        # Production mode
        dist_path = os.path.abspath(os.path.join(DIST_DIR, FRONTEND_ENTRY))
        if not os.path.exists(dist_path):
            raise FileNotFoundError(
                f"Frontend build not found: {dist_path}\n"
                f"Run 'cd frontend && bun run build' first, or start Vite Dev Server."
            )
        logger.info(f"Production mode: loading {dist_path}")
        return dist_path

    @staticmethod
    def _is_server_reachable(url: str, timeout: int = 2) -> bool:
        """Check if a URL is reachable."""
        try:
            request = urllib.request.Request(url, method="GET")
            urllib.request.urlopen(request, timeout=timeout)
            return True
        except (urllib.error.URLError, OSError):
            return False

    def _start_vite_dev_server(self) -> None:
        """Start Vite Dev Server in a background process."""
        frontend_dir = os.path.join(os.getcwd(), "frontend")
        if not os.path.isdir(frontend_dir):
            logger.warning("frontend/ directory not found, cannot start Vite")
            return

        try:
            self._vite_process = __import__("subprocess").Popen(
                ["bun", "dev"],
                cwd=frontend_dir,
                stdout=__import__("subprocess").PIPE,
                stderr=__import__("subprocess").STDOUT,
            )
            logger.info(f"Vite Dev Server starting (PID {self._vite_process.pid})")

            # Wait for server to be ready
            import time
            vite_url = f"http://{DEV_SERVER_HOST}:{self._config.dev.vite_port}"
            for _ in range(30):  # Wait up to 15 seconds
                time.sleep(0.5)
                if self._is_server_reachable(vite_url):
                    logger.info("Vite Dev Server is ready")
                    return

            logger.warning("Vite Dev Server did not become ready in time")
        except FileNotFoundError:
            logger.warning("'bun' not found. Install bun or start Vite manually with 'cd frontend && bun dev'")

    def _emit_callback(self, event_name: str, data: Any = None) -> None:
        """Callback for the logger's frontend sink."""
        if self._window is None:
            return
        try:
            self._api_instance.emit(event_name, data)
        except Exception:
            pass

    def _on_window_loaded(self) -> None:
        """Called when the DOM is ready. Binds the window and injects the JS bridge."""
        logger.info("Window loaded, binding API instance")

        # Update the logger's emit callback now that the window is ready
        update_emit_callback(self._emit_callback)

        # Bind window to ApiBase (injects bridge JS, connects event bus + dialog)
        self._api_instance.bind_window(self._window)

        # Setup drag & drop
        try:
            self._setup_drag_drop()
        except Exception as e:
            logger.warning(f"Drag-drop setup failed: {e}")

    def _setup_drag_drop(self) -> None:
        """Register native drag-and-drop handlers directly via JS injection.

        Bypasses pywebview's DOM event API (Element.on / __generate_events)
        which relies on evaluate_js and silently fails in pywebview 6.x.
        Instead, injects plain JS event listeners via run_js and uses
        pywebview's native _jsApiCallback to extract full file paths.
        """
        from webview.dom import _dnd_state

        # Signal to pywebview that we have a drop listener so the native
        # EdgeChromium handler stores file paths in _dnd_state['paths'].
        _dnd_state['num_listeners'] += 1

        # Register the Python callback that pywebview's event handler will invoke
        doc_element = self._window.dom.document

        def on_drop(event: dict) -> None:
            files = event.get("dataTransfer", {}).get("files", [])
            paths = []
            for f in files:
                full_path = f.get("pywebviewFullPath")
                if full_path:
                    paths.append(full_path)
            if paths:
                threading.Thread(
                    target=self._api_instance.on_file_drop,
                    args=(paths,),
                    daemon=True,
                ).start()
                logger.info(f"Files dropped (drag-drop): {paths}")
            else:
                logger.warning(f"Drop event received but no file paths extracted: {list(files)}")

        # Store callback so pywebview's pywebviewEventHandler can find it
        if doc_element._node_id not in self._window.dom._elements:
            self._window.dom._elements[doc_element._node_id] = doc_element
        doc_element._event_handlers["drop"].append(on_drop)

        # Inject JS event listeners directly - no evaluate_js, no DOM API needed
        drop_js = """
            document.addEventListener('dragover', function(e) { e.preventDefault(); });
            document.addEventListener('dragenter', function(e) { e.preventDefault(); });
            document.addEventListener('drop', function(e) {
                e.preventDefault();
                e.stopPropagation();
                if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                    window.pywebview._jsApiCallback('pywebviewEventHandler', { event: e, nodeId: 'document' }, 'eventHandler');
                }
            });
        """
        self._window.run_js(drop_js)
        logger.info("Drag-drop handlers injected via run_js")

    @staticmethod
    def _patch_element_on() -> None:
        """Monkeypatch pywebview's Element.on() to use run_js instead of evaluate_js.

        In pywebview 6.x EdgeChromium, evaluate_js has a bug where
        json.loads(task.Result) throws for scripts returning undefined,
        silently dropping the execution. Element.on() uses evaluate_js
        to register JS event listeners and get back the handler_id.

        This patch generates handler_id in Python and uses run_js (which
        sets parse_json=False) for JS injection.
        """
        from webview.dom.element import Element
        from webview.dom import DOMEventHandler, _dnd_state

        _original_on = Element.on

        def _patched_on(self, event: str, callback: Any) -> None:
            if isinstance(callback, DOMEventHandler):
                prevent_default = 'e.preventDefault();' if callback.prevent_default else ''
                stop_propagation = 'e.stopPropagation();' if callback.stop_propagation else ''
                debounce = callback.debounce
                cb = callback.callback
            else:
                prevent_default = ''
                stop_propagation = ''
                debounce = 0
                cb = callback

            # Generate handler_id in Python (avoids needing evaluate_js return value)
            handler_id = os.urandom(8).hex()

            callback_func = (
                f"window.pywebview._jsApiCallback('pywebviewEventHandler', "
                f"{{ event: e, nodeId: '{self._node_id}' }}, 'eventHandler')"
            )
            debounced_func = (
                f"pywebview._debounce(function() {{ {callback_func} }}, {debounce})"
                if debounce > 0
                else callback_func
            )

            js_code = (
                f"{self._query_command};"
                f"if (element) {{"
                f"pywebview._eventHandlers['{handler_id}'] = function(e) {{"
                f"{prevent_default}{stop_propagation}{debounced_func};"
                f"}};"
                f"element.addEventListener('{event}', pywebview._eventHandlers['{handler_id}']);"
                f"}};"
            )

            self._window.run_js(js_code)

            if self._node_id not in self._window.dom._elements:
                self._window.dom._elements[self._node_id] = self

            self._event_handlers[event].append(cb)
            self._event_handler_ids[cb] = handler_id

            if event == 'drop':
                _dnd_state['num_listeners'] += 1

        Element.on = _patched_on  # type: ignore[assignment]

    def _on_window_closing(self) -> bool:
        """Called when the window is about to close. Cleanup resources."""
        # Disable frontend logging FIRST, before any logger.info() calls,
        # to prevent evaluate_js on a closing/dead window which hangs the GUI thread.
        update_emit_callback(None)

        logger.info("Window closing")

        # Stop Vite Dev Server if we started it
        if self._vite_process is not None:
            try:
                self._vite_process.terminate()
            except OSError:
                pass
            self._vite_process = None

        return True  # Confirm close

    @staticmethod
    def _discover_api() -> ApiBase:
        """Auto-discover and instantiate an ApiBase subclass from app.py.

        Scans the current working directory for app.py, imports it, and looks
        for classes that inherit from ApiBase. Returns the first one found,
        or an empty default ApiBase if none are found.
        """
        app_module_path = os.path.join(os.getcwd(), "app.py")
        if not os.path.exists(app_module_path):
            logger.info("No app.py found, using default ApiBase")
            return ApiBase()

        try:
            spec = importlib.util.spec_from_file_location("user_app", app_module_path)
            if spec is None or spec.loader is None:
                logger.warning("Failed to load app.py, using default ApiBase")
                return ApiBase()

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Find ApiBase subclasses
            candidates = []
            for _name, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, ApiBase) and obj is not ApiBase:
                    candidates.append(obj)

            if len(candidates) == 1:
                api_class = candidates[0]
                logger.info(f"Discovered ApiBase subclass: {api_class.__name__}")
                return api_class()
            elif len(candidates) > 1:
                names = ", ".join(c.__name__ for c in candidates)
                logger.warning(
                    f"Multiple ApiBase subclasses found in app.py: {names}. "
                    f"Using the first one: {candidates[0].__name__}"
                )
                return candidates[0]()
            else:
                logger.info("No ApiBase subclass found in app.py, using default")
                return ApiBase()

        except Exception as e:
            logger.error(f"Failed to load app.py: {e}")
            return ApiBase()
