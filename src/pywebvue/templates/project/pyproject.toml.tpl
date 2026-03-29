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

[tool.hatch.build.targets.wheel]
packages = ["."]

# [tool.uv.sources]
# For local development without publishing to PyPI, reference the framework
# from a local path (adjust the path to point to your pywebvue-framework repo):
# pywebvue-framework = { path = "../pywebvue-framework" }

[dependency-groups]
dev = [
    "pyinstaller>=6.0",
]
