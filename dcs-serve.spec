# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for dcs-serve — one-file Windows executable.

Bundles the Lua bridge script and the YAML config template as data files so
users can copy them alongside the .exe.
"""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Collect uvicorn and fastapi dynamic data (e.g. routing templates)
datas = []
datas += collect_data_files("uvicorn")
datas += collect_data_files("fastapi")

# Bundle distributable data files next to the executable
datas += [
    ("src/lua/dcs-bridge.lua", "."),
    ("dcs-serve.yaml.template", "."),
]

# uvicorn loads its implementation classes by string at runtime
hidden_imports = [
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.loops.asyncio",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.http.httptools_impl",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.protocols.websockets.websockets_impl",
    "uvicorn.protocols.websockets.wsproto_impl",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
]
hidden_imports += collect_submodules("dcs_bridge.serve")
hidden_imports += collect_submodules("dcs_bridge.common")

a = Analysis(
    ["src/dcs_bridge/serve/app.py"],
    pathex=["src"],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="dcs-serve",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
