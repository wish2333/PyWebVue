# PyWebVue User Development Guide

## 1. Quick Start

### Prerequisites

- Python >= 3.10.8
- [uv](https://docs.astral.sh/uv/) - Python package manager
- [bun](https://bun.sh/) - JavaScript package manager

### Install

```bash
pip install pywebvue-framework
```

Or with uv:

```bash
uv add pywebvue-framework
```

### Scaffold a New Project

```bash
pywebvue create my_app --title "My Application"
cd my_app
```

This creates a complete project structure with Python backend, Vue 3 frontend, and PyInstaller spec files.

### Run in Development Mode

```bash
# Option 1: Connect to an already-running Vite dev server
uv run python main.py

# Option 2: Auto-start Vite dev server alongside the app
uv run python main.py --with-vite
```

### Build for Distribution

```bash
# Build frontend + package with PyInstaller (onedir mode)
uv run pywebvue build

# Skip frontend rebuild
uv run pywebvue build --skip-frontend

# Build as a single executable
uv run pywebvue build --mode onefile

# Clean build directories first
uv run pywebvue build --clean

# Custom icon
uv run pywebvue build --icon path/to/icon.ico
```

---

## 2. Project Structure

A scaffolded PyWebVue project looks like this:

```
my_app/
  main.py             # App entry point
  app.py              # Business API class
  config.yaml         # Application configuration
  pyproject.toml      # Python dependencies
  .gitignore
  my_app.spec         # PyInstaller spec (onedir)
  my_app-onefile.spec # PyInstaller spec (onefile)
  my_app-debug.spec   # PyInstaller spec (debug/console)
  frontend/
    package.json      # Node dependencies
    vite.config.ts    # Vite configuration
    tailwind.config.ts # Tailwind + DaisyUI config
    tsconfig.json     # TypeScript configuration
    index.html        # HTML entry
    src/
      main.ts         # Vue app mount
      App.vue         # Root component
      api.ts          # Backend API call wrapper
      event-bus.ts    # Event subscription composable
      types/index.ts  # TypeScript type definitions
      assets/style.css
      components/     # Pre-built UI components
        FileDrop.vue
        LogPanel.vue
        ProgressBar.vue
        StatusBadge.vue
        Toast.vue
  dist/               # Built frontend (generated)
    index.html
    assets/
```

---

## 3. Adding Business API Methods

All public methods (not prefixed with `_`) on your API class are automatically exposed to the frontend via pywebview's JS bridge.

### Example

```python
# app.py
from pywebvue import ApiBase, Result, ErrCode


class MyAppApi(ApiBase):
    def health_check(self) -> Result:
        return Result.ok(data={"status": "running"})

    def get_user(self, user_id: int) -> Result:
        # Your business logic here
        user = {"id": user_id, "name": "Alice"}
        return Result.ok(data=user)

    def validate_input(self, value: str) -> Result:
        if not value:
            return Result.fail(ErrCode.PARAM_INVALID, detail="Value cannot be empty")
        return Result.ok(data={"valid": True})
```

### Key Rules

- All public methods must return a `Result` object
- Return `Result.ok(data=...)` for success
- Return `Result.fail(code, detail=...)` for errors
- Parameters must be JSON-serializable types (str, int, float, bool, list, dict, None)
- The `ApiProxy` wrapper catches uncaught exceptions and returns `Result.fail(ErrCode.INTERNAL_ERROR)` automatically

---

## 4. Frontend-Backend Communication

### Calling Backend API Methods

```typescript
import { call } from "@/api";
import { isOk } from "@/types";

// Simple call
const result = await call<{ status: string }>("health_check");
if (isOk(result)) {
  console.log(result.data.status);
} else {
  console.error(result.msg);
}

// Call with arguments
const userResult = await call<{ name: string }>("get_user", 42);
```

### Listening for Backend Events

```typescript
import { useEvent } from "@/event-bus";

// Subscribe for component lifetime (auto-cleanup)
useEvent("log:add", (data) => {
  console.log(data);
});

// One-time event with timeout
import { waitForEvent } from "@/event-bus";

const result = await waitForEvent<{ path: string }>("file:process_complete", 30000);
```

### Emitting Events from Python

```python
class MyAppApi(ApiBase):
    def process_data(self, data: str) -> Result:
        self.emit("progress:update", {"current": 5, "total": 10})
        self.emit("log:add", {"level": "INFO", "message": "Processing..."})
        return Result.ok()
```

### Waiting for pywebview Readiness

```typescript
import { waitForReady } from "@/api";

onMounted(async () => {
  await waitForReady();
  // Backend is now available
});
```

---

## 5. Custom Error Codes

### Defining Custom Codes

```python
from pywebvue import ErrCode

# Add custom error codes for your application (start from 10000+)
ErrCode.USER_NOT_FOUND = 10001
ErrCode.INSUFFICIENT_PERMISSION = 10002

# Register messages
ErrCode._MSG[10001] = "user not found"
ErrCode._MSG[10002] = "insufficient permission"
```

### Using Custom Codes

```python
class MyAppApi(ApiBase):
    def find_user(self, name: str) -> Result:
        user = self._db.find(name)
        if not user:
            return Result.fail(ErrCode.USER_NOT_FOUND, detail=name)
        return Result.ok(data=user)
```

### Built-in Error Code Ranges

| Range | Module |
|-------|--------|
| 0 | Success |
| 1-5 | General errors |
| 1001-1006 | File system |
| 2001-2005 | Process management |
| 3001-3002 | Network / communication |

---

## 6. Subprocess Management (ProcessManager)

### Basic Usage

```python
from pywebvue import ApiBase, ProcessManager, Result


class MyAppApi(ApiBase):
    def __init__(self):
        super().__init__()
        self.pm = ProcessManager(self, name="encoder")

    def start_encode(self, input_file: str) -> Result:
        return self.pm.start(
            cmd=["ffmpeg", "-i", input_file, "output.mp4"],
            on_output=lambda line: self.logger.info(line),
            on_complete=lambda rc: self.logger.info(f"Exit code: {rc}"),
        )

    def pause_encode(self) -> Result:
        return self.pm.pause()

    def resume_encode(self) -> Result:
        return self.pm.resume()

    def stop_encode(self) -> Result:
        return self.pm.stop()

    def reset_encode(self) -> Result:
        """Reset to IDLE state, allowing a new start()."""
        return self.pm.reset()
```

### State Machine

```
IDLE -> RUNNING -> PAUSED -> RUNNING (resume)
                 -> STOPPED -> IDLE (reset)
IDLE -> RUNNING -> STOPPED -> IDLE (auto-reset on next start)
```

### Timeout

```python
# Explicit timeout (seconds)
self.pm.start(cmd=["long_task"], timeout=60)

# Uses process.default_timeout from config.yaml if no explicit timeout
# config.yaml:
#   process:
#     default_timeout: 300
```

When timeout triggers:
- Event `process:{name}:timeout` is emitted
- Process is auto-stopped
- State transitions to STOPPED

### Multi-Instance

```python
# Multiple named ProcessManagers in the same API class
self.encoder_pm = ProcessManager(self, name="encoder")
self.uploader_pm = ProcessManager(self, name="uploader")
```

### Events Emitted

| Event | Payload | When |
|-------|---------|------|
| `process:{name}:output` | `{"line": "..."}` | Each stdout/stderr line |
| `process:{name}:complete` | `{"returncode": int}` | Process exits |
| `process:{name}:timeout` | `{"timeout": int}` | Timeout reached |

---

## 7. Configuration Reference (config.yaml)

```yaml
app:
  name: "my_app"           # Python identifier (used for spec files)
  title: "My App"          # Window title
  width: 900               # Window width (pixels)
  height: 650              # Window height (pixels)
  min_size: [600, 400]     # Minimum window size
  max_size: [1920, 1080]   # Maximum window size
  resizable: true          # Allow window resize
  icon: "assets/icon.ico"  # App icon path
  singleton: false         # Prevent multiple instances
  centered: true           # Center window on screen
  theme: light             # DaisyUI theme (light/dark)

  dev:
    enabled: true          # Connect to Vite dev server if available
    vite_port: 5173        # Vite dev server port
    debug: true            # Enable pywebview debug mode

logging:
  level: INFO              # Log level (DEBUG/INFO/WARNING/ERROR/CRITICAL)
  console: true            # Print logs to console
  to_frontend: true        # Forward logs to frontend LogPanel
  file: ""                 # Log file path (empty = disabled)
  max_lines: 1000          # Max log entries in frontend buffer

process:
  default_timeout: 300     # Default subprocess timeout (seconds)

business: {}               # Custom business configuration (access via config.business)
```

---

## 8. Development Mode (Vite HMR)

### Option A: Manual Vite Start

```bash
# Terminal 1: Start Vite dev server
cd frontend && bun dev

# Terminal 2: Start Python app (connects to Vite)
uv run python main.py
```

The app auto-detects the running Vite server via `dev.enabled: true` in config.yaml.

### Option B: Auto-Start Vite

```bash
# Start Vite automatically, then launch the app
uv run python main.py --with-vite
```

This starts the Vite dev server in the background and waits for it to be ready before launching the window.

### How It Works

1. When `dev.enabled` is `true`, the app checks if `http://localhost:{vite_port}` is reachable
2. If reachable, it loads the app from the Vite dev server (with HMR)
3. If not reachable, it falls back to the production build in `dist/`

---

## 9. Packaging & Distribution

### PyInstaller Build Modes

| Mode | Spec File | Output |
|------|-----------|--------|
| `onedir` | `my_app.spec` | Folder containing exe + dependencies |
| `onefile` | `my_app-onefile.spec` | Single executable |
| `debug` | `my_app-debug.spec` | Console window visible (for debugging) |

### CLI Build Command

```bash
# Default: onedir mode
uv run pywebvue build

# Other modes
uv run pywebvue build --mode onefile
uv run pywebvue build --mode debug

# Custom spec file
uv run pywebvue build --spec custom.spec

# Clean build
uv run pywebvue build --clean

# Custom icon
uv run pywebvue build --icon assets/my_icon.ico

# Custom output directory
uv run pywebvue build --output-dir ./release

# Skip frontend build (use previously built dist/)
uv run pywebvue build --skip-frontend
```

### Build Flow

1. `--clean` (optional): Remove `build/` and `dist/`
2. Frontend build: `bun run build` in `frontend/` (unless `--skip-frontend`)
3. PyInstaller: Runs with the selected spec file
4. Output: Executable in `dist/`

---

## 10. Pre-built Components

### FileDrop

Drag-and-drop file zone. Displays dropped file paths and optionally emits events.

```vue
<FileDrop />
```

Requires the `toast` inject: `provide("toast", { showToast })`.

### LogPanel

Displays real-time log entries from the backend. Supports level filtering, auto-scroll, and clear.

```vue
<LogPanel />
```

Subscribes to `log:add` events automatically.

### ProgressBar

Displays a progress bar with percentage and label.

```vue
<ProgressBar :progress="progressData" />
```

Props: `progress: ProgressPayload | null` where `ProgressPayload = { current: number; total: number; label?: string }`.

### StatusBadge

Displays a colored badge indicating a status state.

```vue
<StatusBadge status="running" />
```

Props: `status: "idle" | "running" | "paused" | "error" | "done"`.

### Toast

Auto-dismissing toast notifications.

```vue
<Toast :items="toastQueue" @dismiss="removeToast" />
```

Props: `items: ToastOptions[]`. Events: `dismiss(index: number)`.

```typescript
// Setup in App.vue
let _toastId = 0;
const toastQueue = reactive<ToastOptions[]>([]);

function showToast(options: ToastOptions) {
  toastQueue.push({ ...options, id: ++_toastId });
}

provide("toast", { showToast });
```

---

## Examples

See the `examples/` directory for complete working projects:

- **file-tool**: File drag-drop, metadata display, simulated processing with progress. Demonstrates `on_file_drop`, `emit` events, and background thread processing.

- **process-tool**: Subprocess management with start/pause/resume/stop controls. Demonstrates `ProcessManager`, timeout, state machine, and real-time output logging.
