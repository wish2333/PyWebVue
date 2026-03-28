# PyWebVue 用户指南

> 本指南面向希望安装、运行、配置和打包 PyWebVue 应用程序的**最终用户和开发者**。它涵盖了使用该框架及其 CLI 所需了解的核心知识，而不深入框架内部原理。

---

## 目录

1. [什么是 PyWebVue](#1-什么是-pywebvue)
2. [先决条件与安装](#2-先决条件与安装)
3. [创建新项目](#3-创建新项目)
4. [运行您的应用程序](#4-运行您的应用程序)
5. [项目结构](#5-项目结构)
6. [编写后端逻辑 (app.py)](#6-编写后端逻辑-apppy)
7. [前端开发](#7-前端开发)
8. [内置 UI 组件](#8-内置-ui-组件)
9. [配置参考](#9-配置参考)
10. [子进程管理](#10-子进程管理)
11. [构建与打包](#11-构建与打包)
12. [示例](#12-示例)
13. [故障排除](#13-故障排除)

---

## 1. 什么是 PyWebVue

PyWebVue 是一个面向 Python 开发者的桌面应用程序框架。它结合了：

- 通过 [pywebview](https://pywebview.flowrl.com/) 实现的 **Python 后端** -- 原生窗口与 JS 桥接
- 使用 TypeScript、[Tailwind CSS](https://tailwindcss.com/) 和 [DaisyUI](https://daisyui.com/) 的 **Vue 3 前端**
- 用于项目脚手架和 PyInstaller 打包的 **CLI 工具**

您编写 Python 业务逻辑和 Vue 组件。框架负责处理窗口生命周期、事件通信、日志记录、文件拖放、子进程管理和原生对话框。

### 核心特性概览

| 特性 | 描述 |
|---------|-------------|
| 项目脚手架 | `pywebvue create my_app` 生成完整项目 |
| 热模块替换 | Vite 开发服务器，前端即时更新 |
| 前后端桥接 | 从 TypeScript 调用 Python 方法，从 Python 向前端推送事件 |
| 全局异常处理 | 未捕获的 Python 异常返回 `Result.fail()` 而非导致崩溃 |
| 实时日志 | 后端日志自动显示在前端 LogPanel 中 |
| 文件拖放 | 将文件拖入窗口，由您的 Python 代码处理 |
| 子进程管理 | 启动/暂停/恢复/停止子进程，支持超时 |
| 原生对话框 | 文件打开、文件夹选择、另存为对话框 |
| 单实例锁 | 通过文件锁防止多个应用实例 |
| PyInstaller 打包 | 一键构建为 `.exe`（onedir、onefile 或 debug 模式） |

---

## 2. 先决条件与安装

### 环境要求

| 工具 | 版本 | 用途 |
|------|---------|-----|
| Python | >= 3.10.8 | 运行时 |
| [uv](https://docs.astral.sh/uv/) | 最新 | 包管理器 |
| [bun](https://bun.sh/) | 最新 | 前端包管理器（npm 替代品） |
| PyInstaller (可选) | >= 6.0 | 打包 |

### 安装框架

```bash
# 添加到您的项目（推荐）
uv add pywebvue-framework

# 或全局安装
pip install pywebvue-framework
```

这将安装 `pywebvue` CLI 命令和 Python 包。

### 验证安装

```bash
pywebvue --help
```

应显示：

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

## 3. 创建新项目

### 基础脚手架

```bash
pywebvue create my_app
cd my_app
```

这将创建一个名为 `my_app` 的项目，使用默认设置：
- 窗口标题："My App"（源自项目名称）
- 窗口尺寸：900x650
- 主题：light
- 完整的 Vue 3 + TypeScript + DaisyUI 前端

### 自定义选项

```bash
pywebvue create my_app \
  --title "Invoice Generator" \
  --width 1024 \
  --height 768
```

| 标志 | 默认值 | 描述 |
|------|---------|-----|
| `project_name` | (必填) | Python 标识符（snake_case） |
| `--title` | 项目名称 | 窗口标题文本 |
| `--width` | 900 | 窗口宽度（像素） |
| `--height` | 650 | 窗口高度（像素） |
| `--force` | false | 覆盖现有目录（需确认） |

### 项目命名规则

- 必须是有效的 Python 标识符：字母、数字、下划线，以字母或 `_` 开头
- 不能是 Python 关键字（如 `class`, `def`, `import`）
- 用于规范文件名、配置和 Python 模块命名

---

## 4. 运行您的应用程序

### 使用 Vite HMR（热模块替换）进行开发

**选项 A：手动启动 Vite（两个终端）**

```bash
# 终端 1：启动 Vite 开发服务器
cd my_app/frontend
bun install    # 仅首次
bun dev

# 终端 2：启动应用（自动检测 Vite）
cd my_app
uv run python main.py
```

**选项 B：自动启动 Vite（单终端）**

```bash
cd my_app
uv run python main.py --with-vite
```

这将在后台启动 Vite，等待其就绪，然后打开窗口。

### 生产模式

先构建前端，然后运行：

```bash
cd my_app/frontend
bun run build        # 输出到 ../dist/

cd ..
uv run python main.py   # 加载 dist/index.html
```

### 模式选择原理

应用从 `config.yaml` 读取 `dev.enabled`：

- 若为 `true` 且 Vite 可在 `http://localhost:{vite_port}` 访问：从 Vite 加载（HMR）
- 若为 `true` 但 Vite 不可达：回退到 `dist/index.html` 并显示警告
- 若为 `false`：始终加载 `dist/index.html`

---

## 5. 项目结构

```
my_app/
  main.py                  # 入口点
  app.py                   # 您的业务 API（编辑此文件）
  config.yaml              # 应用设置（编辑此文件）
  pyproject.toml           # Python 依赖
  .gitignore
  my_app.spec              # PyInstaller：文件夹输出
  my_app-onefile.spec      # PyInstaller：单 exe 输出
  my_app-debug.spec        # PyInstaller：控制台窗口可见
  frontend/
    package.json
    vite.config.ts
    tailwind.config.ts
    postcss.config.js
    tsconfig.json
    tsconfig.node.json
    index.html             # HTML 入口（在此处设置 data-theme 属性）
    src/
      main.ts              # Vue 应用引导
      App.vue              # 根组件（编辑此文件）
      api.ts               # 后端 API 调用助手
      event-bus.ts         # 事件订阅助手
      types/index.ts       # TypeScript 类型 + ErrCode
      assets/style.css     # 全局样式
      components/
        FileDrop.vue       # 拖放区域
        LogPanel.vue       # 日志查看器（带级别过滤）
        ProgressBar.vue    # 进度条
        StatusBadge.vue    # 状态指示徽章
        Toast.vue          # 通知弹窗
  dist/                    # 构建的前端（由 bun run build 生成）
```

### 您将编辑的文件

| 文件 | 时机 |
|------|------|
| `app.py` | 添加业务逻辑方法 |
| `config.yaml` | 更改窗口设置、日志、主题 |
| `frontend/src/App.vue` | 自定义 UI 布局 |
| `frontend/src/types/index.ts` | 添加自定义 TypeScript 类型 |
| `frontend/src/components/` | 添加自定义 Vue 组件 |

---

## 6. 编写后端逻辑 (app.py)

### 基本结构

```python
from pywebvue import ApiBase, Result, ErrCode

class MyAppApi(ApiBase):
    """所有公共方法都会自动暴露给前端。"""

    def health_check(self) -> Result:
        return Result.ok(data={"status": "running"})
```

### 规则

1. **继承 `ApiBase`**
2. **所有公共方法**（不以 `_` 开头）均可从 JavaScript 调用
3. **每个方法必须返回 `Result`**
4. **参数**必须是 JSON 可序列化的：`str`, `int`, `float`, `bool`, `list`, `dict`, `None`
5. **未捕获的异常**会自动捕获并作为 `Result.fail(ErrCode.INTERNAL_ERROR)` 返回

### 返回值

```python
# 成功
return Result.ok(data={"name": "Alice", "age": 30})

# 成功且无数据
return Result.ok()

# 错误
return Result.fail(ErrCode.PARAM_INVALID, detail="Email is required")
return Result.fail(ErrCode.FILE_NOT_FOUND, detail="/path/to/file.txt")
```

### 内置错误代码

| 代码 | 名称 | 使用时机 |
|------|------|-------------|
| 0 | `OK` | 成功 |
| 2 | `PARAM_INVALID` | 无效用户输入 |
| 4 | `TIMEOUT` | 操作超时 |
| 5 | `INTERNAL_ERROR` | 意外服务器错误（自动） |
| 1001 | `FILE_NOT_FOUND` | 文件不存在 |
| 1002 | `FILE_READ_ERROR` | 无法读取文件 |
| 2001 | `PROCESS_START_FAILED` | 子进程启动失败 |
| 2002 | `PROCESS_ALREADY_RUNNING` | 子进程已在运行 |
| 2003 | `PROCESS_NOT_RUNNING` | 无活动子进程 |
| 2004 | `PROCESS_TIMEOUT` | 子进程超时 |

### 自定义错误代码

```python
from pywebvue import ErrCode

ErrCode.USER_NOT_FOUND = 10001
ErrCode._MSG[10001] = "user not found"
```

### 文件拖放处理

重写 `on_file_drop` 以处理拖入窗口的文件：

```python
def on_file_drop(self, file_paths: list[str]) -> None:
    for path in file_paths:
        self.logger.info(f"Received: {path}")
        self.emit("file:received", {"path": path})
```

### 后台任务

对长时间运行的操作使用 `self.run_in_thread()`：

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

### 原生对话框

```python
# 文件选择器
paths = self.dialog.open_file(title="Select", file_types=("Images (*.png;*.jpg)",), multiple=True)
if paths is None:
    return Result.fail(ErrCode.PARAM_INVALID, detail="Cancelled")
return Result.ok(data=paths)

# 文件夹选择器
folders = self.dialog.open_folder(title="Select Output Folder")

# 保存对话框
save_paths = self.dialog.save_file(title="Save As", default_name="output.csv", file_types=("CSV (*.csv)",))
```

### 日志记录

```python
# self.logger 是预绑定您类名的 loguru 日志记录器
self.logger.info("User clicked button")
self.logger.warning("Disk space low")
self.logger.error("Connection failed")
self.logger.opt(exception=True).error("Detailed error")  # 包含回溯信息
```

所有达到或超过配置级别的日志都会自动转发到前端 LogPanel。

### 访问配置

```python
def get_app_info(self) -> Result:
    return Result.ok(data={
        "name": self.config.title,
        "width": self.config.width,
        "custom": self.config.business.get("my_key", "default"),
    })
```

---

## 7. 前端开发

### 调用后端方法

```typescript
import { call } from "@/api";
import { isOk } from "@/types";

// 简单调用
const result = await call<{ status: string }>("health_check");
if (isOk(result)) {
  console.log(result.data.status);
}

// 带参数调用
const user = await call<{ name: string }>("get_user", 42);

// 错误处理
if (!isOk(user)) {
  showToast({ type: "error", message: user.msg });
}
```

### 等待后端就绪

```typescript
import { waitForReady } from "@/api";

onMounted(async () => {
  await waitForReady();  // 在 pywebview JS API 可用时解析
  // 现在可以安全调用后端方法
});
```

### 监听事件

```typescript
import { useEvent } from "@/event-bus";

// 组件卸载时自动取消订阅
useEvent("progress:update", (data) => {
  const { current, total } = data as { current: number; total: number };
  console.log(`${current}/${total}`);
});
```

### 一次性事件等待

```typescript
import { waitForEvent } from "@/event-bus";

const result = await waitForEvent<{ path: string }>("file:complete", 30000);
```

### Toast 通知

```typescript
// 在 App.vue（或任何提供 toast 系统的组件）中
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

## 8. 内置 UI 组件

### FileDrop

拖放文件区域。显示已拖放文件列表。

```vue
<FileDrop />
```

需要在祖先组件中 `provide("toast", { showToast })`。

### LogPanel

实时日志查看器。自动订阅 `log:add` 事件。

```vue
<LogPanel />
```

功能：级别过滤（ALL/DEBUG/INFO/WARNING/ERROR/CRITICAL）、自动滚动、清除按钮、最多保留 500 条条目。

### ProgressBar

带百分比徽章和标签文本的进度条。

```vue
<ProgressBar :progress="progressData" />
```

```typescript
import type { ProgressPayload } from "@/types";
const progressData = ref<ProgressPayload | null>(null);

// 显示进度
progressData.value = { current: 5, total: 10, label: "Processing..." };

// 隐藏/重置
progressData.value = null;
// 或从后端发送 { current: 0, total: 0 }
```

### StatusBadge

用于状态指示的彩色徽章。

```vue
<StatusBadge status="running" />
```

取值：`"idle"`（灰色）、`"running"`（蓝色）、`"paused"`（黄色）、`"error"`（红色）、`"done"`（绿色）。

### Toast

自动消失的通知堆栈（4 秒计时器）。

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

## 9. 配置参考

### 完整 config.yaml

```yaml
app:
  name: "my_app"             # Python 标识符（用于规范文件名）
  title: "My App"            # 窗口标题
  width: 900                 # 窗口宽度（像素）
  height: 650                # 窗口高度（像素）
  min_size: [600, 400]       # 最小窗口尺寸
  max_size: [1920, 1080]     # 最大窗口尺寸
  resizable: true            # 允许调整窗口大小
  icon: "assets/icon.ico"    # 窗口图标路径
  singleton: false           # 防止多个实例
  centered: true             # 屏幕居中
  theme: light               # DaisyUI 主题：light 或 dark

  dev:
    enabled: true            # 自动检测 Vite 开发服务器
    vite_port: 5173          # Vite 开发服务器端口
    debug: true              # pywebview 调试模式（右键 > 检查）

logging:
  level: INFO                # 最低级别：DEBUG, INFO, WARNING, ERROR, CRITICAL
  console: true              # 将日志打印到终端
  to_frontend: true          # 在前端 LogPanel 显示日志
  file: ""                   # 日志文件路径（空 = 禁用）
  max_lines: 1000            # 前端缓冲区保留的最大日志条目数

process:
  default_timeout: 300       # 默认子进程超时（秒）

business: {}                 # 自定义配置（通过 self.config.business 访问）
```

### 主题

在 `frontend/index.html` 中设置 `data-theme` 以匹配 `app.theme`：

```html
<html lang="en" data-theme="dark">  <!-- 用于深色主题 -->
```

DaisyUI 默认支持 `light` 和 `dark`。在 `tailwind.config.ts` 的 `daisyui.themes` 下添加更多主题。

---

## 10. 子进程管理

### 快速示例

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

### 状态转换

```
IDLE -> start() -> RUNNING -> pause() -> PAUSED -> resume() -> RUNNING
                                |                                      |
                                +--- stop() -------> STOPPED -----------+
                                                     |
                                                     +--- reset() -> IDLE
                                                     |
                                                     +--- start() -> RUNNING (自动重置)
```

### 超时

```python
# 显式超时（秒）
self.pm.start(cmd=["long_task"], timeout=60)

# 或在 config.yaml 中设置：
# process:
#   default_timeout: 300
```

超时触发时：进程自动停止，并发送 `process:{name}:timeout` 事件。

### 事件（在前端订阅）

| 事件 | 数据 | 时机 |
|-------|------|-----|
| `process:{name}:output` | `{ line: "..." }` | 每个 stdout/stderr 行 |
| `process:{name}:complete` | `{ returncode: 0 }` | 进程退出 |
| `process:{name}:timeout` | `{ timeout: 60 }` | 达到超时 |

---

## 11. 构建与打包

### PyInstaller 构建模式

| 模式 | 标志 | 输出 |
|------|------|-----|
| 文件夹 | `--mode onedir`（默认） | `dist/my_app/my_app.exe` + DLLs |
| 单 exe | `--mode onefile` | `dist/my_app.exe` |
| 调试 | `--mode debug` | 控制台窗口可见 |

### 构建命令

```bash
# 从项目根目录：
uv run pywebvue build
```

### 构建标志

| 标志 | 描述 |
|------|-----|
| `--mode {onedir,onefile,debug}` | 构建模式（默认：onedir） |
| `--spec PATH` | 使用特定的 .spec 文件（覆盖 --mode） |
| `--skip-frontend` | 跳过 `bun run build` 步骤 |
| `--clean` | 构建前移除 `build/` 和 `dist/` |
| `--icon PATH` | 覆盖应用图标（.ico） |
| `--output-dir PATH` | 构建 artifacts 的自定义目录 |

### 示例

```bash
# 完整清理构建为单 exe 并使用自定义图标
uv run pywebvue build --clean --mode onefile --icon assets/my_icon.ico

# 快速重建（跳过前端，使用上次构建）
uv run pywebvue build --skip-frontend

# 自定义输出位置
uv run pywebvue build --output-dir ./release
```

### 构建流程

```
1. [可选] 移除 build/ 和 dist/（--clean）
2. cd frontend && bun run build  （除非 --skip-frontend）
3. pyinstaller --noconfirm my_app.spec
4. 输出到 dist/
```

### 将 PyInstaller 添加为开发依赖

```bash
uv add --dev pyinstaller
```

---

## 12. 示例

`examples/` 目录包含两个完整的可运行项目：

### file-tool

一个文件处理工具，演示：

- 文件拖放到窗口
- 文件元数据显示（名称、大小、类型、修改日期）
- 模拟多步骤处理与进度条
- 深色主题配置
- 使用 `run_in_thread()` 的后台线程处理

```bash
cd examples/file-tool
uv sync
cd frontend && bun install && cd ..
uv run python main.py
```

尝试：将文件拖入窗口，查看其元数据，点击 "Process File" 查看进度。

### process-tool

一个子进程管理工具，演示：

- 带启动/暂停/恢复/停止/重置的 ProcessManager
- LogPanel 中的实时输出日志
- 进程状态的状态徽章
- 超时自动停止（配置：`process.default_timeout: 30`）
- 事件驱动的状态同步

```bash
cd examples/process-tool
uv sync
cd frontend && bun install && cd ..
uv run python main.py
```

尝试：输入类似 `python -c "for i in range(10): print(f'line {i}'); import time; time.sleep(0.5)"` 的命令，点击 Start，然后尝试 Pause/Resume/Stop。

---

## 13. 故障排除

### "Frontend build not found: dist/index.html"

运行 `cd frontend && bun run build` 构建前端，或先启动 Vite 开发服务器。

### "Vite Dev Server not reachable, falling back to production build"

手动启动 Vite（`cd frontend && bun dev`）或使用 `--with-vite` 标志。

### "PyInstaller is not installed"

```bash
uv add --dev pyinstaller
```

### 窗口打开但显示空白页面

- 检查 `dist/index.html` 是否存在（运行 `cd frontend && bun run build`）
- 尝试使用 `--mode debug` 运行以查看控制台错误

### 前端 API 调用返回 "backend is not ready"

确保在 `onMounted()` 中调用 `waitForReady()` 后再进行 API 调用。

### ProcessManager 暂停/恢复在某些 Linux 发行版上无效

暂停/恢复在 Unix 上使用 `SIGSTOP`/`SIGCONT`。这些可能不适用于所有进程类型。在 Windows 上，通过 ctypes 使用 `NtSuspendProcess`/`NtResumeProcess`。

### 启动时显示 "Another instance is already running"

单例锁文件可能过时（例如崩溃后）。框架会自动检查过时锁。如果问题持续，手动从临时目录删除锁文件：Windows 上为 `%TEMP%` 中的 `my_app.lock`，Unix 上为 `/tmp`。

### bun install 失败

确保已安装并可访问 bun：
```bash
bun --version
```

如果 bun 不可用，可以使用 npm 代替：
```bash
cd frontend && npm install
```