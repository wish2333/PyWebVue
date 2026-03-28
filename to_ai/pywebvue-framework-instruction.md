# PyWebVue Framework -- AI Development Instruction

> This document provides complete, precise instructions for an AI agent to develop applications using the PyWebVue framework. It covers every module, every file, every pattern, and every constraint. When in doubt, refer to this document as the single source of truth.

---

## 1. Framework Overview

PyWebVue is a Python desktop application framework. It wraps [pywebview](https://pywebview.flowrl.com/) (native webview window) + [Vue 3](https://vuejs.org/) (frontend SPA) + [DaisyUI](https://daisyui.com/) (component library) into a cohesive development experience with CLI scaffolding, event communication, subprocess management, and PyInstaller packaging.

**Tech stack**: Python >= 3.10.8, Vue 3 + TypeScript, Tailwind CSS + DaisyUI 4, Vite 5, bun (package manager), PyInstaller (packaging).

**Repository structure**:

```
pywebvue-framework/
  pyproject.toml                          # Package metadata (name: pywebvue-framework)
  src/pywebvue/                           # Framework source (installed as package)
    __init__.py                           # Public exports
    app.py                                # App class (window lifecycle) + ApiProxy
    api_base.py                           # ApiBase (user subclass target)
    cli.py                                # CLI: pywebvue create / pywebvue build
    config.py                             # YAML -> AppConfig dataclass
    constants.py                          # __version__, path constants
    dialog.py                             # Native file/folder/save dialogs
    event_bus.py                          # BRIDGE_JS + EventBus (Python->JS)
    logger.py                             # Dual-channel logging (console + frontend)
    process.py                            # ProcessManager (subprocess state machine)
    result.py                             # Result dataclass + ErrCode constants
    singleton.py                          # Cross-platform single-instance lock
    templates/project/                    # Scaffold templates (.tpl files)
  examples/
    file-tool/                            # Example: file drag-drop + metadata + processing
    process-tool/                         # Example: subprocess management
  docs/
    user-guide.md                         # End-user guide
    development-guide.md                  # Developer guide (with examples)
  to_ai/                                  # This directory
```

---

## 2. Creating a New Project

```bash
pywebvue create <name> --title "Title" --width 1024 --height 768 --force
```

The CLI walks `src/pywebvue/templates/project/`, processes `.tpl` files (string substitution), and copies static files. Template variables use `{{UPPER_CASE}}` format.

After scaffolding:
```bash
cd <name>
uv sync                   # Install Python deps
cd frontend && bun install  # Install JS deps
cd ..
uv run python main.py --with-vite  # Start developing
```

---

## 3. Backend Development (Python)

### 3.1 ApiBase Subclass (`app.py`)

This is the primary file for business logic. Every PyWebVue project has exactly one `ApiBase` subclass that the framework auto-discovers from `app.py`.

```python
from pywebvue import ApiBase, Result, ErrCode

class MyAppApi(ApiBase):
    """Every public method (no _ prefix) is exposed to the frontend."""

    def health_check(self) -> Result:
        return Result.ok(data={"status": "running"})
```

**Critical rules**:
- The class MUST be named `*Api` and MUST subclass `ApiBase`
- ALL public methods MUST return `Result`
- Method parameters MUST be JSON-serializable types only: `str`, `int`, `float`, `bool`, `list`, `dict`, `None`. No `Path`, `datetime`, `bytes`, custom objects.
- If a method raises an uncaught exception, `ApiProxy` catches it and returns `Result.fail(ErrCode.INTERNAL_ERROR, detail=str(e))`. The frontend always receives `{ code, msg, data }`.

### 3.2 Result Pattern

```python
# Success with data
return Result.ok(data={"key": "value"})

# Success with no data
return Result.ok()

# Error with detail
return Result.fail(ErrCode.PARAM_INVALID, detail="Email cannot be empty")

# Error with detail (detail is placed in data.detail)
return Result.fail(ErrCode.FILE_NOT_FOUND, detail="/path/to/missing.txt")
```

`Result` is a dataclass with fields: `code: int`, `msg: str`, `data: Any`. Call `result.to_dict()` for JSON serialization (done automatically by `ApiProxy`).

### 3.3 ErrCode Constants

Built-in codes in `src/pywebvue/result.py`:

| Code | Name | When |
|------|------|------|
| 0 | `OK` | Success |
| 1 | `UNKNOWN` | Unknown error |
| 2 | `PARAM_INVALID` | Invalid parameter |
| 3 | `NOT_IMPLEMENTED` | Not implemented |
| 4 | `TIMEOUT` | Timeout |
| 5 | `INTERNAL_ERROR` | Internal error (auto for uncaught exceptions) |
| 1001 | `FILE_NOT_FOUND` | File does not exist |
| 1002 | `FILE_READ_ERROR` | File read failed |
| 1003 | `FILE_WRITE_ERROR` | File write failed |
| 1004 | `FILE_FORMAT_INVALID` | Unsupported format |
| 1005 | `FILE_TOO_LARGE` | File too big |
| 1006 | `PATH_NOT_ACCESSIBLE` | Path not accessible |
| 2001 | `PROCESS_START_FAILED` | Could not start subprocess |
| 2002 | `PROCESS_ALREADY_RUNNING` | Subprocess already active |
| 2003 | `PROCESS_NOT_RUNNING` | No active subprocess |
| 2004 | `PROCESS_TIMEOUT` | Subprocess timed out |
| 2005 | `PROCESS_KILLED` | Process was killed |
| 3001 | `API_CALL_FAILED` | Backend call failed |
| 3002 | `API_NOT_READY` | Backend not ready |

Custom codes: use >= 10000. Register messages in `ErrCode._MSG` dict.

### 3.4 Available Properties on ApiBase

```python
class MyAppApi(ApiBase):
    def some_method(self) -> Result:
        self.logger.info("message")       # loguru logger bound with class name
        self.emit("event:name", data)     # Push event to frontend
        self.dialog.open_file(...)        # Native file dialog
        self.config.title                 # AppConfig dataclass
        self.window                       # pywebview window (None before bind)
        self.run_in_thread(func, *args)   # Start daemon thread
```

### 3.5 Event Emission (Python -> Frontend)

```python
# Simple event
self.emit("notification", {"message": "Hello"})

# Progress event (consumed by ProgressBar component)
self.emit("progress:update", {"current": 5, "total": 10, "label": "Step 5/10"})

# Reset progress bar
self.emit("progress:update", {"current": 0, "total": 0})

# Log event (also works automatically via self.logger)
self.emit("log:add", {"level": "INFO", "message": "Something happened"})
```

Event names follow `module:action` convention. `emit()` calls `window.run_js()` internally (NOT `evaluate_js` -- see Section 13 for why) -- it is safe to call from any thread (pywebview queues JS evaluations on the GUI thread).

### 3.6 Background Tasks

```python
def start_processing(self) -> Result:
    self.run_in_thread(self._do_heavy_work, "arg1", "arg2")
    return Result.ok(data={"message": "Processing started"})

def _do_heavy_work(self, arg1: str, arg2: str) -> None:
    for i in range(100):
        time.sleep(0.1)
        self.emit("progress:update", {"current": i + 1, "total": 100})
    self.emit("work:complete", {"result": "done"})
```

**NEVER** do blocking work (file I/O, network calls, long computation) in a public API method -- it blocks the GUI thread and freezes the window. Always use `self.run_in_thread()`.

### 3.7 File Drop Handling

Override `on_file_drop` to handle files dragged onto the window:

```python
def on_file_drop(self, file_paths: list[str]) -> None:
    """Called from a background thread when files are dropped."""
    for path in file_paths:
        self.logger.info(f"Dropped: {path}")
        self.emit("file:dropped", {"path": path})
```

The framework handles DOM event registration (`_setup_drag_drop` in `app.py`), background threading, and calling this method. You just need to override it.

### 3.8 Native Dialogs

```python
# File open (single)
paths = self.dialog.open_file(
    title="Select File",
    file_types=("Text Files (*.txt)", "All Files (*.*)"),
)
# Returns: list[str] | None (None if cancelled)

# File open (multiple)
paths = self.dialog.open_file(multiple=True)

# Folder select
folders = self.dialog.open_folder(title="Select Output")

# Save as
paths = self.dialog.save_file(
    title="Save As",
    default_name="output.csv",
    file_types=("CSV (*.csv)",),
)
```

### 3.9 Logging

```python
self.logger.info("User clicked button")           # Standard info
self.logger.warning("Retry attempt 3/5")           # Warning (yellow in LogPanel)
self.logger.error("Connection failed")              # Error (red in LogPanel)
self.logger.opt(exception=True).error("Crash")      # Include full traceback
```

Logs are automatically forwarded to the frontend LogPanel when `logging.to_frontend: true` in config. The level filter in LogPanel applies client-side.

### 3.10 Accessing Configuration

```python
def get_settings(self) -> Result:
    return Result.ok(data={
        "title": self.config.title,
        "width": self.config.width,
        "timeout": self.config.process.default_timeout,
        "custom": self.config.business.get("my_key", "default"),
    })
```

---

## 4. ProcessManager

### 4.1 Initialization

```python
from pywebvue import ProcessManager

class MyAppApi(ApiBase):
    def __init__(self):
        super().__init__()
        self.pm = ProcessManager(self, name="worker")
        # For multiple independent subprocesses:
        # self.encoder = ProcessManager(self, name="encoder")
        # self.uploader = ProcessManager(self, name="uploader")
```

### 4.2 State Machine

```
IDLE -> start() -> RUNNING
RUNNING -> pause() -> PAUSED
PAUSED -> resume() -> RUNNING
RUNNING -> stop() -> STOPPED
PAUSED -> stop() -> STOPPED
STOPPED -> reset() -> IDLE
STOPPED -> start() -> RUNNING (auto-reset)
```

Properties: `state`, `is_running`, `is_paused`, `pid`, `timeout_remaining`, `name`

### 4.3 Start with Timeout

```python
result = self.pm.start(
    cmd=["python", "task.py", "--input", "data.csv"],
    cwd="/path/to/working/dir",
    on_output=lambda line: self.logger.info(f"[task] {line}"),
    on_complete=lambda rc: self.logger.info(f"Task exited: {rc}"),
    timeout=60,  # seconds. None = use config.process.default_timeout
)
```

`cmd` MUST be a `list[str]`, not a single string. Use `shlex.split(cmd_string)` to parse.

### 4.4 Pause / Resume / Stop / Reset

```python
self.pm.pause()   # Suspends all process threads (NtSuspendProcess on Win, SIGSTOP on Unix)
self.pm.resume()  # Resumes (NtResumeProcess / SIGCONT)
self.pm.stop()    # terminate(), then kill() after 5s if not exited
self.pm.reset()   # STOPPED -> IDLE (allows re-start)
```

### 4.5 Events Emitted by ProcessManager

| Event | Payload | When |
|-------|---------|------|
| `process:{name}:output` | `{"line": "stdout line"}` | Each stdout/stderr line |
| `process:{name}:complete` | `{"returncode": 0}` | Process exits (naturally or killed) |
| `process:{name}:timeout` | `{"timeout": 60}` | Timer fired, process auto-stopped |

---

## 5. Frontend Development (TypeScript + Vue 3)

### 5.1 Project Layout

```
frontend/src/
  main.ts               # createApp(App).mount("#app")
  App.vue               # Root component
  api.ts                # waitForReady() + call<T>()
  event-bus.ts          # useEvent() + waitForEvent<T>()
  types/index.ts        # ErrCode, ApiResult<T>, isOk(), interfaces
  env.d.ts              # Global type declarations (window.pywebvue, etc.)
  assets/style.css      # Tailwind directives + html/body/#app height:100%
  components/           # Vue SFC components
```

### 5.2 Path Alias

`@/` maps to `frontend/src/` (configured in `vite.config.ts` and `tsconfig.json`).

```typescript
import { call } from "@/api";
import { useEvent } from "@/event-bus";
import { isOk, ErrCode } from "@/types";
import type { LogEntry, ProgressPayload, ToastOptions } from "@/types";
```

### 5.3 Global Type Declarations (env.d.ts)

```typescript
// window.pywebvue.event.on/off -- event bus
// window.pywebview.api -- JS bridge to Python methods
// window.__pywebvue_dispatch -- internal dispatch function
```

### 5.4 Calling Backend Methods

```typescript
import { call } from "@/api";
import { isOk } from "@/types";

// With type parameter (result.data is typed)
const result = await call<{ name: string; age: number }>("get_user", 42);

if (isOk(result)) {
  // result.data is { name: string; age: number }
  console.log(result.data.name);
} else {
  // result.code != 0, result.msg has error message
  // result.data may contain { detail: "..." }
  console.error(result.msg);
}

// Without type parameter (result.data is unknown)
const health = await call("health_check");
```

### 5.5 Event Subscriptions

```typescript
import { useEvent } from "@/event-bus";

// Auto-subscribe on mount, auto-unsubscribe on unmount
useEvent("log:add", (data) => {
  const entry = data as LogEntry;
  console.log(`[${entry.level}] ${entry.message}`);
});

useEvent("progress:update", (data) => {
  progress.value = data as ProgressPayload;
});

// One-time wait with timeout (returns Promise)
import { waitForEvent } from "@/event-bus";
const result = await waitForEvent<{ path: string }>("file:complete", 60000);
```

### 5.6 Backend Readiness

```typescript
import { waitForReady } from "@/api";

onMounted(async () => {
  try {
    await waitForReady();
    backendReady.value = true;
    // Now safe to call backend methods
  } catch {
    // Running outside pywebview (e.g., bun dev without Python)
    backendReady.value = false;
  }
});
```

### 5.7 Toast Notification Pattern

```typescript
// Setup in App.vue
let _toastId = 0;
const toastQueue = reactive<ToastOptions[]>([]);

function showToast(options: ToastOptions) {
  toastQueue.push({ ...options, id: ++_toastId });
}

function removeToast(index: number) {
  toastQueue.splice(index, 1);
}

provide("toast", { showToast });
provide("removeToast", removeToast);
```

```vue
<Toast :items="toastQueue" @dismiss="removeToast" />
```

```typescript
showToast({ type: "success", message: "Saved!" });
showToast({ type: "error", message: "Failed" });
showToast({ type: "warning", message: "Disk full" });
showToast({ type: "info", message: "Update available" });
```

### 5.8 Component Conventions

- Use `<script setup lang="ts">` (Composition API only)
- Props via `defineProps<{ ... }>()`
- Events via `defineEmits<{ ... }>()`
- Use DaisyUI utility classes: `btn`, `card`, `badge`, `alert`, `table`, `navbar`, `footer`, `mockup-code`, etc.
- Color variants: `btn-primary`, `btn-error`, `badge-success`, `alert-warning`, etc.
- Size variants: `btn-sm`, `btn-xs`, `badge-sm`, `select-xs`, `text-xs`, etc.
- Layout: `flex`, `flex-col`, `h-screen`, `overflow-auto`, `p-4`, `gap-2`, `space-y-4`

---

## 6. Pre-built Components

### Toast

File: `components/Toast.vue`

| Prop | Type | Description |
|------|------|-------------|
| `items` | `ToastOptions[]` | Toast messages to display |

| Event | Type | Description |
|-------|------|-------------|
| `dismiss` | `index: number` | Toast dismissed (auto or manual) |

Auto-dismisses after 4 seconds. Rendered via `<Teleport to="body">`. Watcher watches `props.items` reference (not length) for robust change detection.

### LogPanel

File: `components/LogPanel.vue`

No props or events. Self-contained component that subscribes to `log:add` events.

Features: level filter (ALL/DEBUG/INFO/WARNING/ERROR/CRITICAL), auto-scroll checkbox, clear button, max 500 entries, color-coded levels.

### ProgressBar

File: `components/ProgressBar.vue`

| Prop | Type | Description |
|------|------|-------------|
| `progress` | `ProgressPayload \| null` | Progress data. `null` = idle state. |

```typescript
interface ProgressPayload {
  current: number;
  total: number;
  label?: string;
}
```

Color logic: < 50% warning, 50-99% primary, 100% success. To reset: set to `null` or emit `{current: 0, total: 0}`.

### StatusBadge

File: `components/StatusBadge.vue`

| Prop | Type | Description |
|------|------|-------------|
| `status` | `"idle" \| "running" \| "paused" \| "error" \| "done"` | State |

Badge colors: idle=ghost, running=primary, paused=warning, error=error, done=success.

### FileDrop

File: `components/FileDrop.vue`

No required props. Listens to `file:dropped` events and shows dropped file paths. Requires `toast` inject for the Browse button fallback message.

### DataTable

File: `components/DataTable.vue`

| Prop | Type | Description |
|------|------|-------------|
| `columns` | `ColumnDef[]` | Column definitions |
| `rows` | `Record<string, unknown>[]` | Data rows |
| `emptyText` | `string` | Text when no rows (default: "No data") |

```typescript
interface ColumnDef {
  key: string;
  label: string;
  width?: string;
}
```

---

## 7. TypeScript Types (types/index.ts)

```typescript
// Error codes (must match Python ErrCode class exactly)
export const ErrCode = {
  OK: 0, UNKNOWN: 1, PARAM_INVALID: 2, NOT_IMPLEMENTED: 3,
  TIMEOUT: 4, INTERNAL_ERROR: 5,
  FILE_NOT_FOUND: 1001, FILE_READ_ERROR: 1002, FILE_WRITE_ERROR: 1003,
  FILE_FORMAT_INVALID: 1004, FILE_TOO_LARGE: 1005, PATH_NOT_ACCESSIBLE: 1006,
  PROCESS_START_FAILED: 2001, PROCESS_ALREADY_RUNNING: 2002,
  PROCESS_NOT_RUNNING: 2003, PROCESS_TIMEOUT: 2004, PROCESS_KILLED: 2005,
  API_CALL_FAILED: 3001, API_NOT_READY: 3002,
} as const;

// API result shape
export interface ApiResult<T = unknown> {
  code: number;
  msg: string;
  data: T;
}

// Type guard
export function isOk<T>(result: ApiResult<T>): result is ApiResult<T> & { code: 0 };

// Log entry from backend
export interface LogEntry {
  id?: number;
  level: string;
  message: string;
  timestamp?: string;
  class_name?: string;
}

// Progress bar data
export interface ProgressPayload {
  current: number;
  total: number;
  label?: string;
}

// Toast notification
export interface ToastOptions {
  id: number;
  type: "success" | "error" | "warning" | "info";
  message: string;
  duration?: number;
}

// Data table column
export interface ColumnDef {
  key: string;
  label: string;
  width?: string;
}

// Status badge state
export type StatusState = "idle" | "running" | "paused" | "error" | "done";
```

When adding custom error codes or types, mirror them in BOTH `types/index.ts` (TypeScript) and the Python `ErrCode` class.

---

## 8. Configuration (config.yaml)

```yaml
app:
  name: "my_app"             # Python identifier (no hyphens, must be valid Python)
  title: "My App"            # Window title
  width: 900                 # Initial width (px)
  height: 650                # Initial height (px)
  min_size: [600, 400]       # [width, height]
  max_size: [1920, 1080]     # [width, height]
  resizable: true            # Allow resize
  icon: "assets/icon.ico"    # Relative to project root
  singleton: false           # Cross-platform file lock
  centered: true             # Center on screen
  theme: light               # DaisyUI theme name

  dev:
    enabled: true            # Check for Vite dev server
    vite_port: 5173          # Port to check
    debug: true              # pywebview debug (DevTools)

logging:
  level: INFO                # loguru level string
  console: true              # Print to stderr
  to_frontend: true          # Forward to LogPanel via EventBus
  file: ""                   # File path (empty = disabled)
  max_lines: 1000            # Max buffer for frontend

process:
  default_timeout: 300       # Seconds (used by ProcessManager.start)

business: {}                 # Arbitrary key-value for user config
```

Access in Python: `self.config.title`, `self.config.business["key"]`.

---

## 9. PyInstaller Packaging

### CLI

```bash
uv run pywebvue build [--mode onedir|onefile|debug] [--spec PATH] [--skip-frontend]
                     [--clean] [--icon PATH] [--output-dir PATH]
```

### Spec Files

Three spec templates are generated during scaffolding:
- `{name}.spec` -- onedir (folder output, default)
- `{name}-onefile.spec` -- single executable
- `{name}-debug.spec` -- console window visible

Spec files include user customization sections (`EXTRA_DATAS`, `EXTRA_BINARIES`, `EXTRA_HIDDEN_IMPORTS`, `EXTRA_EXCLUDES`) that are preserved across regenerations.

### Build Flow

1. (optional) `--clean` removes `build/` and `dist/`
2. `bun run build` in `frontend/` (unless `--skip-frontend`)
3. `pyinstaller --noconfirm {name}.spec`
4. Output in `dist/`

---

## 10. Common Patterns and Idioms

### 10.1 Standard App.vue Structure

```vue
<script setup lang="ts">
import { ref, reactive, onMounted, provide } from "vue";
import { waitForReady, call } from "@/api";
import { useEvent } from "@/event-bus";
import { isOk } from "@/types";
import type { ToastOptions, ProgressPayload } from "@/types";
// Import pre-built components
import Toast from "@/components/Toast.vue";
import LogPanel from "@/components/LogPanel.vue";

const backendReady = ref(false);
const progress = ref<ProgressPayload | null>(null);

// Toast system
let _toastId = 0;
const toastQueue = reactive<ToastOptions[]>([]);
function showToast(options: ToastOptions) { toastQueue.push({ ...options, id: ++_toastId }); }
function removeToast(index: number) { toastQueue.splice(index, 1); }
provide("toast", { showToast });

// Event subscriptions
useEvent("log:add", (data) => { console.log(data); });
useEvent("progress:update", (data) => { progress.value = data as ProgressPayload; });

// Lifecycle
onMounted(async () => {
  try { await waitForReady(); backendReady.value = true; }
  catch { backendReady.value = false; }
});
</script>

<template>
  <Toast :items="toastQueue" @dismiss="removeToast" />
  <div class="flex flex-col h-screen bg-base-200">
    <nav class="navbar bg-base-100 shadow-md px-4">
      <div class="flex-1"><span class="text-lg font-bold">Title</span></div>
      <span class="badge" :class="backendReady ? 'badge-success' : 'badge-warning'">
        {{ backendReady ? "Connected" : "Connecting..." }}
      </span>
    </nav>
    <main class="flex-1 overflow-auto p-4">
      <div class="max-w-4xl mx-auto space-y-4">
        <!-- Your content here -->
        <LogPanel />
      </div>
    </main>
  </div>
</template>
```

### 10.2 Standard Layout Pattern

```
+--navbar (bg-base-100 shadow-md)-------+
|  Title           [StatusBadge] [Badge] |
+----------------------------------------+
|                                        |
|  main (flex-1 overflow-auto p-4)       |
|    max-w-4xl mx-auto space-y-4         |
|    <card> / <card> / <LogPanel>        |
|                                        |
+----------------------------------------+
|  footer (bg-base-100 text-xs)          |
+----------------------------------------+
```

### 10.3 Error Display Pattern

```typescript
async function doSomething() {
  const result = await call("some_method", arg1, arg2);
  if (isOk(result)) {
    // Use result.data
    showToast({ type: "success", message: "Done" });
  } else {
    showToast({ type: "error", message: result.msg });
  }
}
```

### 10.4 Polling vs Event-Driven

**Prefer events** (push) over polling (pull):

```typescript
// GOOD: Event-driven
useEvent("process:state_changed", (data) => { /* update UI */ });

// AVOID: Polling
setInterval(async () => {
  const status = await call("get_status");
  // ...
}, 1000);
```

### 10.5 Adding Custom Components

Place custom components in `frontend/src/components/`. They can coexist with pre-built components. Use the same imports (`@/types`, `@/event-bus`, `@/api`) for consistency.

---

## 11. Constraints and Anti-Patterns

### DO

- Return `Result` from every public method
- Use `self.run_in_thread()` for blocking operations
- Use `self.emit()` for async notifications
- Use `waitForReady()` before API calls
- Use `isOk()` type guard before accessing `result.data`
- Use DaisyUI classes (no custom CSS unless necessary)
- Use `@/` path alias for imports
- Use TypeScript strict mode (already configured)

### DO NOT

- Block the GUI thread (no `time.sleep()` in public methods, no synchronous file I/O)
- Return `Path`, `datetime`, `bytes`, or custom objects from public methods
- Call `evaluate_js()` or `run_js()` directly -- use `self.emit()` instead
- Create multiple `ApiBase` subclasses in one project
- Use `pywebview` API directly -- go through `ApiBase` / `App`
- Use `npm` instead of `bun` (template `package.json` scripts use `bun`)
- Add emoji characters to Python code (terminal rendering issues)

---

## 12. CLI Reference

### `pywebvue create`

```
pywebvue create <project_name> [--title TITLE] [--width N] [--height N] [--force]
```

| Argument | Required | Description |
|----------|----------|-------------|
| `project_name` | Yes | Valid Python identifier (snake_case) |
| `--title` | No | Window title (default: derived from name) |
| `--width` | No | Window width (default: 900) |
| `--height` | No | Window height (default: 650) |
| `--force` | No | Overwrite existing directory with confirmation |

### `pywebvue build`

```
pywebvue build [--mode MODE] [--spec PATH] [--skip-frontend] [--clean] [--icon PATH] [--output-dir PATH]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--mode` | `onedir` | `onedir`, `onefile`, or `debug` |
| `--spec` | auto | Custom .spec file path |
| `--skip-frontend` | false | Skip `bun run build` |
| `--clean` | false | Remove `build/` and `dist/` |
| `--icon` | from config | Icon file path (.ico) |
| `--output-dir` | auto | Custom output directory |

---

## 13. File-by-File Reference for Scaffolded Projects

| File | Edit? | Purpose |
|------|-------|---------|
| `main.py` | Rarely | `App(config="config.yaml").run()` |
| `app.py` | Always | Business logic (ApiBase subclass) |
| `config.yaml` | Often | Window, logging, theme, process settings |
| `pyproject.toml` | Sometimes | Python dependencies |
| `{name}.spec` | Sometimes | PyInstaller customization (EXTRA_DATAS etc.) |
| `frontend/index.html` | Rarely | Set `data-theme`, title |
| `frontend/src/App.vue` | Always | Root layout, toast, event wiring |
| `frontend/src/types/index.ts` | Often | Custom TypeScript types + error codes |
| `frontend/src/components/*.vue` | Sometimes | Pre-built components (usually don't edit) |
| `frontend/src/api.ts` | Rarely | Helper for calling backend |
| `frontend/src/event-bus.ts` | Rarely | Helper for event subscriptions |
| `frontend/src/main.ts` | Never | Vue app bootstrap |
| `frontend/src/env.d.ts` | Rarely | Global type declarations |
| `frontend/src/assets/style.css` | Rarely | Tailwind directives |
| `frontend/vite.config.ts` | Rarely | Vite config (outDir: ../dist) |
| `frontend/tailwind.config.ts` | Sometimes | Add DaisyUI themes |

---

## 14. pywebview 6.x Compatibility (Critical Knowledge)

PyWebVue targets pywebview 6.x (EdgeChromium on Windows). The framework contains **mandatory workarounds** for several pywebview 6.x bugs. When modifying framework code or debugging issues, keep these in mind:

### 14.1 NEVER use `evaluate_js` -- always use `run_js`

**Bug:** pywebview 6.1 EdgeChromium's `evaluate_js()` internally calls `json.loads(task.Result)`. When the JS script returns `undefined` (no return value), `json.loads` throws `JSONDecodeError`, and the **entire script execution is silently dropped** -- no error, no warning, nothing.

**Rule:** Use `window.run_js(script)` instead of `window.evaluate_js(script)`. The difference: `run_js` passes `parse_json=False` internally, avoiding the JSON parsing bug.

**Framework locations where this matters:**
- `EventBus.emit()` in `event_bus.py` -- dispatches events via `run_js`
- `ApiBase.bind_window()` in `api_base.py` -- injects `BRIDGE_JS` via `run_js`
- `App._setup_drag_drop()` in `app.py` -- injects drag-drop handlers via `run_js`
- `App._patch_element_on()` in `app.py` -- monkeypatches `Element.on()` to use `run_js`

### 14.2 ApiProxy must return bound methods via `types.MethodType`

**Bug:** pywebview 6.x discovers API methods by calling `dir()` on the `js_api` object, then `inspect.ismethod(attr)` on each attribute. A plain function from `__getattr__` fails this check and is silently skipped, making all API methods invisible to `window.pywebview.api`.

**Rule:** `ApiProxy.__getattr__` wraps callbacks with `types.MethodType(wrapper, self)` and the wrapper accepts `self_bound` as its first parameter (discarded internally).

### 14.3 BRIDGE_JS must never overwrite existing frontend state

**Bug:** The frontend's `ensureBridge()` in `event-bus.ts` may initialize the bridge before Python's injection. If `BRIDGE_JS` does `window.__pywebvue_event_listeners = {}`, it wipes out all registered listeners.

**Rule:** `BRIDGE_JS` uses `|| {}` and `if (!...)` guards.

### 14.4 `pywebviewready` is on `window`, NOT `document`

**Bug:** pywebview dispatches `new CustomEvent('pywebviewready')` on `window`.

**Rule:** Frontend `waitForReady()` uses `window.addEventListener(...)`.

### 14.5 Do NOT use `element.events.xxx` for drag-drop

**Bug:** `Element.__generate_events()` uses `evaluate_js` (fails silently) and is additionally blocked by `@_ignore_window_document` for document elements. So `element.events.dragover` etc. never exist.

**Rule:** Drag-drop handlers are injected directly via `run_js` using `document.addEventListener()`.

### 14.6 Dialog params must never be `None`

**Bug:** pywebview's `create_file_dialog()` calls `os.path.exists(None)` which crashes.

**Rule:** `Dialog` methods pass `""` (empty string) and `()` (empty tuple) instead of `None`.

### 14.7 Frontend must self-initialize the bridge

**Rule:** The `ensureBridge()` function in `event-bus.ts` must create `window.__pywebvue_dispatch`, `window.__pywebvue_event_listeners`, and `window.pywebvue.event` independently, since the Python injection timing is non-deterministic relative to Vue's lifecycle.
