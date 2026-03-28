# PyWebVue User Guide

> This guide is for **end users and developers** who want to install, run, configure, and package PyWebVue applications. It covers what you need to know to use the framework and its CLI, without diving into framework internals.

---

## Table of Contents

1. [What is PyWebVue](#1-what-is-pywebvue)
2. [Prerequisites and Installation](#2-prerequisites-and-installation)
3. [Creating a New Project](#3-creating-a-new-project)
4. [Running Your Application](#4-running-your-application)
5. [Project Structure](#5-project-structure)
6. [Writing Backend Logic (app.py)](#6-writing-backend-logic-apppy)
7. [Frontend Development](#7-frontend-development)
8. [Built-in UI Components](#8-built-in-ui-components)
9. [Configuration Reference](#9-configuration-reference)
10. [Subprocess Management](#10-subprocess-management)
11. [Building and Packaging](#11-building-and-packaging)
12. [Examples](#12-examples)
13. [Troubleshooting](#13-troubleshooting)

---

## 1. What is PyWebVue

PyWebVue is a desktop application framework for Python developers. It combines:

- **Python backend** via [pywebview](https://pywebview.flowrl.com/) -- native window with JS bridge
- **Vue 3 frontend** with TypeScript, [Tailwind CSS](https://tailwindcss.com/), and [DaisyUI](https://daisyui.com/)
- **CLI tooling** for project scaffolding and PyInstaller packaging

You write Python business logic and Vue components. The framework handles the window lifecycle, event communication, logging, file drag-drop, subprocess management, and native dialogs.

### Features at a Glance

| Feature | Description |
|---------|-------------|
| Project scaffolding | `pywebvue create my_app` generates a full project |
| Hot module replacement | Vite dev server with instant frontend updates |
| Frontend-Backend bridge | Call Python methods from TypeScript, push events from Python to Vue |
| Global exception handling | Uncaught Python exceptions return `Result.fail()` instead of crashing |
| Real-time logging | Backend logs appear in the frontend LogPanel automatically |
| File drag-and-drop | Drag files onto the window, handled by your Python code |
| Subprocess management | Start/pause/resume/stop subprocesses with timeout support |
| Native dialogs | File open, folder select, save-as dialogs |
| Single-instance lock | Prevent multiple app instances via file lock |
| PyInstaller packaging | One-click build to `.exe` (onedir, onefile, or debug modes) |

---

## 2. Prerequisites and Installation

### Requirements

| Tool | Version | Purpose |
|------|---------|---------|
| Python | >= 3.10.8 | Runtime |
| [uv](https://docs.astral.sh/uv/) | Latest | Package manager |
| [bun](https://bun.sh/) | Latest | Frontend package manager (npm alternative) |
| PyInstaller (optional) | >= 6.0 | Packaging |

### Install the Framework

```bash
# Add to your project (recommended)
uv add pywebvue-framework

# Or install globally
pip install pywebvue-framework
```

This installs the `pywebvue` CLI command and the Python package.

### Verify Installation

```bash
pywebvue --help
```

Should display:

```
usage: pywebvue [-h] {create,build} ...

PyWebVue - Desktop rapid development framework CLI

options:
  -h, --help  show this help message

commands:
  create      Scaffold a new PyWebVue project
  build       Build a PyWebVue project for distribution
```

---

## 3. Creating a New Project

### Basic Scaffolding

```bash
pywebvue create my_app
cd my_app
```

This creates a project named `my_app` with default settings:
- Window title: "My App" (derived from project name)
- Window size: 900x650
- Theme: light
- Full Vue 3 + TypeScript + DaisyUI frontend

### Custom Options

```bash
pywebvue create my_app \
  --title "Invoice Generator" \
  --width 1024 \
  --height 768
```

| Flag | Default | Description |
|------|---------|-------------|
| `project_name` | (required) | Python identifier (snake_case) |
| `--title` | project name | Window title text |
| `--width` | 900 | Window width (px) |
| `--height` | 650 | Window height (px) |
| `--force` | false | Overwrite existing directory (with confirmation) |

### Project Name Rules

- Must be a valid Python identifier: letters, digits, underscores, starting with letter or `_`
- Cannot be a Python keyword (e.g., `class`, `def`, `import`)
- Used in spec filenames, config, and Python module naming

---

## 4. Running Your Application

### Development with Vite HMR (Hot Module Replacement)

**Option A: Manual Vite start (two terminals)**

```bash
# Terminal 1: Start Vite dev server
cd my_app/frontend
bun install    # First time only
bun dev

# Terminal 2: Start the app (auto-detects Vite)
cd my_app
uv run main.py
```

**Option B: Auto-start Vite (single terminal)**

```bash
cd my_app
uv run main.py --with-vite
```

This starts Vite in the background, waits for it to be ready, then opens the window.

### Production Mode

Build the frontend first, then run:

```bash
cd my_app/frontend
bun run build        # Outputs to ../dist/

cd ..
uv run main.py   # Loads dist/index.html
```

### How Mode Selection Works

The app reads `dev.enabled` from `config.yaml`:

- If `true` and Vite is reachable at `http://localhost:{vite_port}`: loads from Vite (HMR)
- If `true` but Vite is not reachable: falls back to `dist/index.html` with a warning
- If `false`: always loads `dist/index.html`

---

## 5. Project Structure

```
my_app/
  main.py                  # Entry point
  app.py                   # Your business API (edit this)
  config.yaml              # Application settings (edit this)
  pyproject.toml           # Python dependencies
  .gitignore
  my_app.spec              # PyInstaller: folder output
  my_app-onefile.spec      # PyInstaller: single exe output
  my_app-debug.spec        # PyInstaller: console window visible
  frontend/
    package.json
    vite.config.ts
    tailwind.config.ts
    postcss.config.js
    tsconfig.json
    tsconfig.node.json
    index.html             # HTML entry (data-theme attribute here)
    src/
      main.ts              # Vue app bootstrap
      App.vue              # Root component (edit this)
      api.ts               # Backend API call helper
      event-bus.ts         # Event subscription helpers
      types/index.ts       # TypeScript types + ErrCode
      assets/style.css     # Global styles
      components/
        FileDrop.vue       # Drag-and-drop zone
        LogPanel.vue       # Log viewer with level filter
        ProgressBar.vue    # Progress bar
        StatusBadge.vue    # State indicator badge
        Toast.vue          # Notification popups
  dist/                    # Built frontend (generated by bun run build)
```

### Files You Will Edit

| File | When |
|------|------|
| `app.py` | Add business logic methods |
| `config.yaml` | Change window settings, logging, theme |
| `frontend/src/App.vue` | Customize the UI layout |
| `frontend/src/types/index.ts` | Add custom TypeScript types |
| `frontend/src/components/` | Add custom Vue components |

---

## 6. Writing Backend Logic (app.py)

### Basic Structure

```python
from pywebvue import ApiBase, Result, ErrCode

class MyAppApi(ApiBase):
    """All public methods are exposed to the frontend automatically."""

    def health_check(self) -> Result:
        return Result.ok(data={"status": "running"})
```

### Rules

1. **Subclass `ApiBase`**
2. **All public methods** (not prefixed with `_`) are callable from JavaScript
3. **Every method must return `Result`**
4. **Parameters** must be JSON-serializable: `str`, `int`, `float`, `bool`, `list`, `dict`, `None`
5. **Uncaught exceptions** are caught automatically and returned as `Result.fail(ErrCode.INTERNAL_ERROR)`

### Return Values

```python
# Success
return Result.ok(data={"name": "Alice", "age": 30})

# Success with no data
return Result.ok()

# Error
return Result.fail(ErrCode.PARAM_INVALID, detail="Email is required")
return Result.fail(ErrCode.FILE_NOT_FOUND, detail="/path/to/file.txt")
```

### Built-in Error Codes

| Code | Name | When to Use |
|------|------|-------------|
| 0 | `OK` | Success |
| 2 | `PARAM_INVALID` | Invalid user input |
| 4 | `TIMEOUT` | Operation timed out |
| 5 | `INTERNAL_ERROR` | Unexpected server error (auto) |
| 1001 | `FILE_NOT_FOUND` | File does not exist |
| 1002 | `FILE_READ_ERROR` | Cannot read file |
| 2001 | `PROCESS_START_FAILED` | Subprocess failed to start |
| 2002 | `PROCESS_ALREADY_RUNNING` | Subprocess already active |
| 2003 | `PROCESS_NOT_RUNNING` | No active subprocess |
| 2004 | `PROCESS_TIMEOUT` | Subprocess timed out |

### Custom Error Codes

```python
from pywebvue import ErrCode

ErrCode.USER_NOT_FOUND = 10001
ErrCode._MSG[10001] = "user not found"
```

### File Drop Handling

Override `on_file_drop` to handle files dragged onto the window:

```python
def on_file_drop(self, file_paths: list[str]) -> None:
    for path in file_paths:
        self.logger.info(f"Received: {path}")
        self.emit("file:received", {"path": path})
```

### Background Tasks

Use `self.run_in_thread()` for long-running operations:

```python
def start_processing(self) -> Result:
    self.run_in_thread(self._do_work)
    return Result.ok(data={"message": "Started"})

def _do_work(self) -> None:
    for i in range(10):
        time.sleep(0.5)
        self.emit("progress:update", {"current": i + 1, "total": 10, "label": f"Step {i+1}"})
    self.emit("work:complete", {})
```

### Native Dialogs

```python
# File picker
paths = self.dialog.open_file(title="Select", file_types=("Images (*.png;*.jpg)",), multiple=True)
if paths is None:
    return Result.fail(ErrCode.PARAM_INVALID, detail="Cancelled")
return Result.ok(data=paths)

# Folder picker
folders = self.dialog.open_folder(title="Select Output Folder")

# Save dialog
save_paths = self.dialog.save_file(title="Save As", default_name="output.csv", file_types=("CSV (*.csv)",))
```

### Logging

```python
# self.logger is a loguru logger pre-bound with your class name
self.logger.info("User clicked button")
self.logger.warning("Disk space low")
self.logger.error("Connection failed")
self.logger.opt(exception=True).error("Detailed error")  # Include traceback
```

All logs at or above the configured level are forwarded to the frontend LogPanel.

### Accessing Configuration

```python
def get_app_info(self) -> Result:
    return Result.ok(data={
        "name": self.config.title,
        "width": self.config.width,
        "custom": self.config.business.get("my_key", "default"),
    })
```

---

## 7. Frontend Development

### Calling Backend Methods

```typescript
import { call } from "@/api";
import { isOk } from "@/types";

// Simple call
const result = await call<{ status: string }>("health_check");
if (isOk(result)) {
  console.log(result.data.status);
}

// Call with arguments
const user = await call<{ name: string }>("get_user", 42);

// Error handling
if (!isOk(user)) {
  showToast({ type: "error", message: user.msg });
}
```

### Waiting for Backend Readiness

```typescript
import { waitForReady } from "@/api";

onMounted(async () => {
  await waitForReady();  // Resolves when pywebview JS API is available
  // Safe to call backend methods now
});
```

### Listening for Events

```typescript
import { useEvent } from "@/event-bus";

// Auto-unsubscribes when component unmounts
useEvent("progress:update", (data) => {
  const { current, total } = data as { current: number; total: number };
  console.log(`${current}/${total}`);
});
```

### One-time Event Wait

```typescript
import { waitForEvent } from "@/event-bus";

const result = await waitForEvent<{ path: string }>("file:complete", 30000);
```

### Toast Notifications

```typescript
// In App.vue (or any component that provides the toast system)
let _toastId = 0;
const toastQueue = reactive<ToastOptions[]>([]);

function showToast(options: ToastOptions) {
  toastQueue.push({ ...options, id: ++_toastId });
}

provide("toast", { showToast });
```

```vue
<Toast :items="toastQueue" @dismiss="(i) => toastQueue.splice(i, 1)" />
```

---

## 8. Built-in UI Components

### FileDrop

Drag-and-drop file zone. Shows a list of dropped files.

```vue
<FileDrop />
```

Requires `provide("toast", { showToast })` in an ancestor component.

### LogPanel

Real-time log viewer. Auto-subscribes to `log:add` events.

```vue
<LogPanel />
```

Features: level filter (ALL/DEBUG/INFO/WARNING/ERROR/CRITICAL), auto-scroll, clear button, max 500 entries.

### ProgressBar

Progress bar with percentage badge and label text.

```vue
<ProgressBar :progress="progressData" />
```

```typescript
import type { ProgressPayload } from "@/types";
const progressData = ref<ProgressPayload | null>(null);

// To show progress
progressData.value = { current: 5, total: 10, label: "Processing..." };

// To hide/reset
progressData.value = null;
// Or emit { current: 0, total: 0 } from backend
```

### StatusBadge

Colored badge for state indication.

```vue
<StatusBadge status="running" />
```

Values: `"idle"` (gray), `"running"` (blue), `"paused"` (yellow), `"error"` (red), `"done"` (green).

### Toast

Auto-dismissing notification stack (4-second timer).

```vue
<Toast :items="toastQueue" @dismiss="removeToast" />
```

```typescript
showToast({ type: "success", message: "Saved!" });
showToast({ type: "error", message: "Failed to save" });
showToast({ type: "warning", message: "Disk almost full" });
showToast({ type: "info", message: "New version available" });
```

---

## 9. Configuration Reference

### Complete config.yaml

```yaml
app:
  name: "my_app"             # Python identifier (used in spec file names)
  title: "My App"            # Window title
  width: 900                 # Window width (pixels)
  height: 650                # Window height (pixels)
  min_size: [600, 400]       # Minimum window size
  max_size: [1920, 1080]     # Maximum window size
  resizable: true            # Allow window resize
  icon: "assets/icon.ico"    # Window icon path
  singleton: false           # Prevent multiple instances
  centered: true             # Center on screen
  theme: light               # DaisyUI theme: light or dark

  dev:
    enabled: true            # Auto-detect Vite dev server
    vite_port: 5173          # Vite dev server port
    debug: true              # pywebview debug mode (right-click > Inspect)

logging:
  level: INFO                # Min level: DEBUG, INFO, WARNING, ERROR, CRITICAL
  console: true              # Print logs to terminal
  to_frontend: true          # Show logs in frontend LogPanel
  file: ""                   # Log file path (empty = disabled)
  max_lines: 1000            # Max log entries kept in frontend buffer

process:
  default_timeout: 300       # Default subprocess timeout (seconds)

business: {}                 # Custom configuration (access via self.config.business)
```

### Theme

Set `data-theme` in `frontend/index.html` to match `app.theme`:

```html
<html lang="en" data-theme="dark">  <!-- for dark theme -->
```

DaisyUI supports `light` and `dark` by default. Add more themes in `tailwind.config.ts` under `daisyui.themes`.

---

## 10. Subprocess Management

### Quick Example

```python
from pywebvue import ApiBase, ProcessManager, Result

class MyAppApi(ApiBase):
    def __init__(self):
        super().__init__()
        self.pm = ProcessManager(self, name="worker")

    def start_task(self, cmd: str) -> Result:
        return self.pm.start(
            cmd=cmd.split(),
            on_output=lambda line: self.logger.info(line),
            on_complete=lambda rc: self.logger.info(f"Exit: {rc}"),
        )

    def pause_task(self) -> Result:
        return self.pm.pause()

    def resume_task(self) -> Result:
        return self.pm.resume()

    def stop_task(self) -> Result:
        return self.pm.stop()

    def reset_task(self) -> Result:
        return self.pm.reset()
```

### State Transitions

```
IDLE -> start() -> RUNNING -> pause() -> PAUSED -> resume() -> RUNNING
                                |                                      |
                                +--- stop() -------> STOPPED -----------+
                                                     |
                                                     +--- reset() -> IDLE
                                                     |
                                                     +--- start() -> RUNNING (auto-reset)
```

### Timeout

```python
# Explicit timeout (seconds)
self.pm.start(cmd=["long_task"], timeout=60)

# Or set in config.yaml:
# process:
#   default_timeout: 300
```

When timeout fires: the process is auto-stopped, and `process:{name}:timeout` event is emitted.

### Events (subscribe in frontend)

| Event | Data | When |
|-------|------|------|
| `process:{name}:output` | `{ line: "..." }` | Each stdout/stderr line |
| `process:{name}:complete` | `{ returncode: 0 }` | Process exits |
| `process:{name}:timeout` | `{ timeout: 60 }` | Timeout reached |

---

## 11. Building and Packaging

### PyInstaller Build Modes

| Mode | Flag | Output |
|------|------|--------|
| Folder | `--mode onedir` (default) | `dist/my_app/my_app.exe` + DLLs |
| Single exe | `--mode onefile` | `dist/my_app.exe` |
| Debug | `--mode debug` | Console window visible |

### Build Command

```bash
# From the project root directory:
uv run pywebvue build
```

### Build Flags

| Flag | Description |
|------|-------------|
| `--mode {onedir,onefile,debug}` | Build mode (default: onedir) |
| `--spec PATH` | Use a specific .spec file (overrides --mode) |
| `--skip-frontend` | Skip `bun run build` step |
| `--clean` | Remove `build/` and `dist/` before building |
| `--icon PATH` | Override application icon (.ico) |
| `--output-dir PATH` | Custom directory for build artifacts |

### Examples

```bash
# Full clean build as single exe with custom icon
uv run pywebvue build --clean --mode onefile --icon assets/my_icon.ico

# Quick rebuild (skip frontend, use previous build)
uv run pywebvue build --skip-frontend

# Custom output location
uv run pywebvue build --output-dir ./release
```

### Build Flow

```
1. [optional] Remove build/ and dist/ (--clean)
2. cd frontend && bun run build  (unless --skip-frontend)
3. pyinstaller --noconfirm my_app.spec
4. Output in dist/
```

### Adding PyInstaller as a Dev Dependency

```bash
uv add --dev pyinstaller
```

---

## 12. Examples

The `examples/` directory contains two complete, runnable projects:

### file-tool

A file processing tool that demonstrates:

- File drag-and-drop onto the window
- File metadata display (name, size, type, modified date)
- Simulated multi-step processing with progress bar
- Dark theme configuration
- Background thread processing with `run_in_thread()`

```bash
cd examples/file-tool
uv sync
cd frontend && bun install && cd ..
uv run main.py  --with-vite
```

Try: drag a file onto the window, view its metadata, click "Process File" to see progress.

### process-tool

A subprocess management tool that demonstrates:

- ProcessManager with start/pause/resume/stop/reset
- Real-time output logging in LogPanel
- StatusBadge for process state
- Timeout auto-stop (config: `process.default_timeout: 30`)
- Event-driven state synchronization

```bash
cd examples/process-tool
uv sync
cd frontend && bun install && cd ..
uv run main.py  --with-vite
```

Try: enter a command like `python -c "for i in range(10): print(f'line {i}'); import time; time.sleep(0.5)"`, click Start, then try Pause/Resume/Stop.

---

## 13. Troubleshooting

### "Frontend build not found: dist/index.html"

Run `cd frontend && bun run build` to build the frontend, or start Vite dev server first.

### "Vite Dev Server not reachable, falling back to production build"

Start Vite manually (`cd frontend && bun dev`) or use `--with-vite` flag.

### "PyInstaller is not installed"

```bash
uv add --dev pyinstaller
```

### Window opens but shows blank page

- Check that `dist/index.html` exists (run `cd frontend && bun run build`)
- Try running with `--mode debug` to see console errors

### Frontend API calls return "backend is not ready"

Make sure you call `waitForReady()` in `onMounted()` before making API calls.

### ProcessManager pause/resume doesn't work on some Linux distros

Pause/resume uses `SIGSTOP`/`SIGCONT` on Unix. These may not work for all process types. On Windows, `NtSuspendProcess`/`NtResumeProcess` is used via ctypes.

### "Another instance is already running" on startup

The singleton lock file may be stale (e.g., after a crash). The framework checks for stale locks automatically. If the issue persists, manually delete the lock file from your temp directory: `my_app.lock` in `%TEMP%` (Windows) or `/tmp` (Unix).

### bun install fails

Ensure bun is installed and accessible:
```bash
bun --version
```

If bun is not available, you can use npm instead:
```bash
cd frontend && npm install
```
