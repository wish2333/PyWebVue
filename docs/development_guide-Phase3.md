# PyWebVue Framework - Phase 3 实现记录

> Phase 3: 打包支持 + 开发体验增强
> 实现日期：2026-03-28
> 测试指南：`docs/Phase3_Test_Instruction-2026-03-28.md`

---

## Phase 3 实现概要

### 目标

基于 Phase 1 (核心模块) 和 Phase 2 (脚手架 CLI + 前端模板) 的成果，实现 PyInstaller 打包支持、CLI 增强（`--force`、`build` 子命令、模板碰撞检测）、前端模板 bug 修复与体验改进。

### 实际交付

| 类别 | 文件数 | 说明 |
|:---|:---|:---|
| CLI 模块修改 | 1 | `src/pywebvue/cli.py` -- PEP 8、`--force`、碰撞检测、`build` 子命令 |
| 前端模板修改 | 3 | Toast.vue.tpl、LogPanel.vue.tpl、ProgressBar.vue.tpl |
| 类型定义修改 | 1 | `types/index.ts.tpl` -- 新增 `id` 字段 |
| App.vue 模板修改 | 1 | `App.vue.tpl` -- toast ID 分配 |
| 项目模板修改 | 2 | `pyproject.toml.tpl`、`.gitignore.tpl` |
| PyInstaller spec 模板 | 3 | onedir、onefile、debug 三套 spec |
| **合计** | **11** | 8 个修改 + 3 个新建 |

---

## 3.1 CLI 改进 (`src/pywebvue/cli.py`)

### 3.1.1 PEP 8 修复

| 变更 | 说明 |
|:---|:---|
| `import keyword` 移至文件顶部 | 原 Phase 2 放在 `_validate_project_name` 与 `_run_command` 之间，不符合 PEP 8 |
| `import yaml` 新增 | `build_project` 需要读取 `config.yaml` 以发现项目名 |

### 3.1.2 `--force` 标志

```bash
pywebvue create my_app --force
```

行为：
- 不带 `--force`：目标目录已存在时，报错并提示 `Use --force to overwrite`
- 带 `--force`：输出 `Overwrite my_app? [y/N]` 确认提示，输入 `y` 后执行 `shutil.rmtree()`，否则中止

### 3.1.3 模板碰撞检测

新增函数 `_check_unsubstituted(content) -> list[str]`，在模板替换后检测文件中是否残留未替换的 `{{UPPER_CASE}}` 占位符。

正则表达式：
```python
_UNSUBSTITUTED_PATTERN = re.compile(r"\{\{[A-Z_][A-Z0-9_]*\}\}")
```

此模式只匹配 `{{UPPER_CASE}}`（全大写 + 下划线），不会误报 Vue 模板中的 `{{ camelCase }}` 插值。检测结果以 WARNING 级别输出，不阻断脚手架流程。

### 3.1.4 文件名变量替换

Phase 2 中模板文件名中的 `{{PROJECT_NAME}}` 不会被替换（仅替换文件内容）。Phase 3 新增了文件名级别的替换逻辑：

```python
# Strip .tpl suffix
if dest_file.name.endswith(".tpl"):
    dest_file = dest_file.with_name(dest_file.name[:-4])

# Substitute {{VARIABLES}} in filename
dest_name = _substitute(dest_file.name, variables)
if dest_name != dest_file.name:
    dest_file = dest_file.with_name(dest_name)
```

这使得 PyInstaller spec 模板文件名如 `{{PROJECT_NAME}}.spec.tpl` 能正确生成为 `my_app.spec`。

### 3.1.5 `build` 子命令

```bash
pywebvue build [--mode onedir|onefile|debug] [--spec FILE] [--skip-frontend]
```

执行流程：
1. 从 `config.yaml` 的 `app.name` 或当前目录名发现项目名
2. 构建前端：`bun run build`（除非 `--skip-frontend`）；构建失败时直接退出
3. 根据 `--mode` 选择 spec 文件（默认 onedir），或使用 `--spec` 指定自定义 spec
4. 通过 `shutil.which("pyinstaller")` 检查 PyInstaller 可用性
5. 执行 `pyinstaller --noconfirm <spec_file>`

| 参数 | 默认值 | 说明 |
|:---|:---|:---|
| `--mode` | `onedir` | `onedir`（文件夹）、`onefile`（单 exe）、`debug`（控制台模式） |
| `--spec` | 自动推导 | 自定义 .spec 文件路径，覆盖 `--mode` |
| `--skip-frontend` | false | 跳过前端构建步骤 |

### 3.1.6 `_run_command` 增强

返回值从 `None` 改为 `bool`（成功/失败），新增 `check` 参数：
- `check=False`（默认）：失败仅 warning 日志，不中断
- `check=True`：失败时 `sys.exit(1)`

`build_project` 中前端构建和 PyInstaller 执行均使用 `check=True`。

### 3.1.7 "Next steps" 消息简化

从 Phase 2 的 4 行简化为 2 行：

```
cd <project>
uv run python main.py          # Run with Vite dev mode
uv run pywebvue build           # Package for distribution
```

### 3.1.8 核心函数一览

```
main()                              -- CLI 入口，argparse 解析
create_project(args)                -- 脚手架生成（含 --force、碰撞检测、文件名替换）
build_project(args)                 -- PyInstaller 打包主流程
_pascal_case(name)                  -- snake_case -> PascalCase
_substitute(content, variables)     -- {{KEY}} 占位符替换
_check_unsubstituted(content)       -- 未替换占位符检测
_validate_project_name(name)        -- Python 标识符 + 关键字校验
_run_command(cmd, cwd, check)       -- 子进程执行（返回 bool）
```

---

## 3.2 前端模板修复

### 3.2.1 Toast.vue.tpl

| 变更 | 说明 |
|:---|:---|
| 移除 `provide` import | `provide` 不再从 vue 导入 |
| 删除冗余 `provide("toast", ...)` | 原 Phase 2 中 Toast 自身声明了一个 noop provide，覆盖了 `App.vue` 中的真实 handler。子组件通过 `inject('toast')` 调用时拿到的是 noop 而非真实函数 |
| 修复 `localItems` 赋值 bug | 原代码 `localItems = localItems.filter(...)` 缺少 `.value`，应为 `localItems.value = localItems.value.filter(...)` |
| `v-for` key 改为 `item.id` | 原使用数组 index 作为 key，toast 从中间删除时会导致 DOM 复用错误 |

### 3.2.2 LogPanel.vue.tpl

| 变更 | 说明 |
|:---|:---|
| 新增 `clearLogs()` 函数 | 同时清空 `logs.value` 和 `filteredLogs.value` |
| 新增 Clear 按钮 | 位于 auto-scroll 复选框右侧，`btn btn-xs btn-ghost` 样式 |
| 新增 `_logId` 计数器 | 为每条日志分配唯一 `id`，避免 `v-for` 使用 index 作为 key |
| 使用不可变模式追加日志 | `logs.value.push(entry)` 改为 `logs.value = [...logs.value, entry]` |
| `v-for` key 改为 `entry.id` | 配合 `LogEntry.id` 字段 |

### 3.2.3 ProgressBar.vue.tpl

| 变更 | 说明 |
|:---|:---|
| 移除 `v-if="progress"` | 卡片始终渲染，不再在无进度时隐藏整个组件 |
| 新增 Idle 空状态 | 无进度时显示 `badge-ghost` 的 "Idle" 徽章 |
| 进度条条件样式 | 有进度时使用 `barClass`（warning/primary/success），无进度时使用 `progress-info` |
| 进度条条件 value | `:value="progress ? percentage : undefined"`，无进度时 HTML `<progress>` 显示为 indeterminate（不确定进度条） |
| 新增空状态文本 | 无进度时显示 "No active progress" 提示文字 |

### 3.2.4 types/index.ts.tpl

为支持稳定的 `v-for` key，`LogEntry` 和 `ToastOptions` 新增 `id: number` 字段：

```typescript
export interface LogEntry {
  id: number;           // 新增
  level: string;
  message: string;
  timestamp?: string;
  class_name?: string;
}

export interface ToastOptions {
  id: number;           // 新增
  type: "success" | "error" | "warning" | "info";
  message: string;
  duration?: number;
}
```

### 3.2.5 App.vue.tpl

Toast ID 分配逻辑：

```typescript
let _toastId = 0;
function showToast(options: ToastOptions) {
  toastQueue.push({ ...options, id: ++_toastId });
}
```

---

## 3.3 项目模板更新

### 3.3.1 pyproject.toml.tpl

新增两个配置块：

```toml
[dependency-groups]
dev = [
    "pyinstaller>=6.0",
]

[tool.uv.scripts]
dev = "python main.py --with-vite"
build-frontend = "cd frontend && bun run build"
build-app = "pyinstaller {{PROJECT_NAME}}.spec"
```

用户可通过 `uv run dev`、`uv run build-frontend`、`uv run build-app` 快捷执行。

### 3.3.2 .gitignore.tpl

新增 PyInstaller 备份文件规则：

```
# PyInstaller
*.spec.bak
```

---

## 3.4 PyInstaller Spec 模板

### 3.4.1 模板变量

| 变量 | 示例值 | 用途 |
|:---|:---|:---|
| `{{PROJECT_NAME}}` | `my_app` | 文件名、pyinstaller 引用 |
| `{{PROJECT_TITLE}}` | `My App` | EXE/COLLECT 的 `name` 字段 |

### 3.4.2 共享 Analysis 配置

三套 spec 共享相同的 Analysis 块：

| 配置项 | 值 |
|:---|:---|
| 入口 | `main.py` |
| datas | `frontend/dist/`、`assets/`、`config.yaml` |
| hiddenimports | `pywebvue`、`pywebview`、`loguru`、`yaml` + `collect_submodules("pywebvue")` |
| 默认 excludes (onedir/onefile) | matplotlib、numpy、pandas、scipy、tkinter、unittest、test |

用户可通过顶部的 `EXTRA_*` 列表自由扩展：

```python
EXTRA_DATAS = []            # 额外数据文件
EXTRA_BINARIES = []         # 额外二进制文件
EXTRA_HIDDEN_IMPORTS = []   # 额外隐藏导入
EXTRA_EXCLUDES = []         # 额外排除项
```

### 3.4.3 三套 spec 差异对比

| 特性 | onedir | onefile | debug |
|:---|:---|:---|:---|
| 文件名 | `{name}.spec` | `{name}-onefile.spec` | `{name}-debug.spec` |
| EXE name | `{{PROJECT_TITLE}}` | `{{PROJECT_TITLE}}` | `{{PROJECT_TITLE}}-debug` |
| `exclude_binaries` | True | False | True |
| COLLECT 块 | 有 | 无 | 有 |
| `console` | False | False | True |
| `debug` | False | False | True |
| `upx` | True | True | False |
| 默认 excludes | 有 | 有 | 无（保留所有依赖用于调试） |
| `icon` | `assets/icon.ico` | `assets/icon.ico` | `assets/icon.ico` |

### 3.4.4 onedir vs onefile 技术差异

**onedir** (推荐)：
- EXE 仅包含 `pyz` + `a.scripts`，`exclude_binaries=True`
- COLLECT 收集 `exe + a.binaries + a.zipfiles + a.datas` 到独立文件夹
- 启动速度快，体积适中

**onefile**：
- EXE 包含 `a.binaries + a.zipfiles + a.datas`（全部打包进单个 exe）
- 启动时解压到临时目录，首次启动较慢
- 分发方便（单文件）

**debug**：
- `console=True` 保留控制台窗口，可看到 print/loguru 输出
- `debug=True` 启用 PyInstaller 调试符号
- `upx=False` 禁用压缩，保留堆栈信息
- `EXTRA_EXCLUDES = []`（初始为空）不排除任何包，便于排查缺失模块问题

---

## 3.5 与原计划的偏差

| 计划项 | 变更 | 原因 |
|:---|:---|:---|
| Vite HMR dev mode | 已在 Phase 1 实现 | Phase 1 的 `app.py` 已包含 `--with-vite` 支持 |
| Singleton lock | 已在 Phase 1 实现 | Phase 1 的 `singleton.py` 已实现跨平台单实例锁 |
| System dialogs | 已在 Phase 1 实现 | Phase 1 的 `dialog.py` 已实现系统对话框封装 |
| 3 套 spec 模板 | 已实现 onedir/onefile/debug | 按原计划执行 |

Phase 3 实际聚焦于原计划中的 **spec 模板** 和 **开发体验改进** 部分，Vite HMR、单实例锁、系统对话框三项在 Phase 1 已提前实现。

---

## Phase 3 验证结果

| 测试项 | 状态 |
|:---|:---|
| `uv run pywebvue --help` 显示 `create` 和 `build` 子命令 | 通过 |
| `uv run pywebvue build --help` 显示 `--mode`、`--spec`、`--skip-frontend` 选项 | 通过 |
| `uv run pywebvue create --help` 显示 `--force` 选项 | 通过 |
| `pywebvue create test_app` 生成 29 个文件（含 3 个 spec） | 通过 |
| spec 文件名正确替换为 `test_app.spec`、`test_app-onefile.spec`、`test_app-debug.spec` | 通过 |
| spec 文件内容中 `{{PROJECT_TITLE}}` 替换为 `Test App` | 通过 |
| 无 unsubstituted placeholder 警告 | 通过 |
| 二次创建同目录时报错并提示 `--force` | 通过 |
| `pyproject.toml` 包含 `[tool.uv.scripts]` 和 `[dependency-groups]` | 通过 |
| `.gitignore` 包含 `*.spec.bak` | 通过 |
| Toast.vue 中无冗余 `provide` | 通过 |
| LogPanel.vue 包含 Clear 按钮 | 通过 |
| ProgressBar.vue 始终渲染（含 Idle 空状态） | 通过 |
| `LogEntry` 和 `ToastOptions` 包含 `id` 字段 | 通过 |

---

## Phase 4 调整建议

基于 Phase 3 的实现经验，对后续开发提出以下建议：

### 4.1 PyInstaller 打包实战验证

当前 spec 模板已生成但未经过实际 PyInstaller 打包测试。Phase 4 应完成端到端打包验证：
- 在真实项目中执行 `pywebvue build` 并确认产物可运行
- 验证 `frontend/dist`、`assets/`、`config.yaml` 是否正确打包进 dist
- 验证 icon.ico 缺失时是否优雅降级

### 4.2 spec 模板去重

三套 spec 文件约 90% 重复代码（Analysis 块完全相同）。可考虑：
- 在 `build_project` 中根据 `--mode` 动态生成 spec 文件，而非使用静态模板
- 或提取共享 Analysis 块为公共模板片段

### 4.3 `build` 子命令增强

- 增加 `--icon` 参数，允许覆盖默认 icon 路径
- 增加 `--clean` 参数，打包前自动清理 `build/` 和 `dist/`
- 增加 `--output-dir` 参数，自定义输出目录

### 4.4 前端模板进一步改进

- **tailwind.config.ts.tpl**：`require('daisyui')` 改为 ESM `import daisyui from 'daisyui'`
- **App.vue.tpl**：`toastQueue.push()` 和 `toastQueue.splice()` 使用不可变模式
- **Toast.vue.tpl**：`watch` 监听 `props.items.length` 改为监听 `props.items`，以捕获同长度替换场景

### 4.5 uv scripts 跨平台

`build-frontend = "cd frontend && bun run build"` 在不同 shell 环境下行为可能不一致。可考虑改用 Python 调用：
```toml
build-frontend = "sh -c 'cd frontend && bun run build'"
```

---

## 当前项目架构

```
src/pywebvue/
  __init__.py          # 公开 API 导出
  app.py               # App 类 + ApiProxy（窗口生命周期、Vite 自动启动）
  api_base.py          # ApiBase 基类（业务方法基座）
  cli.py               # CLI 入口（pywebvue create / pywebvue build）
  config.py            # YAML 配置加载（AppConfig dataclass）
  constants.py         # 框架常量、版本号
  dialog.py            # 系统对话框封装
  event_bus.py         # Python->前端事件桥接（BRIDGE_JS）
  logger.py            # loguru 双通道日志（console + frontend）
  process.py           # 子进程管理（start/pause/resume/stop）
  result.py            # Result dataclass + ErrCode 错误码
  singleton.py         # 跨平台单实例锁
  templates/
    project/           # 脚手架模板（28 个 .tpl 文件）
      .gitignore.tpl
      main.py.tpl
      app.py.tpl
      config.yaml.tpl
      pyproject.toml.tpl
      {{PROJECT_NAME}}.spec.tpl          # Phase 3 新增
      {{PROJECT_NAME}}-onefile.spec.tpl  # Phase 3 新增
      {{PROJECT_NAME}}-debug.spec.tpl    # Phase 3 新增
      frontend/
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
