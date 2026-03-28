# PyWebVue

Desktop rapid development framework for Python developers.

[PyWebView](https://pywebview.flowrl.com/) + [Vue 3](https://vuejs.org/) + [DaisyUI](https://daisyui.com/) + [TypeScript](https://www.typescriptlang.org/)

---

## Features

- **Project scaffolding** -- `pywebvue create my_app` generates a complete project with Python backend, Vue 3 frontend, and PyInstaller spec files
- **Hot module replacement** -- Vite dev server with instant frontend updates
- **Frontend-Backend bridge** -- Call Python methods from TypeScript, push events from Python to Vue
- **Global exception handling** -- Uncaught Python exceptions return `Result.fail()` instead of crashing the app
- **Real-time logging** -- Backend logs appear in the frontend LogPanel automatically
- **File drag-and-drop** -- Drag files onto the window, handled by your Python code
- **Subprocess management** -- Start / pause / resume / stop subprocesses with timeout support
- **Native dialogs** -- File open, folder select, save-as dialogs via pywebview
- **Single-instance lock** -- Cross-platform file-based lock to prevent duplicate launches
- **PyInstaller packaging** -- One-click build to `.exe` (onedir, onefile, or debug modes)

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | >= 3.10.8 | Runtime |
| [uv](https://docs.astral.sh/uv/) | Latest | Package manager |
| [bun](https://bun.sh/) | Latest | Frontend package manager |

## Quick Start

### Install

```bash
# Add to an existing project
uv add pywebvue-framework

# Or install globally
pip install pywebvue-framework
```

### Scaffold and Run

```bash
pywebvue create my_app --title "My Application"
cd my_app
uv sync
cd frontend && bun install && cd ..
uv run python main.py --with-vite
```

### Build for Distribution

```bash
uv run pywebvue build                     # folder output (default)
uv run pywebvue build --mode onefile      # single executable
uv run pywebvue build --clean --icon app.ico
```

## How It Works

```
Python Backend                    Frontend
+------------------+   JS Bridge   +------------------+
| app.py           | <-----------> | App.vue           |
|   class MyApi   |   call<T>()  |   call("method") |
|     def foo()   |              |                  |
|       -> Result |   emit()     |   useEvent()     |
|     self.emit() | -----------> |   onMounted()    |
+------------------+              +------------------+
         |
    pywebview window (native OS window)
```

Write business logic in Python (`app.py`), UI in Vue 3 (`frontend/src/`), and the framework handles the rest.

**Backend** -- Subclass `ApiBase`, define public methods that return `Result`:

```python
from pywebvue import ApiBase, Result

class MyApi(ApiBase):
    def get_data(self, id: int) -> Result:
        return Result.ok(data={"id": id, "name": "Alice"})
```

**Frontend** -- Call backend methods, subscribe to events:

```typescript
import { call } from "@/api";
import { isOk } from "@/types";

const result = await call<{ name: string }>("get_data", 42);
if (isOk(result)) {
  console.log(result.data.name);
}
```

## CLI Reference

### `pywebvue create`

```bash
pywebvue create <name> [--title TITLE] [--width 1024] [--height 768] [--force]
```

### `pywebvue build`

```bash
pywebvue build [--mode onedir|onefile|debug] [--skip-frontend] [--clean] [--icon PATH] [--output-dir PATH]
```

## Project Structure (scaffolded)

```
my_app/
  main.py                  # Entry point
  app.py                   # Business API (ApiBase subclass)
  config.yaml              # Application settings
  pyproject.toml           # Python dependencies
  my_app.spec              # PyInstaller spec (onedir)
  my_app-onefile.spec      # PyInstaller spec (onefile)
  my_app-debug.spec        # PyInstaller spec (debug)
  frontend/
    src/
      App.vue              # Root component
      api.ts               # Backend API call helper
      event-bus.ts         # Event subscription helpers
      types/index.ts       # TypeScript types + ErrCode
      components/          # Pre-built UI components
        FileDrop.vue       # Drag-and-drop zone
        LogPanel.vue       # Real-time log viewer
        ProgressBar.vue    # Progress bar with label
        StatusBadge.vue    # State indicator badge
        DataTable.vue      # Data table
        Toast.vue          # Auto-dismissing notifications
```

## Configuration (config.yaml)

```yaml
app:
  name: "my_app"
  title: "My App"
  width: 900
  height: 650
  min_size: [600, 400]
  resizable: true
  icon: "assets/icon.ico"
  singleton: false
  theme: light                    # DaisyUI theme (light / dark)
  dev:
    enabled: true                # Auto-detect Vite dev server
    vite_port: 5173
    debug: true
logging:
  level: INFO
  console: true
  to_frontend: true              # Forward logs to LogPanel
  file: ""
process:
  default_timeout: 300           # Subprocess timeout (seconds)
business: {}                      # Custom key-value config
```

## Framework Modules

| Module | Description |
|--------|-------------|
| `App` | Window lifecycle, Vite integration, drag-drop |
| `ApiBase` | Base class for user business APIs |
| `Result` / `ErrCode` | Standardized return type and error codes |
| `ProcessManager` | Subprocess state machine with pause/resume/timeout |
| `EventBus` | Python-to-frontend event dispatch |
| `Dialog` | Native file/folder/save dialogs |
| `Logger` | Dual-channel logging (console + frontend) |
| `Config` | YAML configuration loading |
| `SingletonLock` | Cross-platform single-instance lock |

## Examples

The `examples/` directory contains two complete projects (run via `uv workspace`):

| Example | Demonstrates |
|---------|-------------|
| **file-tool** | File drag-drop, metadata display, simulated processing with progress bar, dark theme |
| **process-tool** | Subprocess start/pause/resume/stop/reset, timeout, real-time log output, StatusBadge |

```bash
cd examples/file-tool
uv sync
uv run main.py --with-vite
```

## Documentation

| Document | Audience | Content |
|----------|----------|---------|
| `docs/user-guide.md` | Users | Installation, scaffolding, configuration, packaging, troubleshooting |
| `docs/development-guide.md` | Developers | Architecture walkthrough, patterns, component reference (with examples) |
| `docs/user-guide-zh.md` | Users (Chinese) | Chinese translation of user guide |
| `docs/development-guide-zh.md` | Developers (Chinese) | Chinese translation of development guide |
| `to_ai/pywebvue-framework-instruction.md` | AI Agents | Complete AI-facing development instructions |

## License

MIT
