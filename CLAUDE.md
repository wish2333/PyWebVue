# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PyWebVue is a minimal Python + Vue 3 bridge framework built on [pywebview](https://github.com/r0x0r/pywebview). It provides bidirectional communication between a Python backend and a Vue 3 frontend inside a native desktop window. The framework core is intentionally tiny (~200 lines Python).

## Commands

### Development
```bash
uv run dev.py              # Start Vite dev server + pywebview window (default mode)
uv run dev.py --no-vite    # Load frontend_dist/ from disk (production preview)
uv run dev.py --setup      # Only install dependencies
```

### Frontend
```bash
cd frontend && bun run dev       # Vite dev server alone (port 5173, strictPort)
cd frontend && bun run build     # Build Vue app -> ../frontend_dist/
```

### Production Build
```bash
uv run build.py              # Desktop onedir bundle (PyInstaller)
uv run build.py --onefile    # Desktop single exe
uv run build.py --clean      # Remove build/ and dist/
```

## Architecture

### Communication Flow

```
Vue frontend  --call()-->  window.pywebview.api.method()  -->  @expose Python method
Vue frontend  <--onEvent()--  CustomEvent("pywebvue:name") <--  Bridge._emit()
```

- **Frontend -> Python**: `call<T>(method, ...args)` invokes `@expose`-decorated methods via pywebview's `js_api`. All responses follow `ApiResponse<T> = { success: boolean, data?: T, error?: string, code?: string }`.
- **Python -> Frontend**: `Bridge._emit(event, data)` queues events for delivery via `evaluate_js`. A recursive `setTimeout` calls `tick()` to flush the queue. This is required because Windows WebView2 requires `evaluate_js` on the main thread.

### Core Files

- `pywebvue/bridge.py` -- `Bridge` base class + `@expose` decorator. Handles event queuing (`_emit`/`_flush_events`), bridge-thread task execution (`register_handler`/`run_on_bridge`), drag-and-drop, and the periodic `tick` that drives both. Event names are validated against `^[A-Za-z0-9_.:-]{1,128}$`.
- `pywebvue/app.py` -- `App` class. Creates the pywebview window, resolves frontend path (dev URL vs built files vs PyInstaller bundle), sets up drag-and-drop and the tick timer.
- `frontend/src/bridge.ts` -- TypeScript side: `call()`, `onEvent()`, `waitForPyWebView()`.

### Key Patterns

- `@expose` wraps methods with try/except, always returning `{"success": bool, "data": ..., "error": ..., "code": ...}`. In production mode (default), error details are hidden from the frontend. Pass `Bridge(debug=True)` to see full error strings during development.
- `_emit()` is thread-safe (uses `queue.Queue`). Background threads can push events; `tick()` flushes them every `tick_interval` ms (default 50ms) via recursive `setTimeout` to prevent reentrancy. Event names are validated.
- `run_on_bridge(name, args)` schedules a named handler, blocking the caller until completion. Used for C++ extensions (e.g., ONNX Runtime) that require specific thread initialization. `run_on_main_thread` is deprecated but still works.
- Dev mode is auto-detected via `sys.frozen` -- when not frozen, the app connects to Vite dev server; when frozen (PyInstaller), it loads from `frontend_dist/`.
- Vite builds to `../frontend_dist/` (configured in `frontend/vite.config.ts`).

### Entry Point

`main.py` is the app entry point. It defines a `Bridge` subclass with `@expose` methods and passes it to `App()`. This is what users edit to build their application.

## Conventions

- All `@expose` methods must return `dict[str, Any]` with `success` key.
- Use `uv run` for all Python execution (no bare `python`).
- Frontend package manager: bun preferred, npm fallback.
- Python >= 3.10, Vue 3 Composition API (`<script setup>`), TypeScript ~5.7, Vite ^6.0.
