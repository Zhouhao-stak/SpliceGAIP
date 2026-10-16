# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the SpliceGAIP CLI executable.

Build (onedir):
    pyinstaller packaging/SpliceGAIP.spec \
        --distpath packaging/dist --workpath packaging/build

What goes in:
  * the splicegaip package (flat layout — there is NO src/ directory; the
    package sits at the project root and pathex picks it up)
  * config/*.yaml — runtime data files read by splicegaip.config

Deliberately excluded (not used by the CLI analysis path, saves hundreds
of MB): streamlit, fastapi, uvicorn, pandas, scipy, seaborn, plotly,
sqlalchemy, pytest, tkinter, IPython.
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
]
# matplotlib ships fonts/mpl-data; reportlab ships AFM/VFF font metrics.
datas += collect_data_files("matplotlib")
datas += collect_data_files("reportlab")

# --- hidden imports ------------------------------------------------------------
# autogen 0.7.5 resolves agent/team/tool modules dynamically.
hiddenimports = []
for package in (
    "autogen_agentchat",
    "autogen_agentchat.agents",
    "autogen_agentchat.teams",
    "autogen_core",
    "autogen_core.models",
    "autogen_ext",
    "autogen_ext.models",
    "autogen_ext.models.openai",
    "pymed",
):
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
]

# --- excludes ------------------------------------------------------------------
excludes = [
    "streamlit",
    "fastapi",
    "uvicorn",
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
    [os.path.join(ROOT, "run.py")],
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
