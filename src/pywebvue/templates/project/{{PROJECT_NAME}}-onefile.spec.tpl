# -*- mode: python ; coding: utf-8 -*-
"""PyWebVue onefile spec - outputs a single executable."""

import os

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# ---------------------------------------------------------------------------
# User customization sections -- edit freely, they are preserved across
# regenerations by the pywebvue CLI.
# ---------------------------------------------------------------------------
EXTRA_DATAS = []
EXTRA_BINARIES = []
EXTRA_HIDDEN_IMPORTS = []
EXTRA_EXCLUDES = []

# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------
project_dir = os.path.dirname(os.path.abspath(SPECPATH))

datas = (
    [
        (os.path.join(project_dir, "frontend", "dist"), "frontend/dist"),
        (os.path.join(project_dir, "assets"), "assets"),
        (os.path.join(project_dir, "config.yaml"), "."),
    ]
    + EXTRA_DATAS
)

hiddenimports = (
    [
        "pywebvue",
        "pywebview",
        "loguru",
        "yaml",
    ]
    + EXTRA_HIDDEN_IMPORTS
    + collect_submodules("pywebvue")
)

excludes = (
    [
        "matplotlib",
        "numpy",
        "pandas",
        "scipy",
        "tkinter",
        "unittest",
        "test",
    ]
    + EXTRA_EXCLUDES
)

a = Analysis(
    [os.path.join(project_dir, "main.py")],
    pathex=[project_dir],
    binaries=EXTRA_BINARIES,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="{{PROJECT_TITLE}}",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(project_dir, "assets", "icon.ico"),
)
