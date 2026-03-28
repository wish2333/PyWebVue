# PyWebVue开发指南（含示例）

> 本指南通过参考两个捆绑示例项目，全面展示PyWebVue框架的所有功能。适用于希望深入理解框架运作机制并构建真实应用的开发者。

## 目录
1. [框架架构概述](#1-框架架构概述)
2. [脚手架与项目布局](#2-脚手架与项目布局)
3. [示例1：file-tool -- 后端API设计](#3-示例1-file-tool--后端API设计)
4. [示例1：file-tool -- 前端实现](#4-示例1-file-tool--前端实现)
5. [示例2：process-tool -- ProcessManager实践](#5-示例2-process-tool--ProcessManager实践)
6. [示例2：process-tool -- 实时状态同步](#6-示例2-process-tool--实时状态同步)
7. [前端-后端通信模式](#7-前端-后端通信模式)
8. [预置组件深入解析](#8-预置组件深入解析)
9. [配置系统](#9-配置系统)
10. [高级主题](#10-高级主题)

---

## 1. 框架架构概述
PyWebVue是一个桌面应用框架，结合了三种技术：
```python
Python后端（ApiBase） <-- pywebview JS桥 --> Vue 3前端
| | ProcessManager DaisyUI组件 EventBus / Logger
```

### 核心模块
| 模块 | 文件 | 职责 |
|------|------|------|
| `App` | `app.py` | 窗口生命周期、Vite集成、拖放设置 |
| `ApiBase` | `api_base.py` | 用户业务API基类 |
| `ApiProxy` | `app.py` | 封装ApiBase并处理全局异常 |
| `ProcessManager` | `process.py` | 子进程状态机（启动/暂停/恢复/停止/超时） |
| `EventBus` | `event_bus.py` | 通过`run_js`将Python事件派发至前端 |
| `Dialog` | `dialog.py` | 本地文件/文件夹/保存对话框 |
| `Logger` | `logger.py` | 双通道日志（控制台 + 前端LogPanel） |
| `Config` | `config.py` | YAML配置加载到数据类 |
| `SingletonLock` | `singleton.py` | 跨平台单例锁 |
| `Result` / `ErrCode` | `result.py` | 标准化API返回类型和错误码 |

### 启动流程
```python
main.py -> App(config="config.yaml") -> load_config()
# 解析YAML为AppConfig
-> setup_logger()
# 配置loguru（控制台 + 前端sink）
-> SingletonLock
# 如果singleton=true，获取文件锁
-> _discover_api()
# 自动导入app.py，查找ApiBase子类
-> bind_config()
# 将配置传递给ApiBase实例
-> run()
-> _determine_url()
# Vite开发服务器或生产dist/
-> webview.create_window(js_api=ApiProxy(api_instance))
-> webview.start()
-> _on_window_loaded()
-> 通过run_js注入BRIDGE_JS（避免evaluate_js静默失败）
-> window.pywebvue.event.on/off/dispatch
-> _setup_drag_drop()
# 通过run_js直接注入拖放处理器
```

`ApiProxy`包裹每个公共方法调用。如果方法抛出未捕获异常，代理捕获并返回`Result.fail(ErrCode.INTERNAL_ERROR)`，而非将拒绝Promise传递给JavaScript。这意味着前端代码始终依赖`{ code, msg, data }`响应结构。

---

## 2. 脚手架与项目布局
### 创建项目
```bash
pywebvue create my_app --title "My Application" --width 1024 --height 768
cd my_app
```

CLI从`src/pywebvue/templates/project/`目录复制模板，替换`{{VARIABLES}}`占位符，并保留静态文件。变量名使用UPPER_CASE避免与Vue的`{{ camelCase }}`模板语法冲突。

### 生成文件
```
my_app/
├── main.py # 入口点：App(config="config.yaml").run()
├── app.py # 用户API类（ApiBase子类）
├── config.yaml # 配置文件
├── pyproject.toml # Python依赖 + uv脚本
├── .gitignore
├── my_app.spec # PyInstaller onedir spec
├── my_app-onefile.spec # PyInstaller onefile spec
├── my_app-debug.spec # PyInstaller debug（控制台）spec
└── frontend/
    ├── package.json # Vue 3 + TailwindCSS + DaisyUI + Vite + TypeScript
    ├── vite.config.ts # outDir: ../dist, alias @ -> src/
    ├── tailwind.config.ts # DaisyUI主题：["light", "dark"]
    ├── postcss.config.js
    ├── tsconfig.json / tsconfig.node.json
    ├── index.html # data-theme属性控制DaisyUI主题
    └── src/
        ├── main.ts # createApp(App).mount("#app")
        ├── App.vue # 根布局 + toast/progress/event wiring
        ├── api.ts # waitForReady() + call<T>(method, ...args)
        ├── event-bus.ts # useEvent(name, cb) + waitForEvent<T>(name, timeout)
        └── types/index.ts # ErrCode, ApiResult<T>, isOk(), LogEntry, etc.
```

### 本地运行
```bash
# 终端1：Vite开发服务器（热模块替换）
cd frontend && bun dev

# 终端2：Python应用（自动连接Vite）
uv run python main.py

# 或自动启动Vite从Python：
uv run python main.py --with-vite
```

### 打包
```bash
uv run pywebvue build # onedir（默认）
uv run pywebvue build --mode onefile # 单个exe
uv run pywebvue build --clean # 清理build/和dist/
uv run pywebvue build --icon app.ico # 覆盖图标
uv run pywebvue build --output-dir ./out # 自定义输出目录
```

---

## 3. 示例1：file-tool -- 后端API设计
### 文件结构
```
examples/file-tool/
├── main.py # 与脚手架模板相同
├── app.py # FileToolApi类
├── config.yaml # theme: dark
├── pyproject.toml
└── frontend/
    ├── src/
    │   ├── App.vue # 自定义布局
    │   └── components/
    │       ├── FileInfoCard.vue # 自定义组件
    │       ├── FileDrop.vue # 重用模板
    │       ├── LogPanel.vue # 重用模板
    │       ├── ProgressBar.vue # 重用模板
    │       └── Toast.vue # 重用模板
```

### API类解析
```python
from pywebvue import ApiBase, Result, ErrCode

class FileToolApi(ApiBase):
    def health_check(self) -> Result:
        return Result.ok(data={"status": "running"})

    def on_file_drop(self, file_paths: list[str]) -> None:
        for path in file_paths:
            self.logger.info(f"File dropped: {path}")
            self.emit("file:dropped", {"path": path})

    def get_file_info(self, path: str) -> Result:
        if not os.path.isfile(path):
            return Result.fail(ErrCode.FILE_NOT_FOUND, detail=path)
        # ... 收集元数据 ...
        return Result.ok(data={
            "path": path,
            "name": os.path.basename(path),
            "extension": ext.lower(),
            "size_bytes": size_bytes,
            "size_display": "1.5 MB",
            "modified": "2026-03-28T10:30:00",
            "is_binary": False,
        })

    def process_file(self, path: str) -> Result:
        if not os.path.isfile(path):
            return Result.fail(ErrCode.FILE_NOT_FOUND, detail=path)
        self.run_in_thread(self._simulate_processing, path)
        return Result.ok(data={"message": "Processing started"})

    def _simulate_processing(self, path: str) -> None:
        total_steps = 10
        for i in range(1, total_steps + 1):
            time.sleep(0.5)
            self.emit("progress:update", {
                "current": i,
                "total": total_steps,
                "label": f"Step {i}/{total_steps}: Analyzing"
            })
            self.logger.info(f"Processing [{i}/{total_steps}]: {os.path.basename(path)}")
        self.emit("progress:update", {"current": 0, "total": 0})
        self.emit("file:process_complete", {"path": path, "name": os.path.basename(path)})
```

### 错误处理策略
```python
# 用户错误
return Result.fail(ErrCode.FILE_NOT_FOUND, detail=path)

# 系统错误
return Result.fail(ErrCode.FILE_READ_ERROR, detail=str(e))

# 隐式：任何未捕获异常由ApiProxy捕获并返回Result.fail(ErrCode.INTERNAL_ERROR, detail=str(e))
```

---

## 4. 示例1：file-tool -- 前端实现
### Toast系统（提供/注入）
```typescript
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
<!-- 根模板 -->
<Toast :items="toastQueue" @dismiss="removeToast" />
```

### 事件订阅
```typescript
import { useEvent } from "@/event-bus";

useEvent("file:dropped", (data) => {
    const { path } = data as { path: string };
    showToast({ type: "info", message: `文件接收：${path}` });
    loadFileInfo(path);
});

useEvent("progress:update", (data) => {
    progress.value = data as ProgressPayload;
    if ((data as ProgressPayload).current === 0) {
        processing.value = false;
    }
});

useEvent("file:process_complete", (data) => {
    const { name } = data as { name: string };
    showToast({ type: "success", message: `处理完成：${name}` });
});
```

### API调用
```typescript
import { call } from "@/api";
import { isOk } from "@/types";

async function loadFileInfo(path: string) {
    const result = await call<FileInfo>("get_file_info", path);
    if (isOk(result)) {
        fileInfo.value = result.data;
    } else {
        showToast({ type: "error", message: `读取文件失败：${result.msg}` });
    }
}
```

### 后端就绪
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

---

## 5. 示例2：process-tool -- ProcessManager实践
### ProcessManager初始化
```python
class ProcessToolApi(ApiBase):
    def __init__(self) -> None:
        super().__init__()
        self.pm = ProcessManager(self, name="worker")
```

### 状态机
```python
start() stop() IDLE --------> RUNNING --------> STOPPED
| | | pause() | reset() v v PAUSED
```

### 启动进程
```python
def start_task(self, cmd: str, timeout: int | None = None) -> Result:
    if self.pm.is_running or self.pm.is_paused:
        return Result.fail(ErrCode.PROCESS_ALREADY_RUNNING, ...)
    parts = shlex.split(cmd)
    result = self.pm.start(
        cmd=parts,
        on_output=lambda line: self.logger.info(f"[worker] {line}"),
        on_complete=lambda rc: self.logger.info(f"Exit code: {rc}"),
        timeout=timeout,
    )
```

### 暂停/恢复/停止/重置
```python
def pause_task(self) -> Result:
    return self.pm.pause()

def resume_task(self) -> Result:
    return self.pm.resume()

def stop_task(self) -> Result:
    return self.pm.stop()

def reset_task(self) -> Result:
    return self.pm.reset()
```

### 超时行为
当设置超时时：
1. 启动守护线程等待`timeout`秒
2. 如果定时器在进程完成或手动停止前触发：
   - 发送`process:{name}:timeout`事件
   - 自动调用`pm.stop()`
   - 状态转为STOPPED
3. 如果进程完成或手动停止：
   - 取消定时器（event.set()）
   - `timeout_remaining`返回`None`

### 多实例示例
```python
class EncodingApi(ApiBase):
    def __init__(self):
        super().__init__()
        self.encoder = ProcessManager(self, name="encoder")
        self.uploader = ProcessManager(self, name="uploader")
```

---

## 6. 示例2：process-tool -- 实时状态同步
### 事件驱动状态更新
```typescript
useEvent("process:state_changed", (data) => {
    const payload = data as { state: string };
    const mapped: Record<string, StatusState> = {
        idle: "idle",
        running: "running",
        paused: "paused",
        stopped: "done",
    };
    processState.value = mapped[payload.state] ?? "error";
    refreshStatus();
});
```

### 计算按钮状态
```typescript
const canStart = computed(() => 
    processState.value === "idle" || processState.value === "done"
);

const canPause = computed(() => 
    processState.value === "running"
);

const canResume = computed(() => 
    processState.value === "paused"
);

const canStop = computed(() => 
    processState.value === "running" || processState.value === "paused"
);

const canReset = computed(() => 
    processState.value === "done"
);
```

### 状态显示
```vue
<nav class="navbar bg-base-100 shadow-md px-4">
    <div class="flex items-center gap-2">
        <StatusBadge :status="processState" />
        <span v-if="pid" class="badge badge-outline badge-sm">PID: {{ pid }}</span>
        <span v-if="timeoutRemaining !== null" class="badge badge-outline badge-sm">超时：{{ timeoutRemaining }}s</span>
    </div>
</nav>
```

---

## 7. 前端-后端通信模式
### 模式1：请求-响应（API调用）
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

### 模式2：推送事件（后端 -> 前端）
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

### 模式3：后台任务与进度
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
useEvent("work:complete", () => 
    showToast({ type: "success", message: "完成！" })
);
```

### 模式4：文件拖放
**Python:**
```python
def on_file_drop(self, file_paths: list[str]) -> None:
    for path in file_paths:
        self.emit("file:dropped", {"path": path})
```

### 模式5：本地对话框
**Python:**
```python
def select_file(self) -> Result:
    paths = self.dialog.open_file(
        title="选择文件",
        file_types=("文本文件 (*.txt)", "所有文件 (*.*)"),
        multiple=True,
    )
    if paths is None:
        return Result.fail(ErrCode.PARAM_INVALID, detail="用户取消")
    return Result.ok(data=paths)
```

### 模式6：一次性事件等待
**TypeScript:**
```typescript
import { waitForEvent } from "@/event-bus";
const result = await waitForEvent<{ path: string }>("file:process_complete", 60000);
console.log(result.path);
```

---

## 8. 预置组件深入解析
### Toast
| 属性 | 类型 | 描述 |
|------|------|------|
| `items` | `ToastOptions[]` | 要显示的消息数组 |

```typescript
interface ToastOptions {
    id: number;
    type: "success" | "error" | "warning" | "info";
    message: string;
    duration?: number; // 当前固定4000ms
}
```

### LogPanel
实时日志查看器，自动订阅`log:add`事件。功能：
- 级别过滤下拉菜单（ALL/DEBUG/INFO/WARNING/ERROR/CRITICAL）
- 自动滚动切换
- 清除按钮
- 最多500条记录（FIFO）
- 级别颜色编码

### ProgressBar
| 属性 | 类型 | 描述 |
|------|------|------|
| `progress` | `ProgressPayload \| null` | 进度数据或空状态 |

```typescript
interface ProgressPayload {
    current: number;
    total: number;
    label?: string;
}
```

### StatusBadge
| 属性 | 类型 | 描述 |
|------|------|------|
| `status` | `StatusState` | idle/running/paused/error/done |

### FileDrop
拖放区域，监听`file:dropped`事件（由后端`on_file_drop`触发）。需要注入`toast`：
```typescript
provide("toast", { showToast });
```

---

## 9. 配置系统
### config.yaml结构
```yaml
app:
  name: "my_app" # Python标识符
  title: "My App" # 窗口标题
  width: 900 # 初始宽度（px）
  height: 650 # 初始高度（px）
  min_size: [600, 400] # 最小尺寸
  max_size: [1920, 1080] # 最大尺寸
  resizable: true # 允许调整大小
  icon: "assets/icon.ico" # 窗口图标
  singleton: false # 防止多实例
  centered: true # 居中显示
  theme: light # DaisyUI主题
  dev: enabled: true # 自动检测Vite
  vite_port: 5173 # Vite端口
  debug: true # pywebview调试模式
  logging:
    level: INFO # 最低日志级别
    console: true # 输出到stderr
    to_frontend: true # 前端LogPanel
    file: "" # 日志文件路径
    max_lines: 1000 # 前端缓冲区最大条数
  process:
    default_timeout: 300 # 默认子进程超时（秒）
  business: {} # 自定义键值配置
```

### Python中访问配置
```python
class MyAppApi(ApiBase):
    def some_method(self) -> Result:
        title = self.config.title
        db_path = self.config.business.get("database_path", "")
        timeout = self.config.process.default_timeout
        return Result.ok()
```

### 主题切换
DaisyUI主题通过`<html>`的`data-theme`属性控制：
```html
<!-- 明亮主题 -->
<html lang="en" data-theme="light">

<!-- 暗黑主题 -->
<html lang="en" data-theme="dark">
```

---

## 10. 高级主题
### 单例锁
在`config.yaml`中设置`singleton: true`：
```yaml
app:
  singleton: true
```

### 自定义错误码
```python
from pywebvue import ErrCode
ErrCode.USER_NOT_FOUND = 10001
ErrCode.INSUFFICIENT_PERMISSION = 10002
ErrCode._MSG[10001] = "用户未找到"
ErrCode._MSG[10002] = "权限不足"
```

### 日志最佳实践
```python
self.logger.info("操作完成")
self.logger.warning("第3次重试")
self.logger.error("连接失败")
self.logger.opt(exception=True).error("详细错误并附带堆栈")
```

### ProcessManager：二进制大小考虑
`ProcessManager`使用`subprocess.Popen`，Windows上通过`creationflags`添加最小开销。跨平台暂停/恢复使用`ctypes`调用`NtSuspendProcess`/`NtResumeProcess`。

### 调试技巧
1. **使用`--mode debug`** 获取控制台窗口查看Python日志
2. **使用LogPanel** -- 后端日志实时转发至前端（`to_frontend: true`）
3. **使用`self.logger.opt(exception=True).error(...)`** 获取详细错误上下文
4. **检查浏览器DevTools** -- 调试模式启用右键>检查元素
5. **API错误从不静默** -- `ApiProxy`捕获所有未捕获异常并返回`Result.fail(ErrCode.INTERNAL_ERROR, detail=str(e))`

### pywebview 6.x 兼容性说明

PyWebVue目标平台为pywebview 6.x（Windows EdgeChromium）。框架内部绕过了该版本的多个已知问题：

**1. `evaluate_js` 对无返回值的脚本静默失败**

pywebview 6.1 EdgeChromium存在一个bug：`evaluate_js()`内部调用`json.loads(task.Result)`，当脚本无返回值（返回`undefined`）时，`json.loads`抛出`JSONDecodeError`，整个脚本执行被静默丢弃。

**绕过方案：** 框架在所有需要的地方使用`run_js()`替代`evaluate_js()`：
- `EventBus.emit()` 通过`run_js`派发事件
- `ApiBase.bind_window()` 通过`run_js`注入`BRIDGE_JS`
- `_setup_drag_drop()` 通过`run_js`注入拖放处理器
- `Element.on()` 被monkeypatch为使用`run_js`注册JS事件监听器

**2. `ApiProxy` 必须通过 `inspect.ismethod()` 检查**

pywebview 6.x 通过调用`dir()`枚举`js_api`对象的公开方法，然后对每个属性调用`inspect.ismethod(attr)`来发现API方法。`__getattr__`返回的普通函数无法通过此检查，会被静默跳过，导致所有API方法对前端不可见。

**绕过方案：** `ApiProxy.__getattr__` 通过`types.MethodType(wrapper, self)` 返回包装器，使其成为绑定方法，可通过`inspect.ismethod()`检查。包装器的第一个参数（`self_bound`）接收代理实例注入的`self`并在内部丢弃。

**3. `BRIDGE_JS` 不能覆盖已有的前端状态**

前端的`ensureBridge()`（位于`event-bus.ts`）可能在Python的`BRIDGE_JS`注入之前就初始化了事件桥接。如果`BRIDGE_JS`直接执行`window.__pywebvue_event_listeners = {}`，会清除所有已注册的事件监听器。

**绕过方案：** `BRIDGE_JS` 使用守卫条件（`|| {}` 和 `if (!...)`）确保不会覆盖已有的桥接状态。

**4. `pywebviewready` 事件在 `window` 上派发，而非 `document`**

pywebview在`window`上派发`new CustomEvent('pywebviewready')`。使用`document.addEventListener('pywebviewready', ...)`永远无法捕获。

**绕过方案：** `api.ts`中的`waitForReady()`使用`window.addEventListener(...)`并附带轮询回退。

**5. `Element.__generate_events()` 对 window/document 静默失败**

pywebview的`Element.__generate_events()`使用`evaluate_js`发现DOM元素支持的事件。对于`document`元素，`@_ignore_window_document`装饰器进一步阻止了对`window`/`document`节点ID的处理，返回`None`。因此`element.events.dragover`等属性永远不会被创建。

**绕过方案：** 拖放处理器通过`run_js`直接注入，使用`document.addEventListener()`，完全绕过pywebview的DOM API。

**6. pywebview的 `create_file_dialog` 不接受 `None` 作为可选参数**

传入`directory=None`或`file_types=None`会导致崩溃，因为内部调用了`os.path.exists(None)`。

**绕过方案：** `Dialog`方法传递空字符串`""`和空元组`()`而非`None`。

**7. 前端通过 `ensureBridge()` 自初始化桥接**

由于`run_js(BRIDGE_JS)`的执行时间相对于Vue的`onMounted`是不确定的，前端必须能够独立初始化桥接。`event-bus.ts`中的`ensureBridge()`函数在`window.__pywebvue_dispatch`、`window.__pywebvue_event_listeners`和`window.pywebvue.event`不存在时创建它们，确保事件系统在任何注入时机下都能正常工作。

**`run_js` 与 `evaluate_js` 对比：**

| 方面 | `evaluate_js` | `run_js` |
|------|---------------|----------|
| 返回值 | 返回解析后的JSON结果 | 无返回值 |
| undefined返回 | **静默崩溃**（pywebview 6.x bug） | 正常工作 |
| 适用场景 | 需要返回值时 | 只需要副作用时 |
| 框架中的使用 | 已避免 | 全部使用 |
