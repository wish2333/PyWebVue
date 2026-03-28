# PyWebVue Framework - Phase 2 实现记录

> Phase 2: 脚手架 CLI + 前端模板
> 实现日期：2026-03-28
> 测试指南：`docs/Phase2_Test_Instruction-2026-03-28.md`

---

## Phase 2 实现概要

### 目标

实现 `pywebvue create` CLI 命令和完整的 Vue 3 + Vite + TailwindCSS + DaisyUI + TypeScript 前端工程模板，使用户可以一条命令生成可运行的项目骨架。

### 实际交付

| 类别 | 文件数 | 说明 |
|:---|:---|:---|
| CLI 模块 | 1 | `src/pywebvue/cli.py` |
| 后端模板 | 5 | pyproject.toml, main.py, app.py, config.yaml, .gitignore |
| 前端基础设施 | 9 | package.json, vite.config.ts, tailwind.config.ts, postcss.config.js, tsconfig.json, tsconfig.node.json, index.html, env.d.ts, style.css |
| 前端类型与工具 | 3 | types/index.ts, api.ts, event-bus.ts |
| Vue 入口 | 2 | main.ts, App.vue |
| Vue 组件 | 6 | Toast, FileDrop, LogPanel, ProgressBar, DataTable, StatusBadge |
| 修改已有文件 | 1 | pyproject.toml（注册 CLI 入口点） |
| **合计** | **27** | 26 个新文件 + 1 个修改 |

---

## 2.1 CLI 模块 (`src/pywebvue/cli.py`)

### 实现方案

使用 `argparse`（而非 `click`），零外部依赖。

### 命令格式

```bash
pywebvue create <project_name> [--title TITLE] [--width WIDTH] [--height HEIGHT]
```

### 模板变量

| 变量 | 来源 | 用途 |
|:---|:---|:---|
| `{{PROJECT_NAME}}` | 必填参数 | Python 包名、目录名 |
| `{{PROJECT_TITLE}}` | `--title` 或自动推导 | 窗口标题、HTML title |
| `{{CLASS_NAME}}` | 自动推导 (PascalCase) | API 类名 |
| `{{WIDTH}}` | `--width` (默认 900) | 窗口宽度 |
| `{{HEIGHT}}` | `--height` (默认 650) | 窗口高度 |

### 核心函数

```
main()                -- CLI 入口，argparse 解析
create_project(args)  -- 脚手架生成主逻辑
_pascal_case(name)    -- snake_case -> PascalCase 转换
_substitute(content)  -- {{KEY}} 占位符替换
_validate_project_name(name)  -- Python 标识符 + 关键字校验
_run_command(cmd, cwd)        -- 子进程执行（bun install）
```

### 设计决策

- **模板路径**：`Path(__file__).parent / "templates" / "project"`，随包安装分发
- **变量替换**：简单 `str.replace()`，无 Jinja2。5 个固定变量名与 Vue 的 `{{ }}` 模板插值不冲突（Vue 的 `{{ }}` 中的变量名不匹配任何模板变量 key）
- **bun install**：生成后自动执行；`bun.lockb` 已存在时跳过；bun 未安装时优雅降级

### 入口点注册

```toml
# pyproject.toml
[project.scripts]
pywebvue = "pywebvue.cli:main"
```

---

## 2.2 后端模板

### `main.py.tpl`

```python
from pywebvue import App

if __name__ == "__main__":
    App(config="config.yaml").run()
```

最简入口，两行代码启动应用。

### `app.py.tpl`

```python
class {{CLASS_NAME}}Api(ApiBase):
    def health_check(self) -> Result:
        return Result.ok(data={"status": "running"})

    def on_file_drop(self, file_paths: list[str]) -> None:
        for path in file_paths:
            self.logger.info(f"File dropped: {path}")
            self.emit("file:dropped", {"path": path})
```

用户可在此基础上添加业务方法。所有 public 方法自动暴露给前端。

### `config.yaml.tpl`

完整镜像 `AppConfig` 的 dataclass 结构，包含 `app`、`logging`、`process`、`business` 四个顶层节点。脚手架生成时填入用户指定的 `name`、`title`、`width`、`height`。

### `pyproject.toml.tpl`

```toml
dependencies = [
    "pywebvue-framework>=0.1.0",
    "loguru>=0.7.3",
    "pywebview>=6.1",
    "pyyaml>=6.0.3",
]
```

注意：`loguru`、`pywebview`、`pyyaml` 也被框架传递依赖，这里显式声明是为了给用户 `uv run` 提供直接的可执行环境。

---

## 2.3 前端基础设施

### 依赖版本

| 包 | 版本要求 | 说明 |
|:---|:---|:---|
| vue | ^3.4.21 | 运行时依赖 |
| vite | ^5.1.4 | 构建工具 |
| tailwindcss | ^3.4.1 | 原子化 CSS |
| daisyui | ^4.7.2 | 组件库 |
| typescript | ^5.3.3 | 类型检查 |
| vue-tsc | ^2.0.6 | Vue TypeScript 支持 |

### vite.config.ts.tpl

关键配置：
- `base: "./"` -- pywebview 加载本地文件需要相对路径
- `build.outDir: "../dist"` -- 构建产物输出到项目根目录
- `resolve.alias: "@" -> "src"` -- `@/` 路径别名
- `server.strictPort: true` -- 端口被占用时报错而非自动换端口

### tsconfig.json.tpl

- `target: ES2020`, `module: ESNext`
- `moduleResolution: bundler` -- 与 Vite 兼容
- `paths: { "@/*": ["src/*"] }` -- 与 vite.config.ts 别名一致
- `references: [{ "path": "./tsconfig.node.json" }]` -- 隔离 vite.config.ts 的类型

### env.d.ts.tpl

声明全局类型，使所有 TypeScript 文件获得 autocomplete：

```typescript
interface Window {
  pywebvue: PyWebVue;       // 事件总线
  pywebview: PyWebView;     // JS API 桥接
  __pywebvue_dispatch: fn;  // 内部分发函数
}
```

---

## 2.4 前端类型与工具库

### `types/index.ts.tpl`

与 Python `result.py` 中 `ErrCode` 类精确镜像：

```typescript
export const ErrCode = {
  OK: 0, UNKNOWN: 1, PARAM_INVALID: 2, ...
  FILE_NOT_FOUND: 1001, ...
  API_CALL_FAILED: 3001, API_NOT_READY: 3002,
} as const;
```

接口定义：
- `ApiResult<T>` -- 对应 `Result.to_dict()` 的 `{code, msg, data}` 形状
- `isOk(result)` -- 类型守卫，`result.code === 0` 时收窄为成功类型
- `LogEntry`, `ProgressPayload`, `ToastOptions`, `ColumnDef`, `StatusState` -- 组件类型

### `api.ts.tpl`

```typescript
waitForReady()              // 监听 pywebviewready DOM 事件
call<T>(method, ...args)    // 泛型 API 调用，返回 ApiResult<T>
```

`call()` 内部做了完整错误处理：
- `window.pywebview` 不存在时返回 `API_NOT_READY`
- 方法不存在时返回 `UNKNOWN`
- 调用异常时返回 `API_CALL_FAILED` 并附带错误信息

### `event-bus.ts.tpl`

```typescript
useEvent(name, callback)              // Vue Composable，自动 subscribe/unsubscribe
waitForEvent<T>(name, timeout?)       // 等待一次性事件，支持超时
```

`useEvent` 在 `onMounted` 中注册、`onUnmounted` 中注销，避免内存泄漏。

---

## 2.5 Vue 组件

### Toast (`Toast.vue.tpl`)

- **模式**：provide/inject。`App.vue` 渲染 `<Toast>` 并 provide toast API；子组件通过 `inject('toast')` 调用
- **实现**：Teleport 到 body，使用 DaisyUI `alert` + `toast` 类
- **功能**：4 种类型 (success/error/warning/info)，4 秒自动消失，手动关闭按钮
- **已知问题**：组件内有一个冗余的 `provide` 声明（被 `App.vue` 的同名 provide 覆盖），不影响功能但应清理

### FileDrop (`FileDrop.vue.tpl`)

- **功能**：拖拽区域 + Browse 按钮
- **交互**：拖入时视觉反馈（边框变色 + 背景高亮）
- **事件**：通过 `useEvent("file:dropped")` 接收后端推送的文件路径
- **API**：Browse 按钮尝试调用 `select_file`（需用户在 `app.py` 中实现）

### LogPanel (`LogPanel.vue.tpl`)

- **数据源**：`useEvent("log:add")` 接收后端日志
- **功能**：级别过滤下拉框（ALL/DEBUG/INFO/WARNING/ERROR/CRITICAL）、自动滚动开关
- **限制**：最多保留 500 行日志（`MAX_LINES = 500`），超出自动裁剪

### ProgressBar (`ProgressBar.vue.tpl`)

- **数据源**：通过 props 接收 `ProgressPayload`（由 `App.vue` 从 `useEvent("progress:update")` 获取）
- **样式**：DaisyUI `<progress>` 元素，根据百分比动态变色（warning < 50% < primary < 100% = success）
- **显示**：百分比徽章 + 自定义 label

### DataTable (`DataTable.vue.tpl`)

- **纯 props 驱动**：`columns: ColumnDef[]` + `rows: Record<string, unknown>[]`
- **功能**：DaisyUI `table table-zebra` 样式，空状态提示

### StatusBadge (`StatusBadge.vue.tpl`)

- **5 种状态**：idle (ghost) / running (primary) / paused (warning) / error (error) / done (success)
- **纯展示组件**：接收 `status: StatusState` prop，映射到 DaisyUI badge 颜色

---

## 2.6 App.vue.tpl

### 布局结构

```
+--[navbar]------------------------------------------+
|  {{PROJECT_TITLE}}  v0.1.0           [Connected]   |
+----------------------------------------------------+
|                                                    |
|  [Actions]          Health Check                    |
|  [File Drop]        [drag zone] + [Browse]         |
|  [ProgressBar]      (hidden until progress event)  |
|  [LogPanel]         [filter] [auto-scroll] [logs]  |
|                                                    |
+--[footer]------------------------------------------+
|  Backend: Online | Last API: OK - status: running  |
+----------------------------------------------------+
```

### 事件订阅

| 事件 | 处理 |
|:---|:---|
| `log:add` | 打印到浏览器 console |
| `progress:update` | 更新进度条 props |
| `file:dropped` | 显示 Toast 通知 |

### 生命周期

1. `onMounted` -> `waitForReady()` -> 设置 `backendReady = true`
2. 等待就绪后可点击 "Health Check" 调用后端 API
3. 独立运行（无 pywebview）时显示 "Backend not available" 提示

---

## 2.7 与原计划的偏差

| 计划项 | 变更 | 原因 |
|:---|:---|:---|
| PyInstaller spec 模板 | 推迟到 Phase 3 | Phase 2 聚焦脚手架核心功能，spec 模板需要与打包流程联动验证 |
| npm fallback | 不实现 | 用户明确选择 bun only |
| `require('daisyui')` | 实际使用此写法 | bun 对 ESM 的 `require` 有兼容支持，构建通过 |

---

## Phase 2 验证结果

| 测试项 | 状态 |
|:---|:---|
| `from pywebvue.cli import main` | 通过 |
| `uv run pywebvue --help` | 通过 |
| `uv run pywebvue create test_tool --title "Test Tool" --width 800 --height 600` | 通过（26 文件全部生成，变量替换正确） |
| `bun run build`（vue-tsc + vite） | 通过（零类型错误，产物包含 index.html + assets） |
| `bun dev`（开发服务器） | 通过（页面正常渲染，组件可用） |
| 重复目录检测 | 通过 |
| 无效项目名检测 | 通过 |
| 省略可选参数自动推导 | 通过 |

---

## Phase 3 调整建议

基于 Phase 2 的实现经验，对 Phase 3 提出以下调整：

### 3.1 `cli.py` 代码质量改进

1. **移动 `import keyword` 到文件顶部**：当前放在两个函数定义之间，不符合 PEP 8
2. **模板变量防碰撞检查**：`_substitute()` 可增加断言，确保替换后文件中不再包含未替换的 `{{PROJECT_*}}` 占位符
3. **增加 `--force` 参数**：目标目录已存在时允许强制覆盖（需确认提示）

### 3.2 前端模板改进

1. **tailwind.config.ts.tpl 中的 `require`**：改为 `import daisyui from 'daisyui'` 以符合 ESM 标准
2. **Toast.vue.tpl 冗余 provide**：移除子组件中的 `provide('toast')`，仅保留 `App.vue` 中的声明
3. **LogPanel 新增清空按钮**：当前只支持过滤和自动滚动，缺少一键清空功能
4. **ProgressBar v-if 条件**：当前无进度时完全不渲染，可改为显示一个空进度条（更直观）

### 3.3 PyInstaller spec 模板

Phase 3 需要创建三套 spec 模板：
- `{name}.spec.tpl` (onedir)
- `{name}-onefile.spec.tpl`
- `{name}-debug.spec.tpl`

变量：`{{PROJECT_NAME}}`、`{{PROJECT_TITLE}}`、`{{CLASS_NAME}}`

### 3.4 生成的 pyproject.toml.tpl 增强

当前缺少开发脚本快捷方式，Phase 3 可增加：

```toml
[tool.uv.scripts]
dev = "python main.py --with-vite"
build-frontend = "sh -c 'cd frontend && bun run build'"
```

> 注意：Phase 1 的 `app.py` 已实现 `--with-vite` 参数支持和 Vite 自动启动/清理逻辑。

---

## 当前项目架构

```
src/pywebvue/
  __init__.py          # 公开 API 导出
  app.py               # App 类 + ApiProxy（窗口生命周期、Vite 自动启动）
  api_base.py          # ApiBase 基类（业务方法基座）
  cli.py               # CLI 入口（pywebvue create）
  config.py            # YAML 配置加载（AppConfig dataclass）
  constants.py         # 框架常量、版本号
  dialog.py            # 系统对话框封装
  event_bus.py         # Python->前端事件桥接（BRIDGE_JS）
  logger.py            # loguru 双通道日志（console + frontend）
  process.py           # 子进程管理（start/pause/resume/stop）
  result.py            # Result dataclass + ErrCode 错误码
  singleton.py         # 跨平台单实例锁
  templates/
    project/           # 脚手架模板（25 个 .tpl 文件）
      .gitignore.tpl
      main.py.tpl
      app.py.tpl
      config.yaml.tpl
      pyproject.toml.tpl
      frontend/        # 前端工程模板
        index.html.tpl
        package.json.tpl
        vite.config.ts.tpl
        tailwind.config.ts.tpl
        postcss.config.js.tpl
        tsconfig.json.tpl
        tsconfig.node.json.tpl
        src/
          main.ts.tpl
          App.vue.tpl
          api.ts.tpl
          event-bus.ts.tpl
          env.d.ts.tpl
          assets/style.css.tpl
          types/index.ts.tpl
          components/
            Toast.vue.tpl
            FileDrop.vue.tpl
            LogPanel.vue.tpl
            ProgressBar.vue.tpl
            DataTable.vue.tpl
            StatusBadge.vue.tpl
```
