# PyWebVue

Minimal Python + Vue bridge framework based on [pywebview](https://github.com/r0x0r/pywebview).

Clone and develop -- no boilerplate.

## Quick Start

```bash
# 1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and [bun](https://bun.sh/) (or npm)
# 2. Clone and run
git clone <repo-url> && cd pywebvue-framework
dev.bat              # Windows
./dev.sh             # macOS / Linux
```

A native window opens with the Vue demo app.

## Project Structure

```
pywebvue-framework/
  main.py            # App entry point (edit this)
  app.spec           # PyInstaller build config
  build.py           # Packaging script (desktop + Android)
  dev.py             # Dev startup (Vite + app)
  dev.bat / dev.sh   # One-click launchers
  pywebvue/          # Framework source
    app.py             # App (window, dev/prod, lifecycle)
    bridge.py          # Bridge + @expose decorator
    __init__.py        # Public exports
  frontend/           # Vue app (Vite + TypeScript)
    index.html         # Vite entry
    src/App.vue        # Root component (edit this)
    src/main.ts        # Vue bootstrap
    src/bridge.ts      # Bridge: call(), onEvent(), waitForPyWebView()
```

## Development

```bash
uv run dev.py                    Start Vite dev server + app (default)
uv run dev.py --no-vite          Load frontend_dist/ from disk
uv run dev.py --setup            Only install dependencies
```

[Development details -> docs/development.md](docs/development.md)

## API

### Python

```python
from pywebvue import App, Bridge, expose

class MyApi(Bridge):
    @expose
    def greet(self, name: str) -> dict:
        return {"success": True, "data": f"Hello, {name}!"}

api = MyApi()
App(api, title="My App", frontend_dir="frontend_dist").run()
```

### Vue + TypeScript

```ts
import { call, onEvent, waitForPyWebView } from "../bridge"

await waitForPyWebView()

// JS -> Python
const res = await call<string>("greet", "World")

// Python -> JS
const off = onEvent<{ msg: string }>("status", ({ msg }) => console.log(msg))
off()
```

[Full API reference -> docs/api.md](docs/api.md)

## Packaging

```bash
cd frontend && npm run build   # Build Vue app -> frontend_dist/
uv run build.py                  # Desktop onedir
uv run build.py --onefile        # Desktop single exe
uv run build.py --android        # Android APK (macOS / Linux)
```

[Build configuration -> docs/building.md](docs/building.md)

## Requirements

- Python >= 3.10
- [uv](https://docs.astral.sh/uv/) (package manager)
- [bun](https://bun.sh/) or [npm](https://nodejs.org/) (frontend)
- pywebview >= 6.0 (auto-installed)

## License

MIT
