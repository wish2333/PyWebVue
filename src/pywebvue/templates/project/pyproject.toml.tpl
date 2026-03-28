[project]
name = "{{PROJECT_NAME}}"
version = "0.1.0"
description = "{{PROJECT_TITLE}}"
requires-python = ">=3.10.8"
dependencies = [
    "pywebvue-framework>=0.1.0",
    "loguru>=0.7.3",
    "pywebview>=6.1",
    "pyyaml>=6.0.3",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[dependency-groups]
dev = [
    "pyinstaller>=6.0",
]

[tool.uv.scripts]
dev = "python main.py --with-vite"
build-frontend = "cd frontend && bun run build"
build-app = "pyinstaller {{PROJECT_NAME}}.spec"
