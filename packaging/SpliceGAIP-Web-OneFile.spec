# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller **onefile** spec for the SpliceGAIP desktop/web launcher.

Produces a single self-contained SpliceGAIP.exe that can be dropped straight
onto the Desktop: double-click -> local server starts -> browser opens.

Trade-off vs. SpliceGAIP-Web.spec (onedir):
  * onefile = one file, but every launch unpacks ~110 MB into %TEMP%
    (a few extra seconds before the browser opens)
  * onedir  = starts faster, but ships as a folder (exe + _internal)

Build:
    pyinstaller packaging/SpliceGAIP-Web-OneFile.spec \
        --distpath packaging/dist-web-onefile --workpath packaging/build-web-onefile
"""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

import os

HERE = SPECPATH
ROOT = os.path.dirname(HERE)

datas = [
    (os.path.join(ROOT, "config"), "config"),
    # shipped so the launcher can drop a fill-in template next to the exe
    (os.path.join(ROOT, ".env.example"), "."),
]
datas += collect_data_files("matplotlib")
datas += collect_data_files("reportlab")

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
    "uvicorn",
    "fastapi",
    "starlette",
    "python_multipart",
):
    hiddenimports += collect_submodules(package)

hiddenimports += [
    "matplotlib.backends.backend_agg",
    "matplotlib.backends.backend_svg",
    "matplotlib.backends.backend_pdf",
    "matplotlib.backends.backend_ps",
    "reportlab",
    "yaml",
    "httptools",
    "watchfiles",
    "websockets",
    "click",
    "dotenv",
    "multipart",
    "email",
    "mimetypes",
]

# Explicitly add report submodules since collect_submodules may miss them
hiddenimports += [
    "splicegaip.report",
    "splicegaip.report.generator",
]

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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="SpliceGAIP",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
