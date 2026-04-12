# PyWebVue - 项目文档

## 一、项目概述

### 1.1 项目定位

PyWebVue 是一个极简的 Python + Vue 3 桥接框架，基于 pywebview 构建。核心理念是 **"克隆即开发"** -- 消除 Python 桌面应用开发中的样板代码，让开发者只需关注业务逻辑，无需处理繁琐的前后端通信机制。

### 1.2 核心价值

- **极简设计**: 框架核心仅 3 个文件（`app.py` + `bridge.py` + `__init__.py`），约 200 行 Python 代码
- **双向通信**: Python 方法通过 `@expose` 装饰器暴露给前端；Python 也可通过 `_emit()` 主动推送事件到前端
- **统一响应格式**: 所有通信遵循 `{"success": bool, "data": Any}` 约定，前端错误处理一致
- **开箱即用**: 内置一键开发脚本（dev.bat / dev.sh）、Vite 热重载、PyInstaller 打包脚本
- **多平台支持**: Windows（Edge WebView2）、macOS（Cocoa WebKit）、Linux（GTK WebKit），以及 Android（Buildozer）

### 1.3 技术栈

| 层级 | 技术选型 | 版本 |
|------|---------|------|
| 后端语言 | Python | >= 3.10 |
| 桌面容器 | pywebview | >= 6.0 |
| 前端框架 | Vue 3 + Composition API | ^3.5 |
| 前端语言 | TypeScript | ~5.7 |
| 构建工具 | Vite | ^6.0 |
| 打包工具 | PyInstaller | >= 6.19 |
| 包管理 | uv (Python) + bun/npm (前端) | - |
| 构建系统 | hatchling | - |

---

## 二、系统架构

### 2.1 整体架构

```
+------------------+     +--------------------+     +------------------+
|   Vue 3 前端     |     |   pywebview        |     |   Python 后端    |
|   (TypeScript)   |     |   WebView 窗口     |     |                  |
|                  |     |                    |     |                  |
| call() ----------+---->| window.pywebview   +---->| @expose 方法     |
|                  |     |   .api.method()    |     |   返回 JSON      |
| onEvent() <------+-----+ dispatchEvent()   <-----+ _emit() 推送     |
|                  |     | CustomEvent        |     |                  |
+------------------+     +--------------------+     +------------------+
```

### 2.2 项目结构

```
pywebvue-framework/
  main.py                # 应用入口 -- 定义 Bridge 子类和 @expose 方法
  dev.py                 # 一键开发启动器（自动装依赖 + 启动 Vite + 启动窗口）
  dev.bat / dev.sh       # 一键启动脚本
  build.py               # 生产打包脚本（桌面 / Android）
  app.spec               # PyInstaller 打包配置
  pyproject.toml         # Python 项目元数据
  pywebvue/              # 框架核心（3 个文件）
    __init__.py            # 公共导出: App, Bridge, expose
    app.py                 # App 类: 窗口管理, dev/prod 自动切换, 拖拽支持
    bridge.py              # Bridge 基类 + @expose 装饰器 + 事件推送
  frontend/              # Vue 前端应用
    index.html             # Vite 入口
    package.json           # 前端依赖
    vite.config.ts         # Vite 配置（输出到 ../frontend_dist/）
    src/
      main.ts              # Vue 启动
      App.vue              # 根组件（开发者的主战场）
      bridge.ts            # TypeScript 桥接: call(), onEvent(), waitForPyWebView()
      env.d.ts             # pywebview 类型声明
  docs/                   # 文档
    development.md         # 开发指南
    api.md                 # API 参考
    building.md            # 构建配置
```

### 2.3 核心通信机制

**前端 -> Python（请求-响应模式）**:
1. Vue 组件调用 `call<T>("method_name", arg1, arg2)`
2. bridge.ts 通过 `window.pywebview.api.method_name(arg1, arg2)` 调用 Python
3. Python 的 `@expose` 装饰器包装方法，自动 try/except
4. 返回统一格式 `{"success": true, "data": ...}` 或 `{"success": false, "error": "..."}`

**Python -> 前端（事件推送模式）**:
1. Python 调用 `self._emit("event_name", {"key": "value"})`
2. bridge.py 通过 `window.evaluate_js()` 执行 `document.dispatchEvent(new CustomEvent('pywebvue:event_name', {detail: data}))`
3. 前端通过 `onEvent<T>("event_name", handler)` 监听并处理

---

## 三、开发历程（基于 Git Commit 记录）

### 3.1 完整时间线

| 日期 | Commit | 变更量 | 说明 |
|------|--------|--------|------|
| 03-28 | `8ae3b73` | +181 | 项目初始化：.gitignore, LICENSE, README |
| 03-28 | `885d476` | +2,038 | 添加 PRD 文档、技术调研文档、pyproject.toml、main.py |
| 03-28 | `9108229` | +2,512 | **初始化框架核心结构** -- 实现完整的重型架构 |
| 03-28 | `69b69a9` | +1,780 | 添加 CLI 脚手架系统（模板化项目创建） |
| 03-28 | `d215a0a` | +4,562 | 添加 file-tool / process-tool 示例应用 + 构建命令 |
| 03-28 | `c941710` | +3,052 | 完善用户指南、开发指南、AI 协作文档 |
| 03-28 | `fb95487` | +628 | 中文开发指南 + bun.lock 忽略 |
| 03-28 | `bf024b5` | +207 | README 重写为完整框架介绍 |
| 03-28 | `0fa66d3` | +1,713 | 修复 file-tool 示例的哈希计算 + UI 改进 |
| 03-29 | `1f5f3c7` | -5 | 移除 uv 脚本内嵌配置 |
| 03-30 | `925e1b3` | **-13,569 / +2,166** | **架构重构** -- 删除旧重型架构，重建为极简框架 |
| 03-30 | `33fb92b` | merge | 合并 PR #1 |
| 03-30 | `e2b47ed` | +2/-1 | 修复 CustomEvent 冒泡问题 |

### 3.2 开发阶段详述

#### 阶段 1: 需求调研与规划（03-28 上午）

**背景**: 作为一个熟悉 Python 但对 TypeScript + Vue 3 前端技术仅有基础了解的开发者，面临的核心问题是：如何在不深入学习前端工程化的情况下，利用 Python 的后端能力 + 现代 Vue 3 前端快速构建跨平台桌面应用？

**关键产出**:
- `docs/PRD-2026-03-28.md`（1,275 行）-- 完整的产品需求文档，定义了框架的功能范围、用户场景、技术选型
- `docs/explore-2026-03-28.md`（745 行）-- 技术调研，对比了 Electron、Tauri、pywebview 等方案
- 技术选型决策：选择 pywebview 而非 Electron/Tauri，因为 Python 后端 + WebView 是最自然的前后端分离方案

#### 阶段 2: 第一版架构实现（03-28 下午）

**架构设计**: 采用了传统框架的"功能完备"思路，实现了：

```
src/pywebvue/
  __init__.py       # 公共导出
  api_base.py       # API 基类（107 行）
  app.py            # 应用核心（423 行）-- 窗口、配置、生命周期、多窗口
  config.py         # YAML 配置解析（126 行）
  constants.py      # 常量定义（10 行）
  dialog.py         # 原生对话框封装（76 行）
  event_bus.py      # 事件总线（82 行）
  logger.py         # 日志系统（81 行）
  process.py        # 子进程管理（377 行）
  result.py         # 结果类型（131 行）
  singleton.py      # 单例模式（122 行）
  cli.py            # CLI 脚手架（364 行）
  templates/        # 项目模板（30+ 模板文件）
```

同时创建了两个示例应用：
- `examples/file-tool/` -- 文件哈希计算工具，展示文件拖拽、进度条、日志面板
- `examples/process-tool/` -- 进程管理工具，展示子进程控制、状态监控

**阶段特点**: 功能全面，代码量大（核心约 2,000 行 + 模板/示例约 8,000 行），但使用复杂度高。

#### 阶段 3: 文档与示例完善（03-28 晚）

- 编写了完整的中文/英文用户指南和开发指南
- 为 AI 辅助开发编写了 `to_ai/pywebvue-framework-instruction.md`（880 行）-- 这是 VibeCoding 实践的关键投入
- 修复了 file-tool 示例中的哈希计算 bug 并改进了 UI

#### 阶段 4: 架构重构 -- 从"完备"到"极简"（03-29 ~ 03-30）

**这是整个项目最关键的决策点。**

**问题发现**: 在实际使用和持续开发中，发现第一版架构存在以下问题：
1. **过度设计**: singleton、result 类型、logger 等模块增加了理解成本，但对实际开发帮助不大
2. **CLI 脚手架过重**: 模板系统维护成本高，用户更需要的是"克隆即用"而非"脚手架生成"
3. **示例代码与应用代码耦合**: examples/ 目录增加了仓库体积和心智负担
4. **配置复杂度**: config.yaml 解析增加了不必要的抽象层

**重构决策**: 彻底简化

| 维度 | 重构前 | 重构后 |
|------|--------|--------|
| 核心文件数 | 12 个 .py 文件 | 3 个 .py 文件 |
| 核心代码量 | ~2,000 行 | ~200 行 |
| 配置方式 | config.yaml + 常量 | 构造函数参数 |
| 项目初始化 | CLI 脚手架生成 | git clone |
| 示例应用 | 独立 examples/ 目录 | 集成到 main.py + App.vue |
| 文档 | 多份冗长指南 | 3 份精简文档 |

**具体操作**（commit `925e1b3`，变更量 -13,569 / +2,166）:
- 删除: src/pywebvue/ 全部 12 个模块 + templates/ 30+ 模板文件 + examples/ 两个示例应用 + 旧文档
- 新建:
  - `pywebvue/app.py`（119 行）-- 窗口管理 + dev/prod 切换 + 拖拽支持
  - `pywebvue/bridge.py`（71 行）-- Bridge 基类 + @expose + 事件推送
  - `pywebvue/__init__.py`（6 行）-- 公共导出
  - `frontend/src/bridge.ts`（82 行）-- TypeScript 桥接层
  - `dev.py`（232 行）-- 一键开发启动器
  - `build.py`（446 行）-- 一键打包脚本
  - `docs/` 精简文档（api.md, development.md, building.md）

#### 阶段 5: 收尾与修复（03-30）

- 修复 CustomEvent 冒泡问题（commit `e2b47ed`）-- 确保嵌套组件也能正确接收 Python 推送的事件
- 通过 PR 合并方式整合重构代码，保持 main 分支的整洁

### 3.3 关键技术决策总结

| 决策 | 选择 | 理由 |
|------|------|------|
| 桌面容器 | pywebview 而非 Electron/Tauri | Python 原生生态，无需 Node.js 后端 |
| 通信方式 | window.pywebview.api + CustomEvent | pywebview 原生支持，无需 HTTP 服务 |
| 错误处理 | @expose 装饰器自动 try/except | 统一错误格式，前端无需单独处理异常 |
| 前端框架 | Vue 3 Composition API | `<script setup>` 语法简洁，TypeScript 支持好 |
| 开发模式 | Vite dev server + pywebview 窗口 | 前端热重载 + 后端原生窗口同时调试 |
| 生产模式 | PyInstaller 打包 | Python 生态最成熟的打包方案 |
| 架构演进 | 重型 -> 极简 | 实际使用反馈驱动，减少 90% 核心代码 |

---

## 四、核心 API

### Python 端

```python
from pywebvue import App, Bridge, expose

class MyApi(Bridge):
    @expose
    def greet(self, name: str) -> dict:
        return {"success": True, "data": f"Hello, {name}!"}

    def notify(self):
        self._emit("status", {"msg": "done"})

api = MyApi()
App(api, title="My App", frontend_dir="frontend_dist").run()
```

### TypeScript 端

```ts
import { call, onEvent, waitForPyWebView } from "./bridge"

await waitForPyWebView()

// 调用 Python
const res = await call<string>("greet", "World")
console.log(res.data)  // "Hello, World!"

// 监听 Python 事件
const off = onEvent<{ msg: string }>("status", ({ msg }) => console.log(msg))
off()  // 取消监听
```

---

## 五、快速开始

```bash
# 1. 安装 uv 和 bun/npm
# 2. 克隆项目
git clone <repo-url> && cd pywebvue-framework

# 3. 一键启动开发环境
dev.bat              # Windows
./dev.sh             # macOS / Linux
```

### 开发命令

```bash
uv run dev.py              # 启动 Vite + 窗口（默认）
uv run dev.py --no-vite    # 加载构建产物（测试生产构建）
uv run dev.py --setup      # 仅安装依赖
```

### 生产构建

```bash
cd frontend && npm run build && cd ..
uv run build.py              # 桌面 onedir
uv run build.py --onefile    # 桌面单 exe
uv run build.py --android    # Android APK（macOS/Linux）
```

---

## 六、许可

MIT License - Copyright (c) 2026 wish
