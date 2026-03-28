# PyWebVue Framework - 开发指南

> 本文档基于 `docs/PRD-2026-03-28.md` 需求文档，拆分为可执行的开发任务清单。
> 按阶段顺序逐步实现，每个阶段结束后可手动验证。

---

## 当前项目状态

项目目前仅有骨架：
- `pyproject.toml` - 已声明 `pywebview>=6.1` 依赖
- `main.py` - 占位入口
- `docs/PRD-2026-03-28.md` - 需求规格文档
- `frontend/` - 空目录

---

## Phase 1: 框架核心模块

> 目标：实现框架的 Python 核心，不含脚手架和前端模板。
> 完成后框架可作为 Python 包被引用。

### 1.1 项目结构搭建

**任务**：创建框架包目录结构。

```
src/pywebvue/
    __init__.py
    constants.py
    result.py
    config.py
    logger.py
    event_bus.py
    dialog.py
    singleton.py
    process.py
    api_base.py
    app.py
```

**操作步骤**：

1. 创建 `src/` 和 `src/pywebvue/` 目录
2. 修改 `pyproject.toml`，添加包配置：

```toml
[project]
name = "pywebvue-framework"
version = "0.1.0"
description = "Desktop rapid development framework for Python developers (PyWebView + Vue + DaisyUI)"
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
    "pywebview>=5.0",
    "loguru>=0.7",
    "pyyaml>=6.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/pywebvue"]
```

3. 添加框架依赖：
```bash
uv add loguru pyyaml
```

**验证**：`uv run python -c "import pywebvue; print(pywebvue.__version__)"` 能正常输出。

---

### 1.2 constants.py - 框架常量

**文件**：`src/pywebvue/constants.py`

**内容**：
- `__version__` = "0.1.0"
- `DEFAULT_CONFIG_FILE` = "config.yaml"
- `DEV_SERVER_HOST` = "localhost"
- `DEFAULT_VITE_PORT` = 5173
- `DIST_DIR` = "dist"
- `FRONTEND_ENTRY` = "index.html"
- 前端 JS 桥接函数名 `DISPATCH_FN` = "__pywebvue_dispatch"

---

### 1.3 result.py - Result + ErrCode

**文件**：`src/pywebvue/result.py`

**实现要点**：

1. **ErrCode 类** - 错误码定义，全部为类属性（int 常量）：
   - `OK = 0`
   - `UNKNOWN = 1`, `PARAM_INVALID = 2`, `NOT_IMPLEMENTED = 3`, `TIMEOUT = 4`, `INTERNAL_ERROR = 5`
   - `FILE_NOT_FOUND = 1001`, `FILE_READ_ERROR = 1002`, `FILE_WRITE_ERROR = 1003`, `FILE_FORMAT_INVALID = 1004`, `FILE_TOO_LARGE = 1005`, `PATH_NOT_ACCESSIBLE = 1006`
   - `PROCESS_START_FAILED = 2001`, `PROCESS_ALREADY_RUNNING = 2002`, `PROCESS_NOT_RUNNING = 2003`, `PROCESS_TIMEOUT = 2004`, `PROCESS_KILLED = 2005`
   - `API_CALL_FAILED = 3001`, `API_NOT_READY = 3002`

2. **ErrCode.to_msg(code) -> str** - 类方法，错误码转默认英文消息，内部用 dict 映射

3. **ErrCode.is_user_error(code) -> bool** - 类方法，判断是否为用户操作引起的错误

4. **Result dataclass**：
   - 字段：`code: int`, `msg: str`, `data: Any`
   - `ok(data, msg)` 类方法 - 创建成功结果
   - `fail(code, detail, msg)` 类方法 - 创建失败结果，detail 放入 data
   - `is_ok` 属性 - `code == ErrCode.OK`
   - `to_dict()` 方法 - 返回可序列化 dict

**注意**：Result 需要可被 pywebview 序列化为 JSON，所以 `data` 字段只能是 JSON 兼容类型。`to_dict()` 需要处理 data 中非标准类型（如 Path 对象）的转换。

---

### 1.4 config.py - 配置加载

**文件**：`src/pywebvue/config.py`

**实现要点**：

1. 使用 `dataclasses` 定义配置结构：

```python
@dataclass
class DevConfig:
    enabled: bool = True
    vite_port: int = 5173
    debug: bool = True

@dataclass
class LoggingConfig:
    level: str = "INFO"
    console: bool = True
    to_frontend: bool = True
    file: str = ""
    max_lines: int = 1000

@dataclass
class ProcessConfig:
    default_timeout: int = 300

@dataclass
class AppConfig:
    name: str = "my_app"
    title: str = "My App"
    width: int = 900
    height: int = 650
    min_size: tuple = (600, 400)
    max_size: tuple = (1920, 1080)
    resizable: bool = True
    icon: str = "assets/icon.ico"
    singleton: bool = False
    centered: bool = True
    theme: str = "light"
    dev: DevConfig = field(default_factory=DevConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    process: ProcessConfig = field(default_factory=ProcessConfig)
    business: dict = field(default_factory=dict)
```

2. `load_config(path: str) -> AppConfig` 函数：
   - 用 `yaml.safe_load` 读取 YAML 文件
   - 将 dict 映射到 AppConfig dataclass
   - 文件不存在时返回默认配置，打印 warning
   - 嵌套字段（dev, logging, process）分别解析
   - `business` 字段直接透传为 dict

**config.yaml 格式参考 PRD 第 F-012 节**。

---

### 1.5 logger.py - 日志系统

**文件**：`src/pywebvue/logger.py`

**实现要点**：

1. `setup_logger(config: LoggingConfig, emit_callback=None)` 函数：
   - `logger.remove()` 移除 loguru 默认 sink
   - 根据 `config.console` 决定是否添加 stderr sink（彩色格式化输出）
   - 根据 `config.to_frontend` 决定是否添加前端 sink（调用 emit_callback 推送日志）
   - 根据 `config.file` 决定是否添加文件 sink（带 rotation="10 MB", retention="7 days"）
   - 日志级别使用 `config.level`

2. 前端 sink 的实现：
   - 定义一个 `_frontend_sink(message)` 函数
   - 将 loguru Record 格式化为 JSON：`{"level": level, "message": text, "time": timestamp}`
   - 调用 `emit_callback("log:add", payload)` 推送到前端
   - emit_callback 可能为 None（窗口未就绪时），需判空

3. 控制台格式：
   ```
   <green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>
   ```

**注意**：`emit_callback` 是从外部注入的，因为 logger 初始化时窗口可能还未创建。后续 App 类中会在窗口就绪后更新此回调。

---

### 1.6 event_bus.py - 事件总线

**文件**：`src/pywebvue/event_bus.py`

**实现要点**：

1. `EventBus` 类：
   - 接收 `window` 参数（pywebview 窗口引用）
   - `emit(event_name: str, data: Any = None)` 方法：
     - 将 data 序列化为 JSON（`json.dumps`，确保 ASCII safe）
     - 调用 `self.window.evaluate_js(f'__pywebvue_dispatch("{event_name}", {json_str})')`
     - 异常捕获：窗口未就绪时静默忽略或记录 warning
   - 序列化时处理特殊情况：`data=None` 时传 `{}`

2. 前端桥接 JS（将被注入到 index.html 的 script 标签中）：
   ```javascript
   window.__pywebvue_event_listeners = {};
   window.__pywebvue_dispatch = function(eventName, payload) {
       var listeners = window.__pywebvue_event_listeners[eventName];
       if (listeners) {
           listeners.forEach(function(cb) { cb(payload); });
       }
   };
   window.pywebvue = window.pywebvue || {};
   window.pywebvue.event = {
       on: function(name, callback) {
           if (!window.__pywebvue_event_listeners[name]) {
               window.__pywebvue_event_listeners[name] = [];
           }
           window.__pywebvue_event_listeners[name].push(callback);
       },
       off: function(name, callback) {
           if (!window.__pywebvue_event_listeners[name]) return;
           window.__pywebvue_event_listeners[name] =
               window.__pywebvue_event_listeners[name].filter(function(cb) { return cb !== callback; });
       }
   };
   ```

**这个 JS 代码块需要能被 app.py 或 app.py 在窗口创建后注入到前端**。将其定义为 `BRIDGE_JS` 常量字符串放在 event_bus.py 中。

---

### 1.7 dialog.py - 系统对话框封装

**文件**：`src/pywebvue/dialog.py`

**实现要点**：

1. `Dialog` 类：
   - 接收 `window` 参数（pywebview 窗口引用）
   - `open_file(title, file_types, folder, multiple)` 方法：
     - 调用 `self.window.create_file_dialog(dialog.OPEN_DIALOG, ...)`
     - `file_types` 格式转换：pywebview 使用 `(("Description", "*.ext"),)` 格式
     - 返回选中路径或 None
   - `open_folder(title)` 方法：
     - 调用 `self.window.create_file_dialog(dialog.FOLDER_DIALOG)`
   - `save_file(title, default_name, file_types)` 方法：
     - 调用 `self.window.create_file_dialog(dialog.SAVE_DIALOG, ...)`
   - 所有方法返回 `str | list[str] | None`，ApiBase 层负责包装为 Result

**注意**：pywebview 的文件对话框 API 在不同版本有差异，参考 pywebview 5.0+ 文档。

---

### 1.8 singleton.py - 单实例锁

**文件**：`src/pywebvue/singleton.py`

**实现要点**：

1. `SingletonLock` 类：
   - `__init__(app_name: str)` - 基于 app_name 生成锁文件路径
   - `acquire() -> bool` - 尝试获取锁，成功返回 True
   - `release()` - 释放锁
   - `__enter__` / `__exit__` - 支持 with 语句

2. 跨平台实现：
   - **Windows**：使用 `msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)`
   - **Unix**：使用 `fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)`
   - 锁文件位置：`os.path.join(tempfile.gettempdir(), f"{app_name}.lock")`
   - 锁文件中写入当前 PID，用于异常退出后检测清理

3. 已有实例运行时的行为：
   - 读取锁文件中的 PID
   - 检查该进程是否仍在运行（`os.kill(pid, 0)`）
   - 如果进程已死，清理锁文件并获取新锁
   - 如果进程仍活着，返回 False

---

### 1.9 process.py - 子进程管理器

**文件**：`src/pywebvue/process.py`

**实现要点**：

1. **状态枚举**：`IDLE`, `RUNNING`, `PAUSED`, `STOPPED`

2. `ProcessManager` 类：
   - `__init__(api_base, name="default")` - 绑定 ApiBase 实例用于 emit
   - `start(cmd, cwd, on_output, on_complete)` 方法：
     - 检查当前状态，非 IDLE 时返回错误
     - 使用 `subprocess.Popen` 启动进程
     - 创建后台守护线程逐行读取 stdout/stderr
     - 每行输出自动 emit `process:{name}:output` 事件
     - 进程结束后调用 `on_complete(returncode)` 并 emit `process:{name}:complete` 事件
   - `pause() -> Result`：
     - Windows：`CREATE_NEW_PROCESS_GROUP` + `CTRL_BREAK_EVENT`（或 `SuspendThread`）
     - Unix：`os.kill(pid, signal.SIGSTOP)`
     - 更新状态为 PAUSED
   - `resume() -> Result`：
     - Windows：`ResumeThread`
     - Unix：`os.kill(pid, signal.SIGCONT)`
   - `stop() -> Result`：
     - `process.terminate()`，等待 5 秒后 `process.kill()`
   - 属性：`is_running`, `is_paused`, `pid`, `state`

3. **多实例支持**：
   - `ProcessManager.create(api_base, name)` 类方法（可选，后续迭代）
   - 事件名自动带上 name 前缀

4. **线程安全**：
   - 所有状态变更通过 `threading.Lock` 保护
   - Popen 对象的访问通过锁保护

**注意**：Windows 上进程暂停/恢复的实现比较特殊，需要用 `ctypes` 调用 Win32 API（`SuspendThread`/`ResumeThread`），因为 `CTRL_BREAK_EVENT` 对所有进程组生效。PRD 中提到的 `CREATE_NEW_PROCESS_GROUP` 方案需要进一步调研可行性。

---

### 1.10 api_base.py - 业务 API 基类

**文件**：`src/pywebvue/api_base.py`

**实现要点**：

1. `ApiBase` 类：
   - `__init__()`：
     - 初始化 `_window = None`、`_config = None`
     - 创建 `EventBus` 实例（暂不绑定 window）
     - 创建 `Dialog` 实例（暂不绑定 window）
     - 创建 logger（使用 loguru 的 `logger.bind(class_name=self.__class__.__name__)`）
   - `bind_window(window)` - 框架调用，绑定 pywebview 窗口引用：
     - 设置 `self._window = window`
     - 更新 EventBus 和 Dialog 的 window 引用
     - 注入前端桥接 JS：`window.evaluate_js(BRIDGE_JS)`
   - `bind_config(config)` - 框架调用，绑定配置对象
   - 属性 `window` - 返回 `_window`
   - 属性 `config` - 返回 `_config`
   - 属性 `logger` - 返回绑定了类名的 loguru logger
   - 属性 `emit(event, data)` - 代理到 EventBus.emit
   - 属性 `dialog` - 返回 Dialog 实例
   - `run_in_thread(func, *args, **kwargs)` - 在后台线程中运行函数，返回 threading.Thread
   - `on_file_drop(file_paths)` - 空方法，用户按需覆盖

2. **全局异常拦截**：
   - 当 pywebview 调用 API 方法时，如果方法抛出异常，pywebview 默认会将异常信息返回前端
   - 需要在 App 类中实现代理层：对每个 API 方法的调用进行 try-except 包装
   - 捕获到异常时返回 `Result.fail(ErrCode.INTERNAL_ERROR, detail=str(e))`
   - 同时通过 logger 记录异常堆栈

---

### 1.11 app.py - 应用入口类

**文件**：`src/pywebvue/app.py`

**实现要点**：

1. `App` 类：
   - `__init__(config_path="config.yaml")`：
     - 调用 `load_config(config_path)` 加载配置
     - 调用 `setup_logger(config.logging, emit_callback=self._emit_callback)`
     - 单实例锁检测（如 `config.singleton` 为 True）
     - 自动发现并实例化当前模块中的 ApiBase 子类（或通过参数传入）
   - `run()` 方法：
     - 确定前端 URL：开发模式用 `http://localhost:{port}`，生产模式用 `dist/index.html` 的绝对路径
     - 创建 pywebview 窗口（标题、尺寸、图标、是否可调整大小等从 config 读取）
     - 在窗口 loaded 回调中：
       - 绑定 window 到 ApiBase 实例
       - 注入前端桥接 JS
     - 注册文件拖拽事件（pywebview 5.0+）
     - `webview.start(debug=config.dev.debug, http_server=False)`
   - `_emit_callback(event, data)` - 给 logger 的前端 sink 使用
   - `_on_window_loaded()` - 窗口加载完成回调
   - `_create_window(url)` - 创建窗口，返回 window 实例

2. **API 代理层**（全局异常拦截）：
   - 不直接将 ApiBase 实例传给 pywebview
   - 创建一个代理类/代理对象，包装所有 ApiBase 方法
   - 每个方法调用时 try-except，异常时返回 Result.fail
   - `webview.create_window(..., js_api=proxy_instance)`

3. **自动发现 ApiBase**：
   - 方案A（推荐）：`App.__init__` 接受 `api_class` 或 `api_instance` 参数
   - 方案B：扫描 app.py 模块中继承 ApiBase 的类并自动实例化
   - PRD 中 main.py 的用法是 `App(config="config.yaml")`，所以需要自动发现

4. **自动发现策略**：
   - `App.__init__` 中动态导入当前工作目录的 `app.py` 模块
   - 扫描模块中所有继承 ApiBase 的类
   - 如果只有一个，自动实例化；如果有多个，提示用户指定
   - 如果没有，使用空的默认 ApiBase

5. **开发模式检测**：
   - `config.dev.enabled` 为 True 时，检查 `http://localhost:{vite_port}` 是否可达
   - 如果可达，使用 Vite Dev Server URL
   - 如果不可达，fallback 到 dist/index.html 并打印 warning

6. **前端桥接 JS 注入时机**：
   - `window.loaded` 回调触发后
   - `window.evaluate_js(BRIDGE_JS)`

---

### 1.12 __init__.py - 公开 API

**文件**：`src/pywebvue/__init__.py`

```python
from .result import Result, ErrCode
from .api_base import ApiBase
from .app import App
from .process import ProcessManager
from .config import AppConfig, load_config
from .event_bus import EventBus
from .logger import setup_logger
from .dialog import Dialog
from .singleton import SingletonLock

__version__ = "0.1.0"
```

---

### Phase 1 验证清单

完成 Phase 1 后，按以下步骤手动验证：

1. 包导入验证：
   ```bash
   uv run python -c "from pywebvue import App, ApiBase, Result, ErrCode; print('OK')"
   ```

2. Result/ErrCode 验证：
   ```bash
   uv run python -c "
   from pywebvue import Result, ErrCode
   r = Result.ok(data={'version': '1.0'})
   assert r.is_ok
   assert r.code == 0
   r2 = Result.fail(ErrCode.FILE_NOT_FOUND, detail='/tmp/test.txt')
   assert not r2.is_ok
   assert r2.msg == 'file not found'
   print('Result/ErrCode OK')
   "
   ```

3. Config 加载验证：
   - 创建一个测试用的 `config.yaml`
   ```bash
   uv run python -c "
   from pywebvue import load_config
   c = load_config('config.yaml')
   print(c.title, c.width, c.height)
   "
   ```

4. Logger 验证：
   ```bash
   uv run python -c "
   from pywebvue import setup_logger
   from loguru import logger
   from pywebvue.config import LoggingConfig
   setup_logger(LoggingConfig())
   logger.info('Test log message')
   logger.error('Error message')
   print('Logger OK')
   "
   ```

5. 单实例锁验证：
   ```bash
   # Terminal 1:
   uv run python -c "
   from pywebvue import SingletonLock
   lock = SingletonLock('test_app')
   assert lock.acquire(), 'Should acquire lock'
   print('Lock acquired, press Enter to release...')
   input()
   lock.release()
   "

   # Terminal 2 (while Terminal 1 is waiting):
   uv run python -c "
   from pywebvue import SingletonLock
   lock = SingletonLock('test_app')
   assert not lock.acquire(), 'Should fail to acquire lock'
   print('Correctly failed to acquire lock (instance already running)')
   "
   ```

6. 最小窗口启动验证：
   - 创建一个最小 `main.py` 和 `app.py`：
   ```python
   # main.py
   from pywebvue import App
   app = App(config="config.yaml")
   app.run()
   ```
   ```python
   # app.py
   from pywebvue import ApiBase, Result

   class MyApi(ApiBase):
       def health_check(self) -> Result:
           return Result.ok(data={"status": "ok"})
   ```
   - 创建 `config.yaml`，`dev.enabled: false`
   - 在 `frontend/dist/` 下放一个简单的 `index.html`
   - 运行 `uv run main.py`，确认窗口正常弹出

---

## Phase 2: 脚手架 + 前端模板

> 目标：实现 `pywebvue create` 命令和完整的前端工程模板。

### 2.1 脚手架 CLI

**文件**：`src/pywebvue/cli.py`

**实现要点**：

1. 使用 `argparse` 或 `click` 实现 CLI：
   ```bash
   pywebvue create <project_name> [--title "My Tool"] [--width 900] [--height 650]
   ```

2. `create` 命令逻辑：
   - 校验 project_name（合法 Python 标识符，目录不存在）
   - 读取 `templates/project/` 目录下的所有模板文件
   - 对每个 `.tpl` 文件进行变量替换：
     - `{{PROJECT_NAME}}` -> project_name
     - `{{PROJECT_TITLE}}` -> title 参数
     - `{{WIDTH}}` -> width 参数
     - `{{HEIGHT}}` -> height 参数
   - 替换后去掉 `.tpl` 后缀，写入目标目录
   - 递归复制非模板文件（如 `icon.ico`）
   - 执行 `cd frontend && bun install` 安装前端依赖

3. 将 CLI 入口注册到 `pyproject.toml`：
   ```toml
   [project.scripts]
   pywebvue = "pywebvue.cli:main"
   ```

**模板文件清单**（参考 PRD 第四节）：

| 源模板 | 目标文件 | 说明 |
|:---|:---|:---|
| `templates/project/pyproject.toml.tpl` | `pyproject.toml` | 用户项目配置 |
| `templates/project/main.py.tpl` | `main.py` | 入口文件 |
| `templates/project/app.py.tpl` | `app.py` | 业务 API 示例 |
| `templates/project/config.yaml.tpl` | `config.yaml` | 应用配置 |
| `templates/project/{{PROJECT_NAME}}.spec.tpl` | `{name}.spec` | PyInstaller onedir |
| `templates/project/{{PROJECT_NAME}}-onefile.spec.tpl` | `{name}-onefile.spec` | PyInstaller onefile |
| `templates/project/{{PROJECT_NAME}}-debug.spec.tpl` | `{name}-debug.spec` | PyInstaller debug |
| `templates/project/.gitignore.tpl` | `.gitignore` | Git 忽略规则 |

---

### 2.2 前端工程模板

**目录**：`templates/project/frontend/`

需要创建的文件和内容：

#### 2.2.1 `package.json.tpl`

依赖清单：
```json
{
  "name": "{{PROJECT_NAME}}-frontend",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc --noEmit && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "vue": "^3.4.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.0",
    "autoprefixer": "^10.4.0",
    "daisyui": "^4.0.0",
    "postcss": "^8.4.0",
    "tailwindcss": "^3.4.0",
    "typescript": "^5.3.0",
    "vite": "^5.0.0",
    "vue-tsc": "^2.0.0"
  }
}
```

#### 2.2.2 `vite.config.ts.tpl`

关键配置：
- `base: "./"` - 相对路径，pywebview 加载本地文件需要
- `server.port` 从 config.yaml 的 vite_port 读取（或固定 5173）
- `build.outDir` = "../dist" - 输出到项目根目录的 dist/

#### 2.2.3 `tailwind.config.ts.tpl`

```typescript
import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  theme: { extend: {} },
  plugins: [require('daisyui')],
  daisyui: {
    themes: ['light', 'dark'], // 可按需添加更多主题
  },
} satisfies Config
```

#### 2.2.4 `postcss.config.js.tpl`

```javascript
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

#### 2.2.5 `tsconfig.json.tpl`

标准 Vue 3 + TypeScript 配置，包含 `vite/client` 和 `vue` 类型声明。

#### 2.2.6 `index.html.tpl`

```html
<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{{PROJECT_TITLE}}</title>
</head>
<body>
  <div id="app"></div>
  <script type="module" src="/src/main.ts"></script>
</body>
</html>
```

**注意**：`data-theme` 值需要与 config.yaml 中的 `app.theme` 一致。脚手架生成时可固定为 "light"，用户后续修改。

#### 2.2.7 `src/main.ts.tpl`

```typescript
import { createApp } from 'vue'
import App from './App.vue'
import './assets/style.css'

createApp(App).mount('#app')
```

#### 2.2.8 `src/App.vue.tpl`

根组件，包含示例布局：
- 顶部标题栏（DaisyUI navbar）
- 主内容区：文件拖拽区 + 日志面板
- 底部状态栏

#### 2.2.9 `src/api.ts.tpl`

参考 PRD 第 9.1 节：
- `waitForReady()` - 等待 pywebview 就绪
- `call<T>(method, ...args)` - 通用 API 调用封装

#### 2.2.10 `src/event-bus.ts.tpl`

参考 PRD 第 F-005 节：
- `useEvent(name, callback)` - Vue Composable

#### 2.2.11 `src/types/index.ts.tpl`

参考 PRD 第 F-004 节：
- `ErrCode` 常量对象
- `ApiResult<T>` 接口
- `isOk()` 类型守卫

#### 2.2.12 `src/assets/style.css.tpl`

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

html, body, #app {
  height: 100%;
  margin: 0;
  padding: 0;
}
```

#### 2.2.13 预置组件

每个组件都是 `.vue.tpl` 文件，存放在 `templates/project/frontend/src/components/`：

| 组件 | 功能 |
|:---|:---|
| `FileDrop.vue.tpl` | 文件拖拽区，DaisyUI 样式，emit `file-selected` 事件 |
| `LogPanel.vue.tpl` | 日志面板，通过 `useEvent("log:add")` 接收日志，支持级别过滤、清空 |
| `ProgressBar.vue.tpl` | 进度条，通过 `useEvent("progress:update")` 接收百分比 |
| `DataTable.vue.tpl` | 数据表格，props 驱动，DaisyUI table 样式 |
| `StatusBadge.vue.tpl` | 状态标签，idle/running/paused/error/done 五种状态 |
| `Toast.vue.tpl` | 全局通知，provide/inject 模式，支持 success/error/warning/info |

**组件设计原则**：
- 纯 props 驱动 + emit 事件，不内置业务状态
- 通过 `useEvent` composable 监听后端事件
- 所有样式使用 DaisyUI + TailwindCSS，不引入额外 CSS

---

### Phase 2 验证清单

1. 脚手架生成验证：
   ```bash
   uv run pywebvue create test_tool --title "Test Tool" --width 800 --height 600
   cd test_tool
   # 检查目录结构是否完整
   ls -la
   ls frontend/src/components/
   ```

2. 前端构建验证：
   ```bash
   cd test_tool/frontend
   bun install
   bun run build
   # 检查 dist/ 目录是否生成
   ls ../dist/
   ```

3. Vite Dev Server 验证：
   ```bash
   cd test_tool/frontend
   bun dev
   # 浏览器打开 http://localhost:5173 确认页面正常
   ```

4. 端到端验证：
   ```bash
   cd test_tool
   # Terminal 1: bun dev
   cd frontend && bun dev
   # Terminal 2: uv run main.py
   uv run main.py
   # 确认 pywebview 窗口加载 Vite Dev Server 页面
   # 修改前端代码，确认 HMR 生效
   ```

---

## Phase 3: 打包 + 开发体验增强

> 目标：完善打包流程、HMR 开发模式、单实例锁集成。

### 3.1 PyInstaller spec 模板

三套模板文件已包含在脚手架模板中（Phase 2），这里需要确保：

1. **标准模板 (onedir)**：
   - Analysis 配置中包含 `dist/`、`assets/`、`config.yaml`
   - EXCLUDES 预置常见大体积依赖
   - 图标路径正确

2. **单文件模板 (onefile)**：
   - 共享 Analysis 配置
   - EXE 包含 a.binaries 和 a.datas

3. **Debug 模板**：
   - `console=True`
   - `debug=True`

**脚手架生成时需处理的变量替换**：
- `{{PROJECT_NAME}}` -> 项目名
- `{{PROJECT_TITLE}}` -> 项目标题

### 3.2 Vite HMR 开发模式

**文件**：`src/pywebvue/app.py`（已有，需完善）

**增强要点**：

1. `--with-vite` 命令行参数支持：
   - 解析 `sys.argv`，检测 `--with-vite` 参数
   - 自动在后台启动 Vite Dev Server（`subprocess.Popen(["bun", "dev"], cwd="frontend")`）
   - 等待 Dev Server 就绪（轮询 `http://localhost:{port}` 直到可达）
   - App 退出时自动终止 Vite Dev Server 子进程

2. 开发模式自动检测逻辑：
   ```python
   def _determine_url(self) -> str:
       if self.config.dev.enabled:
           # 尝试连接 Vite Dev Server
           try:
               import urllib.request
               urllib.request.urlopen(
                   f"http://{DEV_SERVER_HOST}:{self.config.dev.vite_port}",
                   timeout=2
               )
               return f"http://{DEV_SERVER_HOST}:{self.config.dev.vite_port}"
           except (URLError, OSError):
               pass  # Fallback 到生产模式

       # 生产模式
       dist_path = os.path.join(os.getcwd(), DIST_DIR, FRONTEND_ENTRY)
       if not os.path.exists(dist_path):
           raise FileNotFoundError(
               f"Frontend build not found: {dist_path}\n"
               f"Run 'cd frontend && bun run build' first."
           )
       return dist_path
   ```

### 3.3 .gitignore 模板

**文件**：`templates/project/.gitignore.tpl`

```
# Python
__pycache__/
*.py[cod]
.venv/
*.egg-info/

# Frontend
frontend/node_modules/
frontend/.vite/

# Build
dist/
build/

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db

# Config (可选，保留用户自定义配置)
# config.yaml
```

### 3.4 pyproject.toml scripts 集成

在脚手架生成的 `pyproject.toml.tpl` 中加入：

```toml
[project.scripts]
dev = "main.py"

[tool.uv.scripts]
dev = "python main.py --with-vite"
build-frontend = "sh -c 'cd frontend && bun run build'"
build-app = "pyinstaller {PROJECT_NAME}.spec"
```

---

### Phase 3 验证清单

1. `--with-vite` 模式验证：
   ```bash
   cd test_tool
   uv run main.py --with-vite
   # 确认 Vite 自动启动，窗口连接成功
   # 修改前端代码，确认 HMR 生效
   # 关闭窗口，确认 Vite 进程自动退出
   ```

2. 打包验证（onedir）：
   ```bash
   cd test_tool
   uv add --dev pyinstaller
   cd frontend && bun run build && cd ..
   uv run pyinstaller test_tool.spec
   # 运行打包产物
   ./build/test_tool/test_tool.exe
   ```

3. 打包验证（onefile）：
   ```bash
   uv run pyinstaller test_tool-onefile.spec
   # 运行单文件
   ./dist/test_tool.exe
   ```

4. 单实例锁验证：
   - 设置 `config.yaml` 中 `singleton: true`
   - 双击 exe 两次，确认只打开一个窗口

---

## Phase 4: 高级功能

> 目标：ProcessManager 多实例、全局异常拦截、文件拖拽完善。

### 4.1 ProcessManager 完善

**文件**：`src/pywebvue/process.py`（已有，需完善）

增强点：
- 多实例管理：`ProcessManager.create(api_base, name)` 工厂方法
- Windows 暂停/恢复：使用 `ctypes` 调用 `kernel32.dll`
  - `OpenProcess` -> `SuspendThread` / `ResumeThread`
  - 需要枚举进程中的所有线程
- 超时机制：`default_timeout` 配置，超时后自动终止
- 事件名带 name 前缀：`process:{name}:output`、`process:{name}:complete`

### 4.2 全局异常拦截

**文件**：`src/pywebvue/app.py`（已有，需完善）

实现方式：创建 API 代理类

```python
class ApiProxy:
    """包装 ApiBase 实例，拦截所有方法调用，实现全局异常处理"""

    def __init__(self, api_instance: ApiBase):
        self._api = api_instance

    def __getattr__(self, name):
        attr = getattr(self._api, name)
        if not callable(attr):
            return attr
        # 包装方法调用
        def wrapper(*args, **kwargs):
            try:
                result = attr(*args, **kwargs)
                # 如果是协程，也需要包装（pywebview 异步调用）
                return result
            except Exception as e:
                self._api.logger.opt(exception=True).error(
                    f"Uncaught exception in {name}: {e}"
                )
                return Result.fail(ErrCode.INTERNAL_ERROR, detail=str(e)).to_dict()
        return wrapper
```

**注意**：pywebview 调用 js_api 方法时，方法返回值会自动序列化为 JSON。所以需要确保 Result 被 `.to_dict()` 转换。

### 4.3 文件拖拽完善

**文件**：`src/pywebvue/app.py`

pywebview 5.0+ 的原生拖拽支持：

```python
# App 类中，窗口创建后
def _setup_drag_drop(self, window):
    def on_drop(paths):
        self._api_instance.on_file_drop(paths)

    # pywebview 5.0+ 的事件绑定方式需要确认具体 API
    # 可能需要通过 events 参数或 window 事件
```

**注意**：pywebview 的拖拽 API 版本差异较大，需要查看 5.0+ / 6.0+ 文档确认具体用法。PRD 中提到 `pywebviewFullPath` 属性。

---

### Phase 4 验证清单

1. ProcessManager 多实例：
   ```python
   # 在 app.py 中创建两个 PM
   # 启动 task_a，确认 task_b 不受影响
   # 事件名确认带 name 前缀
   ```

2. 全局异常拦截：
   - 在 API 方法中故意抛出异常
   - 确认前端收到 `ErrCode.INTERNAL_ERROR` 而非崩溃
   - 确认控制台输出异常堆栈

3. 文件拖拽：
   - 拖拽文件到窗口，确认 `on_file_drop` 被调用
   - 拖拽多个文件，确认路径列表正确
   - 打包后拖拽功能正常

---

## Phase 5: 示例项目 + 文档

> 目标：创建两个完整的示例项目。

### 5.1 file-tool 示例

**目录**：`examples/file-tool/`

功能：拖拽文件 -> 显示文件信息 -> 模拟处理

实现：
- `app.py`：继承 ApiBase，实现 `get_file_info(path)` 和 `process_file(path)`
- 前端：FileDrop 组件 + 信息展示 + 进度条 + LogPanel

### 5.2 process-tool 示例

**目录**：`examples/process-tool/`

功能：启动/暂停/恢复/终止子进程，实时输出

实现：
- `app.py`：使用 ProcessManager 管理一个示例子进程
- 前端：控制面板（按钮组）+ LogPanel + StatusBadge + ProgressBar

### 5.3 用户开发指南

**文件**：`docs/user-guide.md`

内容包括：
1. 快速开始（安装 + 脚手架 + 运行）
2. 项目结构说明
3. 添加业务 API 方法
4. 前端调用 Python API
5. Python 推送事件到前端
6. 自定义错误码
7. 子进程管理
8. 配置文件说明
9. 开发模式（HMR）
10. 打包发布

---

## 开发建议

### 实现顺序（关键依赖链）

```
constants.py  (无依赖)
    |
    v
result.py    (无依赖)
    |
    v
config.py    (依赖 yaml)
    |
    v
logger.py    (依赖 loguru, config)
    |
    v
event_bus.py (依赖 window 引用)
    |
    v
dialog.py    (依赖 window 引用)
    |
    v
singleton.py (无依赖)
    |
    v
process.py   (依赖 event_bus, threading)
    |
    v
api_base.py  (依赖 event_bus, dialog, logger)
    |
    v
app.py       (依赖以上所有)
```

### 关键技术风险

| 风险 | 影响 | 建议 |
|:---|:---|:---|
| pywebview 文件拖拽 API 版本差异 | F-006 可能需要适配多版本 | 先确认 pywebview 5.0+ 和 6.0+ 的拖拽 API |
| Windows 进程暂停实现 | ProcessManager.pause() | 使用 ctypes SuspendThread，需要遍历线程 |
| pywebview API 方法返回值序列化 | Result 需要 .to_dict() | 测试 pywebview 对 dataclass 的 JSON 序列化行为 |
| Vite base path 配置错误 | 生产模式前端加载失败 | `base: "./"` 必须设置，否则资源路径错误 |
| 全局异常拦截代理 | __getattr__ 可能遗漏方法 | 确保所有公开方法都被代理 |
| 脚手架模板变量替换 | 复杂模板可能误替换 | 使用 Jinja2 或简单的 str.replace，注意转义 |

### pywebview API 参考

开发时需要频繁查阅的 pywebview 文档：
- 窗口创建：`webview.create_window(title, url, width, height, ...)`
- JS API 暴露：`js_api` 参数
- JS 执行：`window.evaluate_js(script)`
- 文件对话框：`window.create_file_dialog(dialog_type, ...)`
- 事件系统：`window.events` (pywebview 5.0+)
- 启动：`webview.start(debug, http_server)`
