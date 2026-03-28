# Phase 3 手动测试清单

> 基于 Phase 3 实现的 CLI 增强 + PyInstaller spec 模板 + 前端模板修复编写。
> 所有命令在项目根目录 `Q:\Git\GiteaManager\pywebvue-framework` 下执行。

---

## A. CLI 基础功能

### A1. 模块导入与帮助信息

```bash
uv run pywebvue --help
uv run pywebvue create --help
uv run pywebvue build --help
```

预期：
- `--help` 显示 `create` 和 `build` 两个子命令
- `create --help` 显示 `project_name`、`--title`、`--width`、`--height`、`--force` 五个参数
- `build --help` 显示 `--mode`（onedir/onefile/debug）、`--spec FILE`、`--skip-frontend` 三个选项

### A2. PEP 8 验证

```bash
uv run python -c "from pywebvue.cli import main, keyword; print('OK')"
```

预期：输出 `OK`，`import keyword` 在文件顶部（而非函数中间）。

---

## B. 脚手架生成

### B1. 完整参数生成

```bash
uv run pywebvue create my_app --title "My App" --width 800 --height 600
```

预期：
- 无报错，输出 `Project scaffolded successfully.`
- 生成 `my_app/` 目录，包含 29 个文件（Phase 2 的 26 个 + 3 个 spec）
- 无 "Unsubstituted placeholder" 警告
- Next steps 消息包含 `uv run python main.py` 和 `uv run pywebvue build`

### B2. 文件名变量替换验证

```bash
ls my_app/*.spec
```

预期输出三个文件：
```
my_app/my_app.spec
my_app/my_app-onefile.spec
my_app/my_app-debug.spec
```

**重点**：文件名中的 `{{PROJECT_NAME}}` 应被替换为 `my_app`，而非保留原始占位符。

### B3. Spec 文件内容验证

打开 `my_app/my_app.spec`，确认：
- `name="My App"`（非 `{{PROJECT_TITLE}}`）
- 包含 `datas` 中有 `frontend/dist`、`assets`、`config.yaml`
- `hiddenimports` 中有 `pywebvue`、`pywebview`、`loguru`、`yaml`
- `excludes` 中有 `matplotlib`、`numpy` 等排除项
- `console=False`、`upx=True`
- 底部有 `COLLECT` 块

打开 `my_app/my_app-onefile.spec`，确认：
- EXE 参数包含 `a.binaries`、`a.zipfiles`、`a.datas`（onedir 中 EXE 参数列表为空 `[]`）
- 无 `COLLECT` 块

打开 `my_app/my_app-debug.spec`，确认：
- `name="My App-debug"`（带 `-debug` 后缀）
- `console=True`、`debug=True`、`upx=False`
- `excludes=EXTRA_EXCLUDES`（初始为空列表，不排除任何包）
- 有 `COLLECT` 块

### B4. pyproject.toml 验证

打开 `my_app/pyproject.toml`，确认：

```toml
[dependency-groups]
dev = [
    "pyinstaller>=6.0",
]

[tool.uv.scripts]
dev = "python main.py --with-vite"
build-frontend = "cd frontend && bun run build"
build-app = "pyinstaller my_app.spec"
```

### B5. .gitignore 验证

打开 `my_app/.gitignore`，确认末尾包含：

```
# PyInstaller
*.spec.bak
```

### B6. 省略可选参数（自动推导）

```bash
uv run pywebvue create tool_box
```

预期：
- `--title` 自动推导为 `Tool Box`
- spec 文件名自动生成为 `tool_box.spec`、`tool_box-onefile.spec`、`tool_box-debug.spec`

---

## C. `--force` 标志

### C1. 二次创建（无 --force）

```bash
# my_app/ 已存在时再次执行
uv run pywebvue create my_app
```

预期：
- 报错 `Directory already exists: ...`
- 提示 `Use --force to overwrite (with confirmation)`
- 退出码非 0

### C2. 二次创建（带 --force，确认覆盖）

```bash
uv run pywebvue create my_app --force
# 在提示 "Overwrite my_app? [y/N]" 时输入 y
```

预期：
- 输出 `Removing existing directory: ...`
- 正常完成脚手架生成
- `my_app/` 中的所有文件均为全新内容

### C3. 二次创建（带 --force，取消覆盖）

```bash
uv run pywebvue create my_app --force
# 在提示 "Overwrite my_app? [y/N]" 时按回车（默认 N）或输入 n
```

预期：
- 输出 `Aborted.`
- `my_app/` 目录未被修改

---

## D. 模板碰撞检测

### D1. 正常项目名（无碰撞）

```bash
uv run pywebvue create normal_project 2>&1 | grep -i "unsubstituted"
```

预期：无匹配输出（无警告）。

### D2. 检查 Vue 插值未被误报

Vue 模板中的 `{{ version }}`、`{{ percentage }}`、`{{ entry.level }}` 等 camelCase 插值不应触发碰撞警告。正常创建项目时观察输出，确认无 false positive。

---

## E. 前端模板修复验证

### E1. Toast 组件 - 无冗余 provide

```bash
grep -n "provide" my_app/frontend/src/components/Toast.vue
```

预期：无匹配输出（`provide` 已从 Toast.vue 中完全移除）。

### E2. Toast 组件 - v-for 使用 id 作为 key

```bash
grep -n "v-for" my_app/frontend/src/components/Toast.vue
```

预期：输出包含 `:key="item.id"`（非 `:key="index"`）。

### E3. LogPanel 组件 - Clear 按钮

```bash
grep -n "clearLogs\|Clear" my_app/frontend/src/components/LogPanel.vue
```

预期：
- script 中有 `function clearLogs()` 定义
- template 中有 `<button ... @click="clearLogs">Clear</button>`

### E4. LogPanel 组件 - v-for 使用 id 作为 key

```bash
grep -n "v-for" my_app/frontend/src/components/LogPanel.vue
```

预期：输出包含 `:key="entry.id"`（非 `:key="idx"`）。

### E5. ProgressBar 组件 - 始终渲染

```bash
grep -n "v-if=" my_app/frontend/src/components/ProgressBar.vue
```

预期：
- 根 `<div>` 无 `v-if`（始终渲染）
- 百分比 badge 有 `v-if="progress"`
- 存在 `v-else` 的 "Idle" badge
- 存在 `v-else-if="!progress"` 的空状态文本

### E6. 类型定义 - id 字段

```bash
grep -n "id:" my_app/frontend/src/types/index.ts
```

预期：`LogEntry` 和 `ToastOptions` 接口中均包含 `id: number` 字段。

### E7. App.vue - toast ID 分配

```bash
grep -n "_toastId\|id: ++" my_app/frontend/src/App.vue
```

预期：存在 `let _toastId = 0;` 和 `id: ++_toastId` 逻辑。

---

## F. 前端构建

### F1. TypeScript 类型检查 + Vite 构建

```bash
cd my_app/frontend && bun run build
```

预期：
- `vue-tsc --noEmit` 类型检查通过，零错误
- `vite build` 成功输出 `../dist/index.html` 和 `../dist/assets/`

### F2. 开发服务器（可视化验证）

```bash
cd my_app/frontend && bun dev
```

打开 `http://localhost:5173/`，确认：
- ProgressBar 区域始终可见，显示 "Idle" badge 和 "No active progress" 文本，进度条为 indeterminate 状态
- LogPanel 区域有 Clear 按钮（auto-scroll 复选框右侧）

---

## G. `build` 子命令

### G1. build --help 验证

```bash
cd my_app && uv run pywebvue build --help
```

预期：显示 `--mode`、`--spec`、`--skip-frontend` 三个选项。

### G2. build --skip-frontend（跳过前端构建）

```bash
cd my_app && uv run pywebvue build --skip-frontend 2>&1 | head -5
```

预期：
- 输出 `Skipping frontend build (--skip-frontend)`
- 随后报错 PyInstaller 未安装（因未执行 `uv add --dev pyinstaller`）

### G3. build 缺失 PyInstaller 时的提示

```bash
cd my_app && uv run pywebvue build --skip-frontend 2>&1 | grep -i "pyinstaller"
```

预期：输出包含 `PyInstaller is not installed` 和安装提示 `uv add --dev pyinstaller`。

### G4. build 在非项目目录执行

```bash
cd /tmp && uv run pywebvue build 2>&1
```

预期：报错（无 `frontend/` 目录或无 `config.yaml`）。

---

## H. 端到端集成测试

### H1. pywebview + Vite 联调

```bash
# Terminal 1
cd my_app/frontend && bun dev

# Terminal 2
cd my_app && uv run python main.py
```

预期：
- pywebview 窗口弹出
- ProgressBar 显示 Idle 空状态
- LogPanel 中 Clear 按钮可见且可点击
- 拖拽文件后 Toast 正常弹出（inject 获取到真实 handler）

### H2. `--with-vite` 自动启动

```bash
cd my_app && uv run python main.py --with-vite
```

预期：
- Vite 自动启动，无需手动 `bun dev`
- 窗口关闭后 Vite 进程自动清理

---

## I. 输入校验（延续 Phase 2）

### I1. 无效项目名

```bash
uv run pywebvue create "123abc"
uv run pywebvue create "my-app"
uv run pywebvue create "class"
```

预期：全部报错退出。

---

## J. 已知限制与待改进项

| 项 | 现状 | 建议 |
|:---|:---|:---|
| PyInstaller spec 模板未实战打包验证 | 模板已生成但未经过真实 `pyinstaller` 打包 | Phase 4 端到端打包验证 |
| 三套 spec 约 90% 代码重复 | Analysis 块完全相同 | 改为动态生成或提取公共模板 |
| `build-frontend` uv script 跨平台 | `cd frontend && bun run build` 在不同 shell 环境下行为可能不一致 | 改为 `sh -c '...'` |
| `tailwind.config.ts.tpl` 使用 `require` | 不符合 ESM 标准 | 改为 `import daisyui from 'daisyui'` |
| `App.vue.tpl` 中 toastQueue 使用 `.push()` / `.splice()` | 违反不可变原则 | 改为 spread + filter 不可变模式 |
| Toast `watch` 仅监听 length | 同长度替换（dismiss + add）可能不触发 | 改为监听 `() => props.items` |
| `--spec` 参数未校验扩展名 | 用户可传入非 .spec 文件 | 增加 `.spec` 扩展名检查 |
| icon.ico 缺失时打包失败 | spec 模板硬编码 `assets/icon.ico` | 增加存在性检查或 graceful fallback |

---

## 清理

测试完毕后删除生成目录：

```bash
rm -rf my_app tool_box
```

> 注意：Windows 下可能因文件锁导致删除失败，关闭所有相关进程（pywebview、Vite dev server）后重试。
