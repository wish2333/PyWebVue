---
name: pywebvue-framework.skill
description: Create, scaffold, and develop PyWebVue desktop applications (PyWebView + Vue 3 + DaisyUI). Covers backend API methods, frontend components, event communication, subprocess management, configuration, and PyInstaller packaging.
---

# PyWebVue Framework Development Skill

## Quick Reference

```bash
# Scaffold new project
pywebvue create <project_name> --title "Title" --width 1024 --height 768

# Run development
uv run python main.py              # Connect to running Vite
uv run python main.py --with-vite  # Auto-start Vite

# Build for distribution
uv run pywebvue build                    # onedir (default)
uv run pywebvue build --mode onefile     # single exe
uv run pywebvue build --clean            # wipe build/ dist/ first
uv run pywebvue build --icon path.ico --output-dir ./out

# Frontend
cd frontend && bun install && bun dev     # dev server with HMR
cd frontend && bun run build              # production build to ../dist/
```

## Architecture

```
Python (ApiBase subclass) <--pywebview JS bridge--> Vue 3 (TypeScript + DaisyUI)
```

- **Backend**: `app.py` -- subclass `ApiBase`, define public methods returning `Result`
- **Frontend**: `frontend/src/` -- Vue 3 SFC, call backend via `call<T>(method, ...args)`, listen via `useEvent(name, cb)`
- **Bridge**: `ApiProxy` wraps all public methods with global exception interception; `EventBus` pushes events Python->JS via `evaluate_js`

## Core Rules

### Python Backend

1. ALL public methods (no `_` prefix) are auto-exposed to frontend via pywebview JS bridge
2. ALL public methods MUST return `Result` (from `pywebvue.result`)
3. Parameters MUST be JSON-serializable: `str`, `int`, `float`, `bool`, `list`, `dict`, `None`
4. Uncaught exceptions are caught by `ApiProxy` -> returned as `Result.fail(ErrCode.INTERNAL_ERROR, detail=str(e))`
5. Use `self.run_in_thread(func, *args)` for long-running work (never block the GUI thread)
6. Use `self.emit("event:name", data_dict)` to push events to frontend
7. Use `self.logger.info/warning/error(msg)` for logging (auto-forwarded to frontend LogPanel)
8. Override `on_file_drop(self, file_paths: list[str])` to handle drag-and-drop files

### TypeScript Frontend

1. Use `call<T>(method, ...args)` from `@/api` to call backend (returns `ApiResult<T>`)
2. Use `isOk(result)` type guard from `@/types` to check success
3. Use `useEvent(name, cb)` from `@/event-bus` to subscribe (auto-cleanup on unmount)
4. Always `await waitForReady()` in `onMounted()` before making API calls
5. Use DaisyUI component classes (`btn`, `card`, `badge`, `table`, etc.) -- no raw CSS
6. Path alias: `@/` maps to `frontend/src/`

### Project Files

```
app.py                # Business API (subclass ApiBase)
config.yaml           # App configuration
main.py               # Entry: App(config="config.yaml").run()
frontend/src/App.vue  # Root component
frontend/src/types/index.ts  # ErrCode + ApiResult<T> + interfaces
```

## Result Pattern

```python
from pywebvue import ApiBase, Result, ErrCode

class MyApi(ApiBase):
    def get_user(self, user_id: int) -> Result:
        user = db.find(user_id)
        if not user:
            return Result.fail(ErrCode.PARAM_INVALID, detail=f"User {user_id} not found")
        return Result.ok(data={"id": user.id, "name": user.name})
```

```typescript
import { call } from "@/api";
import { isOk } from "@/types";

const result = await call<{ id: number; name: string }>("get_user", 42);
if (isOk(result)) {
  console.log(result.data.name);
} else {
  console.error(result.msg);
}
```

## Event Pattern

```python
# Python: push event
self.emit("progress:update", {"current": 5, "total": 10, "label": "Processing..."})

# Python: background task
def start_work(self) -> Result:
    self.run_in_thread(self._do_work)
    return Result.ok()

def _do_work(self) -> None:
    for i in range(10):
        time.sleep(1)
        self.emit("progress:update", {"current": i + 1, "total": 10})
    self.emit("work:complete", {})
```

```typescript
// TypeScript: subscribe
import { useEvent } from "@/event-bus";
useEvent("progress:update", (data) => { /* handle */ });
useEvent("work:complete", () => { /* handle */ });
```

## ProcessManager

```python
from pywebvue import ProcessManager

self.pm = ProcessManager(self, name="worker")
self.pm.start(cmd=["python", "task.py"], timeout=60)
self.pm.pause() / .resume() / .stop() / .reset()
```

Events: `process:{name}:output`, `process:{name}:complete`, `process:{name}:timeout`

## Pre-built Components

| Component | Purpose | Key Props |
|-----------|---------|-----------|
| `FileDrop` | Drag-and-drop file zone | (requires toast inject) |
| `LogPanel` | Real-time log viewer | (self-contained, auto-subscribes) |
| `ProgressBar` | Progress bar + percentage | `progress: ProgressPayload \| null` |
| `StatusBadge` | State indicator badge | `status: "idle"\|"running"\|"paused"\|"error"\|"done"` |
| `DataTable` | Data table with columns | `columns: ColumnDef[]`, `rows: Record[]` |
| `Toast` | Auto-dismissing notifications | `items: ToastOptions[]`, `@dismiss` |

## Config (config.yaml)

```yaml
app:
  name: "my_app"           # Python identifier
  title: "My App"          # Window title
  width: 900 / height: 650
  min_size: [600, 400]
  icon: "assets/icon.ico"
  singleton: false          # Single-instance lock
  theme: light              # DaisyUI theme (set data-theme in index.html)
  dev:
    enabled: true           # Auto-detect Vite dev server
    vite_port: 5173
    debug: true
logging:
  level: INFO
  to_frontend: true         # Forward to LogPanel
  file: ""                  # Log file (empty=disabled)
process:
  default_timeout: 300      # Subprocess timeout (seconds)
business: {}                # Custom config (access via self.config.business)
```

## Error Codes

| Code | Constant | Usage |
|------|----------|-------|
| 0 | `OK` | Success |
| 2 | `PARAM_INVALID` | Invalid input |
| 4 | `TIMEOUT` | Timeout |
| 5 | `INTERNAL_ERROR` | Auto (uncaught exception) |
| 1001 | `FILE_NOT_FOUND` | File missing |
| 2001-2005 | `PROCESS_*` | Subprocess errors |
| 3001-3002 | `API_*` | Communication errors |
| 10000+ | (custom) | Application-specific |

## Template Variables

Scaffold uses `{{UPPER_CASE}}` placeholders (not Vue `{{ camelCase }}`):

`{{PROJECT_NAME}}`, `{{PROJECT_TITLE}}`, `{{CLASS_NAME}}`, `{{WIDTH}}`, `{{HEIGHT}}`
