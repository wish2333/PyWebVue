# Process Tool - PyWebVue 示例

子进程管理工具，演示 PyWebVue 框架的 `ProcessManager` 能力，包括进程启动、暂停/恢复、终止、超时控制和实时输出流。

## 功能概览

| 功能 | 说明 |
|------|------|
| 命令执行 | 输入任意系统命令并执行，实时查看输出 |
| 预设命令 | 内置 6 个常用系统诊断命令，一键填充 |
| 进程控制 | 支持 Start / Pause / Resume / Stop / Reset 完整生命周期 |
| 超时控制 | 可设置超时时间，超时自动终止进程 |
| 实时统计 | 进程运行时间、输出行数、PID 等实时显示 |
| 系统信息 | 展示系统诊断信息（OS、CPU、内存等） |
| 实时日志 | 后端日志和进程输出实时推送到前端 |

## 快速开始

### 前置条件

- Python >= 3.10
- [uv](https://docs.astral.sh/uv/) 包管理器
- Node.js >= 18（前端开发需要）
- 推荐使用 [bun](https://bun.sh/) 作为前端包管理器

### 从框架仓库运行

此示例位于 PyWebVue 框架仓库的 `examples/process-tool` 目录下，使用 workspace 依赖。

```bash
# 在框架根目录下
cd examples/process-tool

# 安装 Python 依赖
uv sync

# 可选：安装 psutil 以获取 CPU 和内存详细信息
uv add psutil

# 安装前端依赖
cd frontend
bun install

# 启动前端开发服务器
bun dev
```

然后在另一个终端启动后端：

```bash
cd examples/process-tool
uv run main.py
```

### 独立部署

如果将示例复制到独立目录使用，需要修改 `pyproject.toml` 中的依赖：

```toml
[tool.uv.sources]
# 删除 workspace 依赖，改用 PyPI
# pywebvue-framework = { workspace = true }
```

并在 `[project.dependencies]` 中指定框架版本：

```toml
dependencies = [
    "pywebvue-framework>=0.1.0",
]
```

## 使用指南

### 使用预设命令

应用启动后自动加载 6 个预设命令按钮：

| 预设 | 说明 | 推荐用途 |
|------|------|----------|
| System Info | 显示操作系统、架构、Python 版本 | 验证 API 调用 |
| Count to 20 | 每行输出一个数字，带延迟 | 测试暂停/恢复功能 |
| Disk Usage | 显示磁盘使用情况 | 系统诊断 |
| Process List | 列出运行中的进程 | 系统监控 |
| Network Interfaces | 显示网络适配器信息 | 网络诊断 |
| Environment Variables | 打印所有环境变量 | 调试环境配置 |

点击预设按钮会自动填充命令和推荐的超时时间，然后点击 Start 执行。

### 测试暂停/恢复

推荐使用 "Count to 20" 预设来测试进程控制功能：

1. 选择 "Count to 20" 预设，点击 Start
2. 观察日志面板中逐行输出的数字
3. 点击 Pause，观察输出停止（Windows 下使用 NtSuspendProcess，Unix 下使用 SIGSTOP）
4. 点击 Resume，观察输出继续
5. 进程自然结束后，状态自动变为 Done

### 自定义命令

在命令输入框中输入任意命令：

- **Windows**: `ping localhost -n 10`, `dir /s /b C:\`, `tasklist`
- **Linux/macOS**: `ping -c 10 localhost`, `find / -name "*.log"`, `ps aux`

可在 Timeout 字段设置超时时间（秒），留空则使用 `config.yaml` 中的默认值。

### 查看系统信息

点击导航栏右侧的 "System Info" 按钮，展开系统信息面板：

- 基本信息：主机名、操作系统、架构、Python 版本、CPU 核数
- 如果安装了 `psutil`：CPU 使用率、内存使用量和使用百分比

### 实时统计

导航栏实时显示以下信息：

- **状态**: Idle / Running / Paused / Done（带颜色标签）
- **PID**: 进程 ID
- **输出行数**: 进程已输出的行数
- **运行时间**: 进程从启动到当前的耗时（仅 Running/Paused 状态显示）
- **超时倒计时**: 剩余超时时间（设置了超时时显示）

## 项目结构

```
process-tool/
├── main.py                          # 应用入口
├── app.py                           # 核心 API 逻辑
├── config.yaml                      # 应用配置
├── pyproject.toml                   # Python 项目配置
├── .gitignore
└── frontend/
    ├── package.json                 # 前端依赖
    ├── vite.config.ts               # Vite 构建配置
    ├── tsconfig.json                # TypeScript 配置
    ├── tailwind.config.ts           # Tailwind CSS 配置
    ├── postcss.config.js
    ├── index.html
    └── src/
        ├── main.ts                  # Vue 应用入口
        ├── assets/style.css         # 全局样式（Tailwind + DaisyUI）
        ├── api.ts                   # pywebview API 调用封装
        ├── event-bus.ts             # 事件总线 composable
        ├── types/index.ts           # TypeScript 类型定义
        ├── App.vue                  # 根组件
        └── components/
            ├── StatusBadge.vue      # 进程状态标签
            ├── LogPanel.vue         # 实时日志面板
            └── Toast.vue            # Toast 通知组件
```

## 架构说明

### Python 后端 (`app.py`)

`ProcessToolApi` 继承自 `ApiBase`，内部持有一个 `ProcessManager` 实例用于管理子进程。

#### 公开 API 方法

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `health_check()` | - | `Result` | 后端健康检查 |
| `get_presets()` | - | `Result<{presets}>` | 获取预设命令列表 |
| `get_system_info()` | - | `Result<SystemInfo>` | 获取系统诊断信息 |
| `get_status()` | - | `Result<ProcessStatus>` | 获取进程状态和统计 |
| `start_task(cmd, timeout)` | `str, int?` | `Result` | 启动子进程 |
| `pause_task()` | - | `Result` | 暂停子进程 |
| `resume_task()` | - | `Result` | 恢复子进程 |
| `stop_task()` | - | `Result` | 终止子进程 |
| `reset_task()` | - | `Result` | 重置为 IDLE 状态 |

#### 事件推送

| 事件名 | 数据 | 触发时机 |
|--------|------|----------|
| `process:state_changed` | `{state, pid?}` | 进程状态变化时（running/paused/stopped/idle） |
| `process:worker:output` | `{line}` | 进程每输出一行（由 ProcessManager 内部发出） |
| `process:worker:complete` | `{returncode}` | 进程自然退出 |
| `process:worker:timeout` | `{timeout}` | 进程超时自动终止 |
| `log:add` | `{level, message, ...}` | 后端日志记录 |

### ProcessManager 工作原理

`ProcessManager` 是框架提供的子进程管理器，核心特性：

- **状态机**: IDLE -> RUNNING -> PAUSED -> STOPPED，线程安全
- **实时输出**: 后台线程逐行读取 stdout/stderr，通过 `on_output` 回调处理
- **暂停/恢复**: Windows 下使用 NtSuspendProcess/NtResumeProcess API；Unix 下使用 SIGSTOP/SIGCONT 信号
- **超时控制**: 后台定时线程，超时自动调用 stop()
- **自动终止**: 优先 terminate()，5 秒后仍未退出则 kill()

```python
# ProcessManager 使用模式
pm = ProcessManager(api_instance, name="worker")
pm.start(
    cmd=["python", "task.py"],
    on_output=lambda line: logger.info(line),  # 每行输出回调
    on_complete=lambda rc: logger.info(rc),    # 进程退出回调
    timeout=30,                                 # 超时秒数
)
pm.pause()    # 暂停
pm.resume()   # 恢复
pm.stop()     # 终止
```

### Vue 前端

#### 通信流程

```
用户点击 Start
  -> call("start_task", cmd, timeout)
    -> ProcessManager.start() 启动子进程
      -> emit("process:state_changed", {state: "running"})
        -> 前端更新 UI 状态为 Running
      -> 后台线程读取 stdout
        -> on_output(line) -> logger.info()
          -> 框架转发 log:add 事件
            -> LogPanel.vue 实时显示
      -> 进程退出
        -> on_complete(rc) -> emit("process:state_changed", {state: "stopped"})
          -> 前端更新 UI 状态为 Done
        -> emit("process:worker:complete", {returncode})
          -> 前端显示 Toast 通知
```

#### 按钮状态逻辑

通过 Vue computed 属性控制按钮的启用/禁用状态，确保操作合法：

| 状态 | Start | Pause | Resume | Stop | Reset |
|------|-------|-------|--------|------|-------|
| Idle | Y | N | N | N | N |
| Running | N | Y | N | Y | N |
| Paused | N | N | Y | Y | N |
| Done | Y | N | N | N | Y |

#### 组件职责

- **StatusBadge.vue**: 进程状态标签，5 种状态对应不同颜色。
- **LogPanel.vue**: 订阅 `log:add` 事件实时显示日志，支持级别筛选（ALL/DEBUG/INFO/WARNING/ERROR/CRITICAL）、自动滚动和清空。
- **Toast.vue**: 全局通知组件，用于操作反馈（启动成功、完成、超时、错误）。

## 预设命令详情

### System Info

```python
# 跨平台命令，使用当前 Python 解释器
python -c "import platform; print(f'OS: {platform.system()} {platform.release()}'); ..."
```

输出示例：
```
OS: Windows 11
Arch: AMD64
Python: 3.12.8
CPU count: 16
```

### Count to 20

```python
# 带延迟的循环输出，适合测试暂停/恢复
python -c "for i in range(1, 21): print(f'line {i}'); time.sleep(0.3)"
```

推荐测试流程：启动 -> 等待几行输出 -> 暂停 -> 观察输出停止 -> 恢复 -> 观察输出继续 -> 等待完成。

### 磁盘 / 进程 / 网络 命令

这些命令根据操作系统自动选择：
- **Windows**: `wmic logicaldisk ...`, `tasklist ...`, `ipconfig`
- **Linux/macOS**: `df -h`, `ps aux | head`, `ifconfig` 或 `ip addr`

## 演示的框架能力

1. **ProcessManager** - 子进程全生命周期管理（启动/暂停/恢复/终止）
2. **实时输出流** - 后台线程逐行读取 stdout/stderr 并推送到前端
3. **跨平台进程控制** - Windows NtSuspendProcess API + Unix SIGSTOP/SIGCONT
4. **超时管理** - 自动超时检测和进程终止
5. **事件驱动** - 多种事件（state_changed, complete, timeout, output）协同更新 UI
6. **线程安全状态机** - ProcessState 枚举 + threading.Lock 保证状态一致性
7. **后台线程** - 使用 `run_in_thread()` 和 ProcessManager 内部线程
8. **原生对话框** - 通过 `self.dialog` 访问系统文件对话框（本示例中用于文件拖放日志）

## 配置说明 (`config.yaml`)

```yaml
app:
  name: "process_tool"
  title: "Process Tool"
  width: 900           # 窗口宽度
  height: 700          # 窗口高度
  min_size: [600, 400] # 最小尺寸
  theme: light         # 主题（dark/light）

  dev:
    enabled: true       # 开发模式，连接 Vite 开发服务器
    vite_port: 5173     # Vite 端口

logging:
  level: INFO           # 日志级别
  to_frontend: true     # 日志推送到前端

process:
  default_timeout: 30   # 进程默认超时（秒）
                        # start_task 未指定 timeout 时使用此值
```

## 可选增强

安装 `psutil` 可以在 System Info 面板中显示更丰富的信息：

```bash
uv add psutil
```

安装后的额外信息：
- CPU 使用率（实时采样 0.5 秒）
- 物理内存总量和使用率
