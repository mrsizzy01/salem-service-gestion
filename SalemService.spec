# -*- mode: python ; coding: utf-8 -*-
# =====================================================================
# PyInstaller spec file – Salem Service (macOS .app bundle)
# =====================================================================
# Usage (sur Mac) :
#   pip install pyinstaller
#   pyinstaller SalemService.spec
# =====================================================================

import sys
from pathlib import Path

block_cipher = None

# Chemin du projet (auto-détecté par PyInstaller)
PROJECT_ROOT = Path(SPECPATH)

# ---- Collecte des données & ressources --------------------------------
datas = [
    # Dossier du paquet applicatif
    (str(PROJECT_ROOT / "app"), "app"),
]

# ---- Imports cachés requis par PySide6 / SQLAlchemy / ReportLab ------
hiddenimports = [
    # PySide6
    "PySide6",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.QtCharts",
    "PySide6.QtPrintSupport",
    # SQLAlchemy
    "sqlalchemy",
    "sqlalchemy.dialects.sqlite",
    "sqlalchemy.orm",
    "sqlalchemy.ext.declarative",
    # ReportLab
    "reportlab",
    "reportlab.pdfgen",
    "reportlab.lib.pagesizes",
    "reportlab.lib.styles",
    "reportlab.lib.units",
    "reportlab.platypus",
    # openpyxl
    "openpyxl",
    "openpyxl.styles",
    # matplotlib
    "matplotlib",
    "matplotlib.backends.backend_qt5agg",
    # stdlib
    "sqlite3",
    "logging",
    "json",
    "csv",
    "io",
    "hashlib",
    "uuid",
]

# ---- Analyse du point d'entrée ----------------------------------------
a = Analysis(
    ["main.py"],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "pytest", "_pytest"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ---- Exécutable -------------------------------------------------------
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SalemService",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # Pas de terminal (app GUI)
    disable_windowed_traceback=False,
    target_arch=None,       # arm64 ou x86_64 selon le Mac hôte
    codesign_identity=None,
    entitlements_file=None,
    icon=None,              # Remplacer par "assets/icon.icns" si dispo
)

# ---- Bundle macOS .app ------------------------------------------------
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="SalemService",
)

app = BUNDLE(
    coll,
    name="SalemService.app",
    icon=None,              # Remplacer par "assets/icon.icns" si dispo
    bundle_identifier="com.salemservice.gestion",
    info_plist={
        "CFBundleDisplayName": "Salem Service",
        "CFBundleName": "SalemService",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        "NSHighResolutionCapable": True,
        "NSRequiresAquaSystemAppearance": False,   # Support Dark Mode
        "LSMinimumSystemVersion": "11.0",          # macOS Big Sur +
        "CFBundleDocumentTypes": [],
        "NSHumanReadableCopyright": "© 2025 Salem Service. Tous droits réservés.",
    },
)
