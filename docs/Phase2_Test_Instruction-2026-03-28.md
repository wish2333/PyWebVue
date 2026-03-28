# Phase 2 手动测试清单

> 基于已实现的 CLI + 前端模板代码编写。
> 所有命令在项目根目录 `Q:\Git\GiteaManager\pywebvue-framework` 下执行。

---

## A. CLI 基础功能

### A1. 模块导入

```bash
uv run python -c "from pywebvue.cli import main; print('OK')"
```

预期：输出 `OK`，无报错。

### A2. CLI 帮助信息

```bash
uv run pywebvue --help
uv run pywebvue create --help
```

预期：
- `--help` 显示 `create` 子命令
- `create --help` 显示 `project_name`、`--title`、`--width`、`--height` 四个参数

---

## B. 脚手架生成

### B1. 完整参数生成

```bash
uv run pywebvue create my_app --title "My App" --width 800 --height 600
```

预期：
- 无报错，输出 `Project scaffolded successfully.`
- 自动运行 `bun install` 且成功
- 生成 `my_app/` 目录

### B2. 变量替换验证

打开 `my_app/` 下的文件，确认 5 个模板变量全部正确替换：

| 文件 | 检查项 |
|:---|:---|
| `config.yaml` | `name: "my_app"`, `title: "My App"`, `width: 800`, `height: 600` |
| `app.py` | 类名为 `MyAppApi`，docstring 中为 `My App` |
| `pyproject.toml` | `name = "my_app"`, `description = "My App"` |
| `frontend/index.html` | `<title>My App</title>` |
| `frontend/src/App.vue` | `<span class="text-lg font-bold">My App</span>` |

### B3. 目录结构完整性

```bash
ls -R my_app/
```

确认以下 26 个文件全部存在（不含 `node_modules/`、`bun.lockb`）：

```
my_app/
  .gitignore
  app.py
  config.yaml
  main.py
  pyproject.toml
  frontend/
    index.html
    package.json
    postcss.config.js
    tailwind.config.ts
    tsconfig.json
    tsconfig.node.json
    vite.config.ts
    src/
      api.ts
      App.vue
      env.d.ts
      event-bus.ts
      main.ts
      assets/style.css
      types/index.ts
      components/
        DataTable.vue
        FileDrop.vue
        LogPanel.vue
        ProgressBar.vue
        StatusBadge.vue
        Toast.vue
```

### B4. 省略可选参数（自动推导）

```bash
uv run pywebvue create tool_box
```

预期：
- `--title` 自动推导为 `Tool Box`（snake_case 转 Title Case）
- `--width` / `--height` 使用默认值 900x650
- `app.py` 中类名推导为 `ToolBoxApi`

---

## C. 输入校验

### C1. 重复目录检测

```bash
# my_app/ 已存在时再次执行
uv run pywebvue create my_app
```

预期：报错 `Directory already exists`，退出码非 0。

### C2. 无效项目名检测

```bash
uv run pywebvue create "123abc"
uv run pywebvue create "my-app"
uv run pywebvue create "class"
```

预期：全部报错并退出（`123abc` 非合法标识符；`my-app` 含连字符；`class` 为 Python 关键字）。

---

## D. 前端构建

### D1. TypeScript 类型检查 + Vite 构建

```bash
cd my_app/frontend && bun run build
```

预期：
- `vue-tsc --noEmit` 类型检查通过，零错误
- `vite build` 成功输出：
  - `../dist/index.html`
  - `../dist/assets/index-*.css`
  - `../dist/assets/index-*.js`

### D2. 构建产物验证

```bash
ls ../dist/
```

预期：包含 `index.html` 和 `assets/` 目录。

---

## E. 前端开发服务器

### E1. Vite Dev Server 启动

```bash
cd my_app/frontend && bun dev
```

预期：
- 终端显示 `Local: http://localhost:5173/`
- 浏览器打开后能看到完整页面：
  - 导航栏显示 "My App" + 版本徽章 + 连接状态徽章
  - Actions 卡片中包含 "Health Check" 按钮
  - File Drop 卡片（拖拽区域 + Browse 按钮）
  - Log Panel 卡片（级别过滤器 + 自动滚动开关）
- 控制台无红色报错（`Backend not available` 是正常的，因为脱离 pywebview 环境）

### E2. Vue 模板插值未被误替换

在浏览器中检查页面源码，确认：
- 导航栏显示 `My App`（模板变量已替换）
- 版本徽章旁显示 `v0.1.0`（Vue `{{ version }}` 插值正常工作）
- 页面不出现 `{{ percentage }}` 等原始模板语法

---

## F. 端到端集成测试

### F1. pywebview + Vite 联调

```bash
# Terminal 1
cd my_app/frontend && bun dev

# Terminal 2
cd my_app && uv run python main.py
```

预期：
- Terminal 1: Vite Dev Server 正常运行
- Terminal 2: 日志显示 `Dev mode: connecting to Vite at http://localhost:5173`
- pywebview 窗口弹出，加载 Vite 页面
- 导航栏状态徽章变为绿色 "Connected"
- 点击 "Health Check" 按钮，Footer 显示 `OK - status: running`
- 拖拽文件到窗口，Log Panel 中出现 `Files dropped:` 日志

### F2. `--with-vite` 自动启动模式

```bash
cd my_app && uv run python main.py --with-vite
```

预期：
- 日志显示 `Vite Dev Server starting (PID xxx)`
- 等待 Vite 就绪后自动连接，无需手动 `bun dev`
- 关闭窗口后 Vite 进程自动退出

---

## G. 已知限制与待改进项

| 项 | 现状 | 建议 |
|:---|:---|:---|
| `cli.py` 中 `import keyword` 位于函数定义之后 | 功能正常但不符合 PEP 8 规范 | 移至文件顶部导入区 |
| `cli.py` 中 `_substitute` 使用简单 `str.replace` | 对当前 5 个变量足够安全，但无防护机制 | 如需更复杂模板可引入 Jinja2 |
| `tailwind.config.ts.tpl` 使用 `require('daisyui')` | 当前 `bun run build` 通过，但 `require` 在 ESM 中不标准 | 改为 `import daisyui from 'daisyui'` |
| Toast 组件的 `provide` 在子组件中重复声明 | `App.vue` 的 `provide` 优先级更高，不影响功能 | 移除 `Toast.vue.tpl` 中的冗余 `provide` |
| `bun install` 失败不会中断脚手架流程 | 只打印 warning，用户体验可能困惑 | 考虑增加重试或更明确的错误提示 |

---

## 清理

测试完毕后删除生成目录：

```bash
rm -rf my_app tool_box
```

> 注意：Windows 下可能因文件锁导致删除失败，关闭所有相关进程后重试。
