# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for dcs-client — one-file Windows executable.

Bundles the static web files (Leaflet map) and the YAML config template.
The TUI, web, and MCP sub-commands are loaded lazily inside click callbacks,
so their modules are declared as hidden imports.
"""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = []
datas += collect_data_files("uvicorn")
datas += collect_data_files("fastapi")
datas += collect_data_files("textual")  # CSS themes and bundled assets

# Static web client (Leaflet map HTML)
datas += [
    ("src/dcs_bridge/client/web/static", "dcs_bridge/client/web/static"),
    ("dcs-client.yaml.template", "."),
]

# Lazy sub-command imports — loaded inside typer callbacks at runtime
hidden_imports = [
    # TUI
    "dcs_bridge.client.tui.app",
    "textual",
    # Web
    "dcs_bridge.client.web.server",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.loops.asyncio",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.protocols.websockets.websockets_impl",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    # MCP
    "dcs_bridge.client.mcp.server",
    "mcp",
    "mcp.server.stdio",
]
hidden_imports += collect_submodules("dcs_bridge.client")
hidden_imports += collect_submodules("dcs_bridge.common")

a = Analysis(
    ["src/dcs_bridge/client/app.py"],
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
    name="dcs-client",
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
