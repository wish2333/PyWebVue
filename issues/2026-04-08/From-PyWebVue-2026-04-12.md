# PyWebVue Issue Response - 2026-04-12

**Re**: [TO-pywebvue-2026-04-08.md] Windows ONNX Runtime 支持、主线程任务执行、线程安全事件发送等关键问题

---

感谢详细的反馈。以下是对每个问题的处理结果。

---

## 已修复的问题

### 2.1 线程安全问题：`_emit` 现已线程安全

**问题**: `_emit` 直接调用 `evaluate_js`，在 Windows 上从非主线程调用会触发 COM 违规。

**修复**: `_emit` 改为队列模式 -- 事件入队后由主线程定时器统一刷新。签名不变，现有代码无需修改。

```python
# 之前（崩溃风险）
def _emit(self, event, data):
    self._window.evaluate_js(js)  # 非主线程 -> COM 违规

# 之后（线程安全）
def _emit(self, event, data):
    self._event_queue.put((event, data))  # 入队，由 _tick 在主线程刷新
```

**行为变化**: 事件最多延迟 `tick_interval` ms（默认 50ms）到达前端，对 UI 事件不可感知。

---

### 2.2 主线程任务执行机制

**问题**: 框架缺少让后台线程安全地在主线程执行代码的机制。

**修复**: 新增 `register_handler` + `run_on_main_thread` API。

采用 handler 注册模式（而非你方案中的 `dispatch_task` 继承模式），理由：
- 更灵活：可在运行时动态注册/替换，无需继承
- 更简单：一行注册即可，无需子类化
- 更安全：未注册的 handler 返回明确错误

```python
class MyApi(Bridge):
    def __init__(self):
        super().__init__()
        self.register_handler("create_recognizer", self._create_recognizer)

    def _create_recognizer(self, args):
        return sherpa_onnx.OnlineRecognizer.from_paraformer(args)

    def start_from_background(self):
        # 从后台线程安全调用：
        recognizer = self.run_on_main_thread("create_recognizer", config_path)
```

**与你的方案的对比**:

| 维度 | 你的方案 (`dispatch_task`) | 本方案 (`register_handler`) |
|------|---------------------------|---------------------------|
| 使用方式 | 继承 Bridge 并覆写 `dispatch_task` | 调用 `register_handler(name, fn)` |
| 灵活性 | 一个方法处理所有命令 | 每个命令独立注册 |
| 代码量 | 需要完整的子类 | 一行注册 |
| 动态性 | 不可运行时修改 | 可随时注册新 handler |

---

### 2.3 预加载钩子

**问题**: 框架没有提供在 WebView2 初始化前执行代码的钩子。

**修复**: `App` 构造函数新增 `on_start` 回调，在 `webview.create_window()` 之前执行。

```python
App(api, on_start=lambda: preload_native_libs())
```

**设计考量**: 命名为 `on_start`（而非 `on_ready`）以避免歧义 -- 它在窗口创建前执行，而非窗口就绪后。文档中同时说明了 DLL 预加载的两种方式：

```python
# 方式 1: 在 import pywebvue 之前预加载（推荐）
import sherpa_onnx
from pywebvue import App, Bridge, expose

# 方式 2: 使用 on_start 回调
App(api, on_start=lambda: preload_dlls())
```

---

### 2.4 方法暴露规则

**问题**: `_` 前缀方法是否暴露给 JavaScript 不明确。

**说明**: pywebview 会将 Bridge 的所有方法（包括 `_` 前缀）暴露给 JavaScript。`@expose` 装饰器不控制可见性，只添加 try/except 错误包装。

框架内部方法（`_tick`、`_on_drop`）以 `_` 前缀标识为内部使用，用户不应直接从 JavaScript 调用。此约定已在文档中明确说明。

---

### 2.5 定时器频率

**问题**: 定时器间隔硬编码。

**修复**: `App` 构造函数新增 `tick_interval` 参数（默认 50ms）。

```python
App(api, tick_interval=100)  # 降低频率
```

**与你的方案的区别**:
- 采用单一 `_tick` 定时器合并事件刷新 + 任务执行，而非两个独立定时器
- 未实现自适应频率 -- 50ms 轮询空队列的 CPU 开销可忽略，如确有需要后续可扩展

---

### 2.6 DLL 加载顺序

**问题**: ONNX Runtime DLL 与 WebView2 共享 MSVC runtime。

**处理**: 文档化解决方案，而非在框架中添加代码。理由：
- 这是 Windows 平台特有问题，与框架核心逻辑无关
- 不同 C++ 扩展的预加载需求不同
- `on_start` 回调已提供足够的框架级支持

在 `docs/development.md` 和 `docs/building.md` 中新增了 Windows C++ 扩展集成指南。

---

## Bug 修复

### `get_dropped_files` 缺失 `@expose` 装饰器

`get_dropped_files()` 方法缺少 `@expose` 装饰器，导致错误处理不一致。已修复。

---

## 超时任务清理

你的方案中存在一个隐含问题：如果 `run_on_main_thread` 超时，任务仍在队列中等待执行。本方案新增 `_cancelled_tasks` 集合，超时后跳过该任务的执行，避免浪费主线程资源。

---

## 变更汇总

| 文件 | 变更 |
|------|------|
| `pywebvue/bridge.py` | 线程安全 `_emit`、handler 注册、`run_on_main_thread`、`_tick`、`get_dropped_files` bug fix |
| `pywebvue/app.py` | `tick_interval`、`on_start`、单定时器、`_setup_drag_drop` -> `_setup_bridge` |
| `docs/api.md` | 新增 API 文档、线程安全指南 |
| `docs/development.md` | 新增线程安全、主线程任务执行、Windows C++ 扩展集成章节 |
| `docs/building.md` | 新增 Windows C++ 扩展打包注意事项 |
| `docs/SKILL.md` | 更新 Python API 速查 |

---

## 手动测试清单

- [ ] 运行 `main.py` demo，验证 tick 计数器、greet、add、get_info 正常工作
- [ ] 在后台线程高频调用 `app.emit()`（10ms 间隔），验证 Windows 不崩溃
- [ ] 使用 `register_handler` + `run_on_main_thread` 从后台线程调度任务
- [ ] 测试超时：handler sleep 超过 timeout，验证 `TimeoutError` 正确抛出
- [ ] 测试未注册 handler：调用 `run_on_main_thread("nonexistent")`，验证 `RuntimeError`
- [ ] 测试 `on_start`：传入回调，验证在窗口创建前执行
- [ ] 测试 `tick_interval`：设为 200，验证事件仍能正常到达
- [ ] 测试 `get_dropped_files`：从 JS 调用，验证返回 `{"success": true, "data": []}`
