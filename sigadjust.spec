# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for SigAdjust V2 — onefile Windows executable."""

import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[str(Path(__file__).parent)],
    binaries=[],
    datas=[],
    hiddenimports=[
        # Core computation — explicit for PyInstaller auto-detect
        'pandas', 'statsmodels', 'plotly', 'pyfixest',
        'pyfixest.estimation', 'pyfixest.feols',
        'pyreadstat', 'openpyxl',
        # PySide6 QtWebEngine — needs explicit mention
        'PySide6.QtWebEngineWidgets',
        'PySide6.QtWebEngineCore',
        # App packages
        'core', 'core.models', 'ui', 'ui.widgets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 'test', 'distutils', 'setuptools',
        'unittest', 'email', 'http.server',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SigAdjust',
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
    icon=None,
)
