# GitHub Issue: PyWebVue 框架问题与改进建议
**标题**：Windows ONNX Runtime 支持、主线程任务执行、线程安全事件发送等关键问题
**标签**：bug, enhancement, windows, thread-safety, dll-conflict

---

## 1. 问题背景
在 Windows 平台上使用 **pywebvue** 与 **sherpa-onnx**（包含 ONNX Runtime C++ 扩展）时，遇到以下问题：
- 进程级崩溃（访问违规）：当在后台线程创建 sherpa-onnx 识别器时触发。
- DLL 冲突：ONNX Runtime DLL 与 WebView2 (Chromium) 共享 MSVC runtime，预加载顺序不当导致崩溃。
- `evaluate_js` 线程限制：WebView2 要求 `evaluate_js` 只能在主线程调用，但现有 `_emit` 可能从任意线程调用。
- 缺乏主线程任务执行机制：无法安全地在主线程执行 C++ 扩展初始化。

---

## 2. 具体问题清单

### 2.1 线程安全问题：`evaluate_js` 可能从后台线程调用
- **位置**：`pywebvue/bridge.py` 的 `_emit` 方法
- **问题**：直接调用 `self._window.evaluate_js(js)`，在 Windows 上从非主线程调用会触发 COM 违规。
- **影响**：可能导致窗口崩溃或未定义行为。
- **当前修复**：已通过队列 + 定时器轮询方式绕过（用户项目自定义实现）。

### 2.2 缺少主线程任务执行 API
- **需求**：某些 C++ 扩展（如 ONNX Runtime）必须在创建 WebView2 的主线程上初始化。
- **缺失**：框架没有提供机制让后台线程安全地调度同步代码到主线程执行。
- **当前做法**：用户项目实现了一套命令模式（`run_on_main_thread`、`_task_queue`、`execute_task`）。
- **建议**：框架应内置此功能。

### 2.3 预加载点不足
- **问题**：框架没有提供在 WebView2 初始化前执行代码的钩子。
- **影响**：用户必须在 `main.py` 最顶层预加载 DLL，但此时 pywebvue 可能已导入。
- **建议**：添加 `pre_init` 钩子或延迟导入机制。

### 2.4 方法暴露的不确定性
- **现象**：以 `_` 开头的方法是否暴露给 JavaScript 不明确。
- **文档缺失**：未明确说明命名约定。
- **观察**：`@expose` 装饰器似乎暴露所有方法（包括 `_` 前缀），但不应依赖此行为。
- **建议**：明确文档或强制只暴露公共方法（无 `_` 前缀）。

### 2.5 定时器频率硬编码
- **现状**：`_setup_drag_drop` 中 `setInterval` 间隔硬编码（50ms、10ms）。
- **问题**：高频调用导致日志刷屏，且 `_execute_task` 空调用浪费 CPU。
- **建议**：提供配置选项或动态调整（如无任务时降低频率）。

### 2.6 DLL 加载顺序与 Windows 兼容性
- **根本原因**：ONNX Runtime DLL 与 WebView2 的 Chromium 使用不同版本的 MSVC runtime。
- **现有方案**：在 WebView2 前预加载 ONNX Runtime DLL，但框架未提供协助。
- **建议**：文档中明确 Windows 下第三方 C++ 扩展的加载顺序要求。

---

## 3. 建议的修复方案

### 3.1 为 Bridge 添加主线程任务执行能力
```python
# pywebvue/bridge.py
class Bridge:
    def run_on_main_thread(self, command: str, args: Any = None, timeout: float = 30.0) -> Any:
        """Schedule a task to run on main thread via execute_task."""
        # 实现参考用户项目
```

### 3.2 自动化任务执行定时器
```javascript
// pywebvue/app.py 的 _setup_drag_drop 中
window.setInterval(() => window.pywebview.api.execute_task(), 50);
```
- 改为可配置间隔（构造函数参数）。
- 添加自适应频率（有任务时快，空闲时慢）。

### 3.3 添加预初始化钩子
```python
# pywebvue/__init__.py 或 App 类
def pre_init(self, callback: Callable[[], None]):
    """Execute callback before WebView2 initialization."""
    # 用户在创建 App 前注册
```

### 3.4 明确方法暴露规则
- 只暴露公共方法（无 `_` 前缀）。
- 或提供装饰器选项 `@expose_private`。

### 3.5 增强文档
- Windows 特定注意事项（DLL 冲突、ONNX Runtime、COM 线程模型）。
- 线程安全指南。
- C++ 扩展集成最佳实践。

---

## 4. 最小可复现示例 (MRE)
用户项目已展示完整场景：
```python
# main.py
# 后台线程调用 run_on_main_thread("create_recognizer")
# execute_task 在主线程执行 sherpa_onnx.OnlineRecognizer.from_paraformer()
# 若无主线程执行，直接后台线程调用会崩溃
```

---

## 5. 环境信息
- **OS**：Windows 11 10.0.22631
- **Python**：3.10.8
- **pywebview**：6.1
- **sherpa-onnx**：1.12.35
- **ONNX Runtime**：来自 sherpa-onnx-bin
- **Browser**：WebView2 (Chromium)

---

## 6. 临时变通方案（用户项目实现）
- 通过队列实现线程安全事件发送。
- 通过命令模式实现主线程任务执行。
- 在 `main.py` 最顶层预加载 ONNX Runtime DLL。
- 降低定时器频率避免日志刷屏。

---

## 7. 优先级建议
1. **高**：提供主线程任务执行机制（`execute_task` / `run_on_main_thread`）。
2. **高**：文档化 Windows C++ 扩展的预加载要求。
3. **中**：添加预初始化钩子。
4. **低**：方法暴露规则澄清。

---

## 8. 相关文件
- `pywebvue/bridge.py`：需要添加任务系统。
- `pywebvue/app.py`：需要添加可配置定时器。
- `README.md` / `docs/`：需要 Windows 线程与 DLL 注意事项。

---

**附注**：用户项目已实现完整解决方案，可作为 PR 参考。建议将此功能合并到 pywebvue 核心。