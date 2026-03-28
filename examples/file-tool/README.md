# File Tool - PyWebVue 示例

文件元数据查看与哈希计算工具，演示 PyWebVue 框架的文件拖放、原生对话框、后台线程处理和事件推送能力。

## 功能概览

| 功能 | 说明 |
|------|------|
| 拖放文件 | 将文件拖放到窗口上，自动读取元数据 |
| 浏览文件 | 通过原生文件选择对话框选择文件（支持多选） |
| 文件元数据 | 显示文件名、大小、扩展名、修改时间、类型分类 |
| 哈希计算 | 计算 MD5 和 SHA-256，带进度条反馈 |
| 多文件管理 | 支持同时查看多个文件，切换标签页 |
| 实时日志 | 后端日志实时推送到前端 Log 面板 |

## 快速开始

### 前置条件

- Python >= 3.10
- [uv](https://docs.astral.sh/uv/) 包管理器
- Node.js >= 18（前端开发需要）
- 推荐使用 [bun](https://bun.sh/) 作为前端包管理器

### 从框架仓库运行

此示例位于 PyWebVue 框架仓库的 `examples/file-tool` 目录下，使用 workspace 依赖。

```bash
# 在框架根目录下
cd examples/file-tool

# 安装 Python 依赖
uv sync

# 安装前端依赖
cd frontend
bun install

# 启动前端开发服务器
bun dev
```

然后在另一个终端启动后端：

```bash
cd examples/file-tool
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

### 拖放文件

1. 将任意文件从系统文件管理器拖放到应用窗口上
2. 框架自动触发 `on_file_drop` 回调，后端读取文件元数据
3. 前端收到 `file:dropped` 事件后调用 `get_file_info` API 获取详情
4. 文件信息显示在 FileInfoCard 组件中

### 浏览文件

点击 "Browse Files..." 按钮，调用 `self.dialog.open_file(multiple=True)` 打开系统原生文件选择对话框，支持同时选择多个文件。

### 哈希计算

1. 选中一个文件后，点击 "Calculate MD5 & SHA-256" 按钮
2. 后端在独立线程中分块读取文件（64KB/块），实时计算哈希值
3. 每处理约 5% 文件内容时，通过 `progress:update` 事件推送进度
4. 计算完成后，`hash:complete` 事件携带 MD5 和 SHA-256 结果推送到前端
5. 结果以等宽字体显示，支持点击选中复制

### 文件列表管理

- 拖放或浏览多个文件后，文件标签页横向排列在顶部
- 点击标签切换查看不同文件的元数据和哈希结果
- 点击标签右侧的 "x" 按钮从列表中移除文件
- 系统自动去重，重复路径不会重复添加

## 项目结构

```
file-tool/
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
            ├── FileDrop.vue         # 拖放区域（视觉反馈）
            ├── FileInfoCard.vue     # 文件元数据展示卡片
            ├── ProgressBar.vue      # 进度条组件
            ├── LogPanel.vue         # 实时日志面板
            └── Toast.vue            # Toast 通知组件
```

## 架构说明

### Python 后端 (`app.py`)

`FileToolApi` 继承自 `ApiBase`，定义以下公开方法（自动暴露给前端）：

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `health_check()` | - | `Result` | 后端健康检查 |
| `browse_files()` | - | `Result` | 打开文件选择对话框 |
| `get_file_info(path)` | `str` | `Result<FileInfo>` | 读取文件元数据 |
| `compute_hash(path)` | `str` | `Result` | 启动哈希计算（后台线程） |

`on_file_drop(file_paths)` 是框架生命周期回调，在文件被拖放到窗口时自动调用。

#### 事件推送

| 事件名 | 数据 | 触发时机 |
|--------|------|----------|
| `file:dropped` | `{path: str}` | 文件被拖放或浏览选择后 |
| `progress:update` | `{current, total, label}` | 哈希计算进度更新 |
| `hash:complete` | `{path, name, md5, sha256, size}` | 哈希计算完成 |
| `hash:error` | `{path, message}` | 哈希计算出错 |

### Vue 前端

#### 通信流程

```
用户拖放文件
  -> pywebview 触发 on_file_drop(file_paths)
    -> 后端 emit("file:dropped", {path})
      -> 前端 useEvent("file:dropped") 接收
        -> call("get_file_info", path)
          -> 后端返回 Result<FileInfo>
            -> 前端渲染 FileInfoCard
```

#### 组件职责

- **FileDrop.vue**: 纯视觉组件，提供拖放区域的悬停效果。实际文件路径由 pywebview 在原生窗口层面捕获。
- **FileInfoCard.vue**: 展示文件元数据表格，包括文件名、扩展名、类型分类（带颜色标签）、大小、修改时间、文件类型（文本/二进制）。
- **ProgressBar.vue**: 根据 `ProgressPayload` 数据渲染 DaisyUI 进度条，颜色随百分比变化。
- **LogPanel.vue**: 订阅 `log:add` 事件，实时展示后端日志，支持按级别筛选和自动滚动。
- **Toast.vue**: 全局通知组件，通过 provide/inject 模式共享 `showToast` 方法。

#### 文件分类系统

后端根据文件扩展名将文件分为 7 个类别，前端以不同颜色的 Badge 展示：

| 分类 | 颜色 | 包含扩展名示例 |
|------|------|----------------|
| Code | 蓝色 (info) | .py, .js, .ts, .java, .go, .rs |
| Data | 绿色 (success) | .json, .xml, .yaml, .csv |
| Document | 主色 (primary) | .pdf, .doc, .md, .txt |
| Image | 黄色 (warning) | .png, .jpg, .svg, .webp |
| Archive | 红色 (error) | .zip, .tar, .gz, .7z |
| Executable | 红色 (error) | .exe, .bat, .sh, .dll |
| Media | 灰色 (secondary) | .mp3, .mp4, .wav |

## 演示的框架能力

1. **ApiBase 基类** - 继承 `ApiBase` 定义业务 API，公开方法自动暴露给前端
2. **Result 标准响应** - 使用 `Result.ok()` / `Result.fail()` 统一响应格式
3. **ErrCode 错误码** - 使用框架内置错误码（FILE_NOT_FOUND, FILE_READ_ERROR 等）
4. **事件推送** - 通过 `emit()` 向前端推送实时事件
5. **后台线程** - 使用 `run_in_thread()` 在后台线程执行哈希计算
6. **原生对话框** - 通过 `self.dialog.open_file()` 调用系统文件选择对话框
7. **文件拖放** - 通过覆写 `on_file_drop()` 处理拖放事件
8. **日志转发** - 后端 loguru 日志自动推送到前端 Log 面板

## 配置说明 (`config.yaml`)

```yaml
app:
  name: "file_tool"
  title: "File Tool"
  width: 900           # 窗口宽度
  height: 700          # 窗口高度
  min_size: [600, 400] # 最小尺寸
  theme: dark          # 主题（dark/light）

  dev:
    enabled: true       # 开发模式，连接 Vite 开发服务器
    vite_port: 5173     # Vite 端口

logging:
  level: INFO           # 日志级别
  to_frontend: true     # 日志推送到前端
```
