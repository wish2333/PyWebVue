# PyWebVue 用户开发指南

## 1. 快速开始

### 前置条件

- Python >= 3.10.8
- [uv](https://docs.astral.sh/uv/) - Python 包管理器
- [bun](https://bun.sh/) - JavaScript 包管理器

### 安装

```bash
pip install pywebvue-framework
```

或使用 uv：

```bash
uv add pywebvue-framework
```

### 生成新项目脚手架

```bash
pywebvue create my_app --title "My Application"
cd my_app
```

这将生成一个完整的项目结构，包含 Python 后端、Vue 3 前端和 PyInstaller 规范文件。

### 以开发模式运行

```bash
# 选项 1：连接到已在运行的 Vite 开发服务器
uv run python main.py

# 选项 2：自动启动 Vite 开发服务器并运行应用
uv run python main.py --with-vite
```

### 构建分发版本

```bash
# 构建前端 + 使用 PyInstaller 打包（onedir 模式）
uv run pywebvue build

# 跳过前端重新构建
uv run pywebvue build --skip-frontend

# 构建为单个可执行文件
uv run pywebvue build --mode onefile

# 先清理构建目录
uv run pywebvue build --clean

# 自定义图标
uv run pywebvue build --icon path/to/icon.ico
```

---

## 2. 项目结构

一个通过脚手架生成的 PyWebVue 项目结构如下：

```
my_app/
  main.py             # 应用入口点
  app.py              # 业务 API 类
  config.yaml         # 应用配置
  pyproject.toml      # Python 依赖
  .gitignore
  my_app.spec         # PyInstaller 规范 (onedir)
  my_app-onefile.spec # PyInstaller 规范 (onefile)
  my_app-debug.spec   # PyInstaller 规范 (debug/console)
  frontend/
    package.json      # Node 依赖
    vite.config.ts    # Vite 配置
    tailwind.config.ts # Tailwind + DaisyUI 配置
    tsconfig.json     # TypeScript 配置
    index.html        # HTML 入口
    src/
      main.ts         # Vue 应用挂载
      App.vue         # 根组件
      api.ts          # 后端 API 调用封装
      event-bus.ts    # 事件订阅组合式函数
      types/index.ts  # TypeScript 类型定义
      assets/style.css
      components/     # 预构建 UI 组件
        FileDrop.vue
        LogPanel.vue
        ProgressBar.vue
        StatusBadge.vue
        Toast.vue
  dist/               # 构建后的前端 (生成)
    index.html
    assets/
```

---

## 3. 添加业务 API 方法

您 API 类上所有公共方法（不以 `_` 开头）都会通过 pywebview 的 JS 桥接自动暴露给前端。

### 示例

```python
# app.py
from pywebvue import ApiBase, Result, ErrCode


class MyAppApi(ApiBase):
    def health_check(self) -> Result:
        return Result.ok(data={"status": "running"})

    def get_user(self, user_id: int) -> Result:
        # 您的业务逻辑在此
        user = {"id": user_id, "name": "Alice"}
        return Result.ok(data=user)

    def validate_input(self, value: str) -> Result:
        if not value:
            return Result.fail(ErrCode.PARAM_INVALID, detail="Value cannot be empty")
        return Result.ok(data={"valid": True})
```

### 关键规则

- 所有公共方法必须返回一个 `Result` 对象
- 成功时返回 `Result.ok(data=...)`
- 错误时返回 `Result.fail(code, detail=...)`
- 参数必须是 JSON 可序列化类型 (str, int, float, bool, list, dict, None)
- `ApiProxy` 包装器会自动捕获未处理的异常并返回 `Result.fail(ErrCode.INTERNAL_ERROR)`

---

## 4. 前后端通信

### 调用后端 API 方法

```typescript
import { call } from "@/api";
import { isOk } from "@/types";

// 简单调用
const result = await call<{ status: string }>("health_check");
if (isOk(result)) {
  console.log(result.data.status);
} else {
  console.error(result.msg);
}

// 带参数的调用
const userResult = await call<{ name: string }>("get_user", 42);
```

### 监听后端事件

```typescript
import { useEvent } from "@/event-bus";

// 订阅（组件生命周期内自动清理）
useEvent("log:add", (data) => {
  console.log(data);
});

// 一次性事件（带超时）
import { waitForEvent } from "@/event-bus";

const result = await waitForEvent<{ path: string }>("file:process_complete", 30000);
```

### 从 Python 发送事件

```python
class MyAppApi(ApiBase):
    def process_data(self, data: str) -> Result:
        self.emit("progress:update", {"current": 5, "total": 10})
        self.emit("log:add", {"level": "INFO", "message": "Processing..."})
        return Result.ok()
```

### 等待 pywebview 准备就绪

```typescript
import { waitForReady } from "@/api";

onMounted(async () => {
  await waitForReady();
  // 后端现在可用
});
```

---

## 5. 自定义错误代码

### 定义自定义代码

```python
from pywebvue import ErrCode

# 为应用添加自定义错误代码（从 10000+ 开始）
ErrCode.USER_NOT_FOUND = 10001
ErrCode.INSUFFICIENT_PERMISSION = 10002

# 注册消息
ErrCode._MSG[10001] = "user not found"
ErrCode._MSG[10002] = "insufficient permission"
```

### 使用自定义代码

```python
class MyAppApi(ApiBase):
    def find_user(self, name: str) -> Result:
        user = self._db.find(name)
        if not user:
            return Result.fail(ErrCode.USER_NOT_FOUND, detail=name)
        return Result.ok(data=user)
```

### 内置错误代码范围

| 范围 | 模块 |
|-------|--------|
| 0 | 成功 |
| 1-5 | 通用错误 |
| 1001-1006 | 文件系统 |
| 2001-2005 | 进程管理 |
| 3001-3002 | 网络/通信 |

---

## 6. 子进程管理 (ProcessManager)

### 基本用法

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
        """重置为 IDLE 状态，允许新的 start()。"""
        return self.pm.reset()
```

### 状态机

```
IDLE -> RUNNING -> PAUSED -> RUNNING (恢复)
                 -> STOPPED -> IDLE (重置)
IDLE -> RUNNING -> STOPPED -> IDLE (下次 start 自动重置)
```

### 超时

```python
# 显式超时（秒）
self.pm.start(cmd=["long_task"], timeout=60)

# 如果未指定显式超时，则使用 config.yaml 中的 process.default_timeout
# config.yaml:
#   process:
#     default_timeout: 300
```

超时触发时：
- 会发送事件 `process:{name}:timeout`
- 进程会自动停止
- 状态转换为 STOPPED

### 多实例

```python
# 在同一个 API 类中使用多个命名的 ProcessManager
self.encoder_pm = ProcessManager(self, name="encoder")
self.uploader_pm = ProcessManager(self, name="uploader")
```

### 发送的事件

| 事件 | 负载 | 何时 |
|-------|--------|------|
| `process:{name}:output` | `{"line": "..."}` | 每个 stdout/stderr 行 |
| `process:{name}:complete` | `{"returncode": int}` | 进程退出 |
| `process:{name}:timeout` | `{"timeout": int}` | 达到超时 |

---

## 7. 配置参考 (config.yaml)

```yaml
app:
  name: "my_app"           # Python 标识符（用于规范文件）
  title: "My App"          # 窗口标题
  width: 900               # 窗口宽度（像素）
  height: 650              # 窗口高度（像素）
  min_size: [600, 400]     # 最小窗口尺寸
  max_size: [1920, 1080]   # 最大窗口尺寸
  resizable: true          # 允许调整窗口大小
  icon: "assets/icon.ico"  # 应用图标路径
  singleton: false         # 防止多个实例
  centered: true           # 窗口在屏幕居中
  theme: light             # DaisyUI 主题 (light/dark)

  dev:
    enabled: true          # 如果可用则连接到 Vite 开发服务器
    vite_port: 5173        # Vite 开发服务器端口
    debug: true            # 启用 pywebview 调试模式

logging:
  level: INFO              # 日志级别 (DEBUG/INFO/WARNING/ERROR/CRITICAL)
  console: true            # 将日志打印到控制台
  to_frontend: true        # 将日志转发到前端 LogPanel
  file: ""                 # 日志文件路径（空 = 禁用）
  max_lines: 1000          # 前端缓冲区中的最大日志条目数

process:
  default_timeout: 300     # 默认子进程超时（秒）

business: {}               # 自定义业务配置（通过 config.business 访问）
```

---

## 8. 开发模式 (Vite HMR)

### 选项 A：手动启动 Vite

```bash
# 终端 1：启动 Vite 开发服务器
cd frontend && bun dev

# 终端 2：启动 Python 应用（连接到 Vite）
uv run python main.py
```

应用通过 `config.yaml` 中的 `dev.enabled: true` 自动检测正在运行的 Vite 服务器。

### 选项 B：自动启动 Vite

```bash
# 自动启动 Vite，然后启动应用
uv run python main.py --with-vite
```

这会在后台启动 Vite 开发服务器，并在它准备就绪后等待再启动窗口。

### 工作原理

1. 当 `dev.enabled` 为 `true` 时，应用会检查 `http://localhost:{vite_port}` 是否可达
2. 如果可达，则从 Vite 开发服务器加载应用（启用 HMR）
3. 如果不可达，则回退到 `dist/` 中的生产构建

---

## 9. 打包与分发

### PyInstaller 构建模式

| 模式 | 规范文件 | 输出 |
|------|-----------|------|
| `onedir` | `my_app.spec` | 包含 exe 和依赖的文件夹 |
| `onefile` | `my_app-onefile.spec` | 单个可执行文件 |
| `debug` | `my_app-debug.spec` | 控制台窗口可见（用于调试） |

### CLI 构建命令

```bash
# 默认：onedir 模式
uv run pywebvue build

# 其他模式
uv run pywebvue build --mode onefile
uv run pywebvue build --mode debug

# 自定义规范文件
uv run pywebvue build --spec custom.spec

# 清理构建
uv run pywebvue build --clean

# 自定义图标
uv run pywebvue build --icon assets/my_icon.ico

# 自定义输出目录
uv run pywebvue build --output-dir ./release

# 跳过前端构建（使用之前构建的 dist/）
uv run pywebvue build --skip-frontend
```

### 构建流程

1. `--clean` (可选)：移除 `build/` 和 `dist/`
2. 前端构建：在 `frontend/` 中运行 `bun run build`（除非 `--skip-frontend`）
3. PyInstaller：使用选定的规范文件运行
4. 输出：`dist/` 中的可执行文件

---

## 10. 预构建组件

### FileDrop

拖放文件区域。显示拖放的文件路径，并可选择发送事件。

```vue
<FileDrop />
```

需要 `toast` 注入：`provide("toast", { showToast })`。

### LogPanel

显示来自后端的实时日志条目。支持级别过滤、自动滚动和清除。

```vue
<LogPanel />
```

自动订阅 `log:add` 事件。

### ProgressBar

显示带有百分比和标签的进度条。

```vue
<ProgressBar :progress="progressData" />
```

属性：`progress: ProgressPayload | null`，其中 `ProgressPayload = { current: number; total: number; label?: string }`。

### StatusBadge

显示指示状态状态的彩色徽章。

```vue
<StatusBadge status="running" />
```

属性：`status: "idle" | "running" | "paused" | "error" | "done"`。

### Toast

自动消失的 toast 通知。

```vue
<Toast :items="toastQueue" @dismiss="removeToast" />
```

属性：`items: ToastOptions[]`。事件：`dismiss(index: number)`。

```typescript
// 在 App.vue 中设置
let _toastId = 0;
const toastQueue = reactive<ToastOptions[]>([]);

function showToast(options: ToastOptions) {
  toastQueue.push({ ...options, id: ++_toastId });
}

provide("toast", { showToast });
```

---

## 示例

请参阅 `examples/` 目录获取完整的工作项目：

- **file-tool**：文件拖放、元数据显示、带进度的模拟处理。演示了 `on_file_drop`、`emit` 事件和后台线程处理。

- **process-tool**：带开始/暂停/恢复/停止控制的子进程管理。演示了 `ProcessManager`、超时、状态机和实时输出日志。