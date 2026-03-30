# API Reference

## Python

### `App`

```python
from pywebvue import App
```

Creates a pywebview window wired to a Bridge instance.

#### Constructor

```python
App(
    bridge: Bridge,
    *,
    title: str = "App",
    width: int = 800,
    height: int = 600,
    min_size: tuple[int, int] = (600, 400),
    frontend_dir: str = "frontend_dist",
    dev_url: str = "http://localhost:5173",
)
```

| Param | Default | Description |
|---|---|---|
| `bridge` | -- | Your `Bridge` subclass instance |
| `title` | `"App"` | Window title |
| `width` | `800` | Window width in pixels |
| `height` | `600` | Window height in pixels |
| `min_size` | `(600, 400)` | Minimum window size |
| `frontend_dir` | `"frontend_dist"` | Directory containing `index.html` (used when `dev=False`) |
| `dev_url` | `"http://localhost:5173"` | Vite dev server URL (used when `dev=True`) |

#### `run(dev=None, *, debug=None)`

Create the window and start the event loop.

| Param | Default | Description |
|---|---|---|
| `dev` | `None` | `True` = Vite dev server, `False` = disk, `None` = auto (dev when not frozen) |
| `debug` | `None` | Open developer tools. `None` = auto (True when not frozen) |

```python
app.run()           # auto-detect: dev + debug when not frozen, prod when frozen
app.run(dev=False)  # force load from disk (still opens devtools in dev env)
app.run(dev=True, debug=False)  # force connect to Vite, no devtools
```

#### `emit(event, data=None)`

Push an event to the frontend. Dispatches a `CustomEvent` named `pywebvue:{event}`.

```python
app.emit("progress", {"percent": 50})
```

#### `dev` (property)

`True` when not running inside a PyInstaller bundle.

---

### `Bridge`

```python
from pywebvue import Bridge
```

Base class for Python APIs exposed to the frontend.

```python
class MyApi(Bridge):
    def __init__(self):
        super().__init__()
        # self._window is set automatically by App

    @expose
    def my_method(self, arg: str) -> dict:
        return {"success": True, "data": f"got {arg}"}

    def push_to_frontend(self):
        self._emit("my_event", {"key": "value"})
```

#### `_emit(event, data=None)`

Dispatch a `CustomEvent` named `pywebvue:{event}` to the frontend. The `data` is serialized to JSON and attached as `event.detail`.

#### `get_dropped_files()`

Return file paths from the most recent drag-and-drop event and clear the buffer.

```python
result = self.get_dropped_files()
# result = {"success": True, "data": ["/path/to/file1.txt", ...]}
```

---

### `@expose`

```python
from pywebvue import expose
```

Decorator that wraps a Bridge method with try/except. If the method raises an exception, it returns `{"success": False, "error": "..."}` instead of crashing.

```python
@expose
def divide(self, a: float, b: float) -> dict:
    return {"success": True, "data": a / b}
    # If b == 0, returns {"success": False, "error": "division by zero"}
```

**Convention**: exposed methods should return `{"success": True, "data": ...}`.

---

## TypeScript (Vue)

The bridge functions live in `frontend/src/bridge.ts` and are imported directly in Vue components.

```ts
import { call, onEvent, waitForPyWebView } from "./bridge"
```

### `call<T>(method, ...args): Promise<ApiResponse<T>>`

Call an `@expose`-decorated Python method.

```ts
const res = await call<string>("greet", "World")
if (res.success) {
    console.log(res.data)  // "Hello, World!"
}
```

### `onEvent<T>(name, handler): () => void`

Listen for events dispatched by `Bridge._emit()`. Returns a cleanup function.

```ts
const off = onEvent<{ percent: number }>("progress", ({ percent }) => {
    console.log(`${percent}%`)
})
// Later: off() to remove listener
```

### `waitForPyWebView(timeout?: number): Promise<void>`

Poll until `window.pywebview.api` is populated. Default timeout: 10 seconds.

```ts
await waitForPyWebView()
// Bridge is ready, safe to call Python methods
```

### `ApiResponse<T>`

```ts
interface ApiResponse<T = unknown> {
    success: boolean
    data?: T
    error?: string
}
```

---

## Response Convention

All Python -> JS communication uses a consistent envelope:

```json
{"success": true, "data": <any>}
```

On error (automatic via `@expose` or manual):

```json
{"success": false, "error": "description of what went wrong"}
```
