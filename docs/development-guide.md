# PyWebVue Development Guide (with Examples)

> This guide walks through every capability of the PyWebVue framework by referencing the two bundled example projects. It is intended for **developers** who want to understand how the framework works and how to build real applications with it.

---

## Table of Contents

1. [Framework Architecture Overview](#1-framework-architecture-overview)
2. [Scaffolding and Project Layout](#2-scaffolding-and-project-layout)
3. [Example 1: file-tool -- Backend API Design](#3-example-1-file-tool----backend-api-design)
4. [Example 1: file-tool -- Frontend Implementation](#4-example-1-file-tool----frontend-implementation)
5. [Example 2: process-tool -- ProcessManager in Practice](#5-example-2-process-tool----processmanager-in-practice)
6. [Example 2: process-tool -- Real-time State Synchronization](#6-example-2-process-tool----real-time-state-synchronization)
7. [Frontend-Backend Communication Patterns](#7-frontend-backend-communication-patterns)
8. [Pre-built Components Deep Dive](#8-pre-built-components-deep-dive)
9. [Configuration System](#9-configuration-system)
10. [Advanced Topics](#10-advanced-topics)

---

## 1. Framework Architecture Overview

PyWebVue is a desktop application framework that combines three technologies:

```
Python Backend (ApiBase)  <--pywebview JS bridge-->  Vue 3 Frontend
       |                                                    |
  ProcessManager                                      DaisyUI Components
  EventBus / Logger                                   TypeScript + Vite
```

### Core Modules

| Module | File | Responsibility |
|--------|------|----------------|
| `App` | `app.py` | Window lifecycle, Vite integration, drag-drop setup |
| `ApiBase` | `api_base.py` | Base class for user business APIs |
| `ApiProxy` | `app.py` | Wraps ApiBase with global exception interception |
| `ProcessManager` | `process.py` | Subprocess state machine (start/pause/resume/stop/timeout) |
| `EventBus` | `event_bus.py` | Python-to-frontend event dispatch via `evaluate_js` |
| `Dialog` | `dialog.py` | Native file/folder/save dialogs |
| `Logger` | `logger.py` | Dual-channel logging (console + frontend LogPanel) |
| `Config` | `config.py` | YAML configuration loading into dataclasses |
| `SingletonLock` | `singleton.py` | Cross-platform single-instance lock |
| `Result` / `ErrCode` | `result.py` | Standardized API return type and error codes |

### Startup Flow

```
main.py
  -> App(config="config.yaml")
    -> load_config()        # Parse YAML into AppConfig
    -> setup_logger()       # Configure loguru (console + frontend sink)
    -> SingletonLock        # If singleton=true, acquire file lock
    -> _discover_api()      # Auto-import app.py, find ApiBase subclass
    -> bind_config()        # Pass config to ApiBase instance
    -> run()
      -> _determine_url()   # Vite dev server or production dist/
      -> webview.create_window(js_api=ApiProxy(api_instance))
      -> webview.start()
        -> _on_window_loaded()
          -> inject BRIDGE_JS    # window.pywebvue.event.on/off/dispatch
          -> _setup_drag_drop()  # DOM event handlers for file drops
```

The `ApiProxy` wraps every public method call. If the method raises an uncaught exception, the proxy catches it and returns `Result.fail(ErrCode.INTERNAL_ERROR)` instead of propagating a rejected Promise to JavaScript. This means frontend code can always rely on the `{ code, msg, data }` response shape.

---

## 2. Scaffolding and Project Layout

### Creating a Project

```bash
pywebvue create my_app --title "My Application" --width 1024 --height 768
cd my_app
```

The CLI walks the `src/pywebvue/templates/project/` directory, substitutes `{{VARIABLES}}` placeholders, and copies static files as-is. Variable names use UPPER_CASE to avoid collision with Vue's `{{ camelCase }}` template syntax.

### Generated Files

```
my_app/
  main.py                  # Entry point: App(config="config.yaml").run()
  app.py                   # User API class (subclass of ApiBase)
  config.yaml              # All configuration
  pyproject.toml           # Python dependencies + uv scripts
  .gitignore
  my_app.spec              # PyInstaller onedir spec
  my_app-onefile.spec      # PyInstaller onefile spec
  my_app-debug.spec        # PyInstaller debug (console) spec
  frontend/
    package.json           # vue 3 + tailwindcss + daisyui + vite + typescript
    vite.config.ts         # outDir: ../dist, alias @ -> src/
    tailwind.config.ts     # DaisyUI themes: ["light", "dark"]
    postcss.config.js
    tsconfig.json / tsconfig.node.json
    index.html             # data-theme attribute controls DaisyUI theme
    src/
      main.ts              # createApp(App).mount("#app")
      App.vue              # Root layout + toast/progress/event wiring
      api.ts               # waitForReady() + call<T>(method, ...args)
      event-bus.ts         # useEvent(name, cb) + waitForEvent<T>(name, timeout)
      types/index.ts       # ErrCode, ApiResult<T>, isOk(), LogEntry, etc.
      assets/style.css     # Tailwind directives + html/body/#app height:100%
      components/
        FileDrop.vue       # Drag-and-drop zone + file list
        LogPanel.vue       # Real-time log viewer with level filter
        ProgressBar.vue    # Progress bar with percentage and label
        StatusBadge.vue    # Colored state badge (idle/running/paused/error/done)
        Toast.vue          # Auto-dismissing notification stack
```

### Running Locally

```bash
# Terminal 1: Vite dev server (hot module replacement)
cd frontend && bun dev

# Terminal 2: Python app (auto-connects to Vite)
uv run python main.py

# Or auto-start Vite from Python:
uv run python main.py --with-vite
```

### Packaging

```bash
uv run pywebvue build                    # onedir (default)
uv run pywebvue build --mode onefile     # single exe
uv run pywebvue build --clean            # wipe build/ and dist/ first
uv run pywebvue build --icon app.ico     # override icon
uv run pywebvue build --output-dir ./out # custom output directory
```

---

## 3. Example 1: file-tool -- Backend API Design

Source: `examples/file-tool/app.py`

This example demonstrates the most common pattern: define public methods on an `ApiBase` subclass, each returning `Result`.

### File Structure

```
examples/file-tool/
  main.py              # App entry (identical to scaffolded template)
  app.py               # FileToolApi class
  config.yaml          # theme: dark
  pyproject.toml
  frontend/
    src/
      App.vue           # Custom layout
      components/
        FileInfoCard.vue # Custom component for metadata display
        FileDrop.vue     # Reused from template
        LogPanel.vue     # Reused from template
        ProgressBar.vue  # Reused from template
        Toast.vue        # Reused from template
```

### API Class Walkthrough

```python
from pywebvue import ApiBase, Result, ErrCode

class FileToolApi(ApiBase):
```

**1. Health check** -- every API class should implement this for frontend connectivity detection:

```python
def health_check(self) -> Result:
    return Result.ok(data={"status": "running"})
```

**2. File drop handler** -- override `on_file_drop` to process files dropped onto the window:

```python
def on_file_drop(self, file_paths: list[str]) -> None:
    for path in file_paths:
        self.logger.info(f"File dropped: {path}")
        self.emit("file:dropped", {"path": path})
```

Key points:
- `on_file_drop` is called by the framework from a background thread when files are dragged onto the window
- Use `self.emit()` to push events to the frontend
- `self.logger` is a loguru logger bound with the class name, and its output automatically appears in the frontend LogPanel when `logging.to_frontend: true`

**3. File info retrieval** -- a synchronous API method that returns file metadata:

```python
def get_file_info(self, path: str) -> Result:
    if not os.path.isfile(path):
        return Result.fail(ErrCode.FILE_NOT_FOUND, detail=path)
    # ... gather metadata ...
    return Result.ok(data={
        "path": path,
        "name": os.path.basename(path),
        "extension": ext.lower(),
        "size_bytes": size_bytes,
        "size_display": "1.5 MB",
        "modified": "2026-03-28T10:30:00",
        "is_binary": False,
    })
```

Key points:
- Parameter types must be JSON-serializable (str, int, float, bool, list, dict, None)
- Use `Result.fail(ErrCode.XXX, detail=...)` for error responses; `detail` goes into `data.detail`
- Use `Result.ok(data=...)` for success; data is auto-serialized to JSON (Path objects become strings, etc.)

**4. Background processing** -- long-running work in a background thread with progress events:

```python
def process_file(self, path: str) -> Result:
    if not os.path.isfile(path):
        return Result.fail(ErrCode.FILE_NOT_FOUND, detail=path)
    self.run_in_thread(self._simulate_processing, path)
    return Result.ok(data={"message": "Processing started"})
```

`self.run_in_thread(func, *args)` is a convenience method on `ApiBase` that starts a daemon thread. Use it for any work that would block the pywebview GUI thread.

The `_simulate_processing` method emits `progress:update` events at each step:

```python
def _simulate_processing(self, path: str) -> None:
    total_steps = 10
    for i in range(1, total_steps + 1):
        time.sleep(0.5)
        self.emit("progress:update", {
            "current": i,
            "total": total_steps,
            "label": f"Step {i}/{total_steps}: Analyzing",
        })
        self.logger.info(f"Processing [{i}/{total_steps}]: {os.path.basename(path)}")

    self.emit("progress:update", {"current": 0, "total": 0})  # Reset progress
    self.emit("file:process_complete", {"path": path, "name": os.path.basename(path)})
```

Important: `self.emit()` calls `evaluate_js()` which must run on the GUI thread. pywebview queues these calls safely, but avoid emitting thousands of events per second in tight loops.

### Error Handling Strategy

```python
# Validation error (user-caused)
return Result.fail(ErrCode.FILE_NOT_FOUND, detail=path)

# System error
return Result.fail(ErrCode.FILE_READ_ERROR, detail=str(e))

# Implicit: any uncaught exception in a public method is caught by ApiProxy
# and returned as Result.fail(ErrCode.INTERNAL_ERROR, detail=str(e))
```

---

## 4. Example 1: file-tool -- Frontend Implementation

Source: `examples/file-tool/frontend/src/App.vue`

### Toast System (provide/inject)

Every PyWebVue app needs a toast system for user feedback. The pattern is consistent across all projects:

```typescript
// App.vue
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
<!-- Place at template root -->
<Toast :items="toastQueue" @dismiss="removeToast" />
```

### Event Subscriptions

The `useEvent` composable subscribes for the component's lifetime and auto-unsubscribes on unmount:

```typescript
import { useEvent } from "@/event-bus";

// React to file drops -- load metadata immediately
useEvent("file:dropped", (data) => {
  const { path } = data as { path: string };
  showToast({ type: "info", message: `File received: ${path}` });
  loadFileInfo(path);
});

// React to progress updates
useEvent("progress:update", (data) => {
  progress.value = data as ProgressPayload;
  if ((data as ProgressPayload).current === 0) {
    processing.value = false;  // Processing finished
  }
});

// React to completion
useEvent("file:process_complete", (data) => {
  const { name } = data as { name: string };
  showToast({ type: "success", message: `Processing complete: ${name}` });
});
```

### API Calls

```typescript
import { call } from "@/api";
import { isOk } from "@/types";

async function loadFileInfo(path: string) {
  const result = await call<FileInfo>("get_file_info", path);
  if (isOk(result)) {
    fileInfo.value = result.data;
  } else {
    showToast({ type: "error", message: `Failed to read file: ${result.msg}` });
  }
}
```

The generic type parameter `<FileInfo>` provides type safety for `result.data`. `isOk(result)` narrows the type to exclude null data.

### Backend Readiness

```typescript
import { waitForReady } from "@/api";

onMounted(async () => {
  try {
    await waitForReady();
    backendReady.value = true;
  } catch {
    backendReady.value = false;
  }
});
```

Always wait for readiness before making API calls. If the app runs outside pywebview (e.g., `bun dev` without Python), `waitForReady` will never resolve, so wrap it in try/catch.

### Custom Component: FileInfoCard

The file-tool example adds a custom `FileInfoCard.vue` that is not part of the framework's pre-built components. It receives a `FileInfo` object as a prop and renders a DaisyUI table:

```vue
<script setup lang="ts">
import type { FileInfo } from "@/types";
defineProps<{ fileInfo: FileInfo | null }>();
</script>

<template>
  <div class="card bg-base-100 shadow">
    <div class="card-body">
      <h2 class="card-title">File Information</h2>
      <div v-if="fileInfo" class="overflow-x-auto">
        <table class="table table-sm">
          <tr><td class="font-medium w-36">Name</td><td>{{ fileInfo.name }}</td></tr>
          <tr><td class="font-medium">Size</td><td>{{ fileInfo.size_display }}</td></tr>
          <!-- ... more rows ... -->
        </table>
      </div>
    </div>
  </div>
</template>
```

This demonstrates that you can mix framework pre-built components with your own custom components freely. The only contract is that custom components should use the same `@/types` and `@/event-bus` imports.

---

## 5. Example 2: process-tool -- ProcessManager in Practice

Source: `examples/process-tool/app.py`

This example demonstrates the `ProcessManager` -- a thread-safe state machine for managing subprocesses with real-time output streaming, pause/resume (cross-platform), timeout, and reset.

### ProcessManager Initialization

```python
class ProcessToolApi(ApiBase):
    def __init__(self) -> None:
        super().__init__()
        self.pm = ProcessManager(self, name="worker")
```

The `name` parameter distinguishes events from multiple ProcessManager instances. Events are emitted as `process:{name}:output`, `process:{name}:complete`, `process:{name}:timeout`.

### State Machine

```
          start()                 stop()
IDLE --------> RUNNING --------> STOPPED
                  |                  |
                  | pause()          | reset()
                  v                  v
               PAUSED --------> IDLE

Note: start() auto-resets from STOPPED, so:
  STOPPED -> start() -> RUNNING (implicit reset)
```

### Starting a Process

```python
def start_task(self, cmd: str, timeout: int | None = None) -> Result:
    if self.pm.is_running or self.pm.is_paused:
        return Result.fail(ErrCode.PROCESS_ALREADY_RUNNING, ...)

    parts = shlex.split(cmd)  # Parse command string into args list
    result = self.pm.start(
        cmd=parts,
        on_output=lambda line: self.logger.info(f"[worker] {line}"),
        on_complete=lambda rc: self.logger.info(f"Exit code: {rc}"),
        timeout=timeout,
    )
```

Key points:
- `cmd` must be a list of strings (not a single string)
- `on_output` is called for each stdout/stderr line from the subprocess
- `on_complete` is called with the exit code when the subprocess terminates
- `timeout` (seconds) starts a daemon timer that auto-stops the process. If None, reads `process.default_timeout` from config.yaml

### Pause/Resume/Stop/Reset

```python
def pause_task(self) -> Result:
    return self.pm.pause()     # Windows: NtSuspendProcess, Unix: SIGSTOP

def resume_task(self) -> Result:
    return self.pm.resume()    # Windows: NtResumeProcess, Unix: SIGCONT

def stop_task(self) -> Result:
    return self.pm.stop()      # terminate(), force kill after 5s

def reset_task(self) -> Result:
    return self.pm.reset()     # STOPPED -> IDLE (allows re-start)
```

### Timeout Behavior

When `timeout` is set (explicitly or from config):

1. A daemon thread starts a `threading.Event.wait(timeout)`
2. If the timer fires before the process completes or is manually stopped:
   - `process:{name}:timeout` event is emitted
   - `pm.stop()` is called automatically
   - State transitions to STOPPED
3. If the process completes or is manually stopped before timeout:
   - The timer is cancelled (event.set())
   - `timeout_remaining` property returns `None`

### Multi-Instance Example

```python
class EncodingApi(ApiBase):
    def __init__(self):
        super().__init__()
        self.encoder = ProcessManager(self, name="encoder")
        self.uploader = ProcessManager(self, name="uploader")

    # Events: process:encoder:*, process:uploader:*
```

---

## 6. Example 2: process-tool -- Real-time State Synchronization

Source: `examples/process-tool/frontend/src/App.vue`

### Event-Driven State Updates

Instead of polling `get_status()` repeatedly, the frontend subscribes to state change events:

```typescript
// Python emits: self.emit("process:state_changed", {"state": "running", "pid": 1234})
useEvent("process:state_changed", (data) => {
  const payload = data as { state: string };
  const mapped: Record<string, StatusState> = {
    idle: "idle", running: "running", paused: "paused", stopped: "done",
  };
  processState.value = mapped[payload.state] ?? "error";
  refreshStatus();  // Fetch PID and timeout from get_status()
});
```

This push-based pattern is more efficient than polling and updates the UI instantly.

### Computed Button States

Using Vue's `computed` to derive button disabled states from process state:

```typescript
const canStart = computed(() =>
  processState.value === "idle" || processState.value === "done"
);
const canPause = computed(() => processState.value === "running");
const canResume = computed(() => processState.value === "paused");
const canStop = computed(() =>
  processState.value === "running" || processState.value === "paused"
);
const canReset = computed(() => processState.value === "done");
```

Template:
```vue
<button class="btn btn-primary btn-sm" :disabled="!backendReady || !canStart" @click="startProcess">
  Start
</button>
<button class="btn btn-warning btn-sm" :disabled="!backendReady || !canPause" @click="pauseProcess">
  Pause
</button>
<!-- ... -->
```

### Subscribing to ProcessManager Events

```typescript
// Timeout notification
useEvent("process:worker:timeout", (data) => {
  const { timeout } = data as { timeout: number };
  showToast({ type: "warning", message: `Process timed out after ${timeout}s` });
});

// Completion notification (with exit code)
useEvent("process:worker:complete", (data) => {
  const { returncode } = data as { returncode: number };
  if (returncode === 0) {
    showToast({ type: "success", message: "Process completed successfully" });
  } else {
    showToast({ type: "error", message: `Process exited with code ${returncode}` });
  }
});
```

### Displaying Status in the Navbar

```vue
<nav class="navbar bg-base-100 shadow-md px-4">
  <div class="flex items-center gap-2">
    <StatusBadge :status="processState" />
    <span v-if="pid" class="badge badge-outline badge-sm">PID: {{ pid }}</span>
    <span v-if="timeoutRemaining !== null" class="badge badge-outline badge-sm">
      Timeout: {{ timeoutRemaining }}s
    </span>
  </div>
</nav>
```

---

## 7. Frontend-Backend Communication Patterns

### Pattern 1: Request-Response (API Call)

Use when the frontend needs data from the backend.

**Python:**
```python
def get_data(self, id: int) -> Result:
    return Result.ok(data={"id": id, "value": "hello"})
```

**TypeScript:**
```typescript
const result = await call<{ id: number; value: string }>("get_data", 42);
if (isOk(result)) {
  console.log(result.data.value);
}
```

### Pattern 2: Push Event (Backend -> Frontend)

Use when the backend needs to notify the frontend asynchronously.

**Python:**
```python
self.emit("progress:update", {"current": 5, "total": 10})
```

**TypeScript:**
```typescript
useEvent("progress:update", (data) => {
  const { current, total } = data as { current: number; total: number };
});
```

### Pattern 3: Background Task with Progress

Use when a long-running operation needs progress feedback.

**Python:**
```python
def start_work(self) -> Result:
    self.run_in_thread(self._do_work)
    return Result.ok(data={"message": "Started"})

def _do_work(self) -> None:
    for i in range(10):
        time.sleep(1)
        self.emit("progress:update", {"current": i + 1, "total": 10})
    self.emit("work:complete", {})
```

**TypeScript:**
```typescript
useEvent("work:complete", () => showToast({ type: "success", message: "Done!" }));
```

### Pattern 4: File Drop

Use when the user drags files onto the window.

**Python** (override `on_file_drop`):
```python
def on_file_drop(self, file_paths: list[str]) -> None:
    for path in file_paths:
        self.emit("file:dropped", {"path": path})
```

The framework handles the DOM event registration and background threading automatically. You just need to override `on_file_drop` and emit events as needed.

### Pattern 5: Native Dialog

Use when you need a native OS dialog.

**Python:**
```python
def select_file(self) -> Result:
    paths = self.dialog.open_file(
        title="Select File",
        file_types=("Text Files (*.txt)", "All Files (*.*)"),
        multiple=True,
    )
    if paths is None:
        return Result.fail(ErrCode.PARAM_INVALID, detail="User cancelled")
    return Result.ok(data=paths)
```

### Pattern 6: One-time Event Wait

Use when you need to wait for a specific event in an async function.

**TypeScript:**
```typescript
import { waitForEvent } from "@/event-bus";

const result = await waitForEvent<{ path: string }>("file:process_complete", 60000);
console.log(result.path);
```

---

## 8. Pre-built Components Deep Dive

### Toast

Auto-dismissing notification stack rendered via `<Teleport to="body">`.

| Prop | Type | Description |
|------|------|-------------|
| `items` | `ToastOptions[]` | Array of toast messages to display |

| Event | Payload | Description |
|-------|---------|-------------|
| `dismiss` | `index: number` | Fired when auto-dismiss or manual close |

```typescript
// Types
interface ToastOptions {
  id: number;
  type: "success" | "error" | "warning" | "info";
  message: string;
  duration?: number;  // Currently uses fixed 4000ms
}
```

The watcher detects new items by comparing array length, and starts a 4-second auto-dismiss timer for each new toast. The `dismiss` event lets the parent remove the item from its source array.

### LogPanel

Real-time log viewer that subscribes to `log:add` events automatically.

Features:
- Level filter dropdown (ALL/DEBUG/INFO/WARNING/ERROR/CRITICAL)
- Auto-scroll toggle
- Clear button
- Max 500 entries (FIFO)
- Color-coded levels via DaisyUI text utilities

No props or events required -- it is fully self-contained.

### ProgressBar

Displays progress with percentage, label, and color transitions.

| Prop | Type | Description |
|------|------|-------------|
| `progress` | `ProgressPayload \| null` | Progress data, or null for idle state |

```typescript
interface ProgressPayload {
  current: number;
  total: number;
  label?: string;
}
```

Color logic: `< 50%` = warning, `50-99%` = primary, `100%` = success.

To reset the progress bar (hide it), emit `{ current: 0, total: 0 }` or set progress to `null`.

### StatusBadge

Simple colored badge for state display.

| Prop | Type | Description |
|------|------|-------------|
| `status` | `StatusState` | One of: idle/running/paused/error/done |

| State | Badge Style |
|-------|-------------|
| idle | `badge-ghost` |
| running | `badge-primary` |
| paused | `badge-warning` |
| error | `badge-error` |
| done | `badge-success` |

### FileDrop

Drag-and-drop zone with file list display.

Listens to `file:dropped` events (emitted by the backend's `on_file_drop` handler) and maintains a local list of dropped file paths.

Requires the `toast` inject for the Browse button's fallback message:
```typescript
provide("toast", { showToast });
```

---

## 9. Configuration System

### config.yaml Structure

```yaml
app:
  name: "my_app"             # Python identifier (used in spec filenames)
  title: "My App"            # Window title bar text
  width: 900                 # Initial window width (px)
  height: 650                # Initial window height (px)
  min_size: [600, 400]       # Minimum window size
  max_size: [1920, 1080]     # Maximum window size
  resizable: true            # Enable window resizing
  icon: "assets/icon.ico"    # Window icon path
  singleton: false           # Prevent multiple instances
  centered: true             # Center window on screen
  theme: light               # DaisyUI theme (light or dark)

  dev:
    enabled: true            # Auto-detect Vite dev server
    vite_port: 5173          # Vite port to check
    debug: true              # pywebview debug mode

logging:
  level: INFO                # Minimum log level
  console: true              # Print to stderr
  to_frontend: true          # Forward to frontend LogPanel
  file: ""                   # Log file path (empty = disabled)
  max_lines: 1000            # Max entries in frontend buffer

process:
  default_timeout: 300       # Default subprocess timeout (seconds)
                              # Used by ProcessManager.start() when no explicit timeout

business: {}                 # Custom key-value config (access via self.config.business)
```

### Accessing Config in Python

```python
class MyAppApi(ApiBase):
    def some_method(self) -> Result:
        # Access any config value
        title = self.config.title
        db_path = self.config.business.get("database_path", "")
        timeout = self.config.process.default_timeout
        return Result.ok()
```

### Theme Switching

The DaisyUI theme is controlled by the `data-theme` attribute on `<html>`:

```html
<!-- Light theme -->
<html lang="en" data-theme="light">

<!-- Dark theme -->
<html lang="en" data-theme="dark">
```

The `app.theme` config value is not automatically applied to the HTML. Set `data-theme` in `index.html` to match your desired theme.

---

## 10. Advanced Topics

### Singleton Lock

Set `singleton: true` in config.yaml to prevent multiple instances:

```yaml
app:
  singleton: true
```

The lock uses file-based primitives (`msvcrt.locking` on Windows, `fcntl.flock` on Unix). It checks for stale lock files by verifying whether the PID in the lock file is still alive.

### Custom Error Codes

```python
from pywebvue import ErrCode

# Use codes >= 10000 for application-specific errors
ErrCode.USER_NOT_FOUND = 10001
ErrCode.INSUFFICIENT_PERMISSION = 10002
ErrCode._MSG[10001] = "user not found"
ErrCode._MSG[10002] = "insufficient permission"
```

On the frontend, mirror them in `types/index.ts`:
```typescript
export const ErrCode = {
  // ... built-in codes ...
  USER_NOT_FOUND: 10001,
  INSUFFICIENT_PERMISSION: 10002,
} as const;
```

### Logging Best Practices

```python
# self.logger is pre-bound with your class name
self.logger.info("Operation completed")
self.logger.warning("Retry attempt 3/5")
self.logger.error("Connection failed")
self.logger.opt(exception=True).error("Detailed error with traceback")  # Include traceback
```

All log output at or above `logging.level` is automatically forwarded to the frontend LogPanel when `logging.to_frontend: true`.

### ProcessManager: Binary Size Considerations

When packaging with PyInstaller, the `ProcessManager` uses `subprocess.Popen` with `creationflags` on Windows. This adds minimal overhead. The cross-platform suspend/resume uses `ctypes` to call `NtSuspendProcess`/`NtResumeProcess` on Windows.

### Debugging Tips

1. **Use `--mode debug`** to get a console window alongside your app for Python log output
2. **Use the LogPanel** -- backend logs are forwarded in real-time when `to_frontend: true`
3. **Use `self.logger.opt(exception=True).error(...)`** for detailed error context
4. **Check the browser DevTools** -- pywebview in debug mode enables right-click > Inspect Element
5. **API errors are never silent** -- `ApiProxy` catches all uncaught exceptions and returns `Result.fail(ErrCode.INTERNAL_ERROR, detail=str(e))`
