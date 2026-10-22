# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the SpliceGAIP **desktop / web** executable.

Double-clicking the built SpliceGAIP.exe starts a local FastAPI+uvicorn
server on a free port and opens the browser UI automatically.

Build (onedir):
    pyinstaller packaging/SpliceGAIP-Web.spec \
        --distpath packaging/dist-web --workpath packaging/build-web

Differences from SpliceGAIP.spec (the CLI build):
  * entry point is serve_ui.py, not run.py
  * fastapi / uvicorn / starlette / python-multipart are INCLUDED (they were
    excluded from the CLI bundle to save space)
  * everything else (matplotlib backends, autogen submodules, config/) is
    identical — the figure/report pipeline is the same code path.
"""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

import os

# SPECPATH is the spec file's directory; the project root is its parent.
HERE = SPECPATH
ROOT = os.path.dirname(HERE)

# --- data files ---------------------------------------------------------------
datas = [
    # YAML configuration read at runtime (config.py resolves it relative to
    # the frozen package root, i.e. <bundle>/config).
    (os.path.join(ROOT, "config"), "config"),
    # API configuration guide (users copy this to .env and fill in their key)
    (os.path.join(ROOT, "API_CONFIG.md"), "."),
    (os.path.join(ROOT, "splicegaip", "interface", "opencc-cn2t.js"), "splicegaip/interface"),
    (os.path.join(ROOT, "splicegaip", "interface", "OPENCC-JS-LICENSE.txt"), "splicegaip/interface"),
    (os.path.join(ROOT, "splicegaip", "interface", "OPENCC-DATA-LICENSE.txt"), "splicegaip/interface"),
    (os.path.join(ROOT, "splicegaip", "interface", "OPENCC-NOTICE.txt"), "splicegaip/interface"),
]
# matplotlib ships fonts/mpl-data; reportlab ships AFM/VFF font metrics.
datas += collect_data_files("matplotlib")
datas += collect_data_files("reportlab")

# --- hidden imports ------------------------------------------------------------
# autogen 0.7.5 resolves agent/team/tool modules dynamically.
hiddenimports = []
for package in (
    # the platform itself: several modules are imported lazily (inside
    # functions) so collecting everything keeps the frozen build complete
    "splicegaip",
    "autogen_agentchat",
    "autogen_agentchat.agents",
    "autogen_agentchat.teams",
    "autogen_core",
    "autogen_core.models",
    "autogen_ext",
    "autogen_ext.models",
    "autogen_ext.models.openai",
    "pymed",
    # Step 5: bioservices integration (optional, gracefully degrades)
    "bioservices",
    "bioservices.Ensembl",
    "bioservices.UniProt",
    "bioservices.KEGG",
    "bioservices.Reactome",
):
    hiddenimports += collect_submodules(package)

# Web stack. uvicorn picks its event loop / http protocol implementation at
# runtime via try/except imports inside uvicorn.loops.auto and
# uvicorn.protocols.http.auto, which the static analyser cannot follow.
for package in ("uvicorn", "fastapi", "starlette", "python_multipart"):
    hiddenimports += collect_submodules(package)

hiddenimports += [
    # matplotlib backends are imported lazily by savefig(); the SVG/PDF
    # backends are required because every figure is written as PNG **and**
    # SVG. Missing one used to abort the whole figure set after the first PNG.
    "matplotlib.backends.backend_agg",
    "matplotlib.backends.backend_svg",
    "matplotlib.backends.backend_pdf",
    "matplotlib.backends.backend_ps",
    "reportlab",
    "yaml",
    # uvicorn[standard] optional accelerators / CLI helpers.
    "httptools",
    "watchfiles",
    "websockets",
    "click",
    "dotenv",
    # multipart parsing for /api/upload (UploadFile).
    "multipart",
    "email",
    "mimetypes",
]

# --- excludes ------------------------------------------------------------------
# NOTE: fastapi/uvicorn MUST stay available here. Only the pieces that are
#       genuinely unused by the web path are dropped.
excludes = [
    "streamlit",
    "pytest",
    "pandas",
    "scipy",
    "seaborn",
    "plotly",
    "sqlalchemy",
    "tkinter",
    "PyQt5",
    "PySide2",
    "IPython",
    "notebook",
]

block_cipher = None

a = Analysis(
    [os.path.join(ROOT, "serve_ui.py")],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[os.path.join(HERE, "rthook_runtime.py")],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SpliceGAIP",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    # Keep the console: it prints the local URL and the user closes the
    # window to stop the server.
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(HERE, "icon.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="SpliceGAIP",
)

# Output to root dist/ directory for clean organization
import shutil
from pathlib import Path
dist_root = Path(HERE).parent / "dist"
dist_root.mkdir(exist_ok=True)
build_dir = Path(HERE) / "build-temp"
if build_dir.exists():
    shutil.rmtree(build_dir, ignore_errors=True)
