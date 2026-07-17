"""Configuration py2app : construction du bundle macOS ``.app``.

Usage (sur macOS) :

    python3 -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt py2app
    python setup.py py2app

Le bundle est généré dans ``dist/Gestion Commerciale.app``.
Le script ``scripts/build_mac.sh`` automatise tout (icône, .app, .dmg).
"""

from pathlib import Path

from setuptools import setup

APP = ["main.py"]
APP_NAME = "Gestion Commerciale"
ICON = Path("resources/AppIcon.icns")

OPTIONS = {
    "argv_emulation": False,
    "packages": ["PySide6", "sqlalchemy", "reportlab", "openpyxl", "matplotlib"],
    "excludes": ["tkinter", "pytest"],
    "plist": {
        "CFBundleName": APP_NAME,
        "CFBundleDisplayName": APP_NAME,
        "CFBundleIdentifier": "com.maisondevente.gestioncommerciale",
        "CFBundleShortVersionString": "1.0.0",
        "CFBundleVersion": "1",
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "11.0",
    },
}

# L'icône est incluse seulement si elle a été générée (scripts/make_icon.py).
if ICON.exists():
    OPTIONS["iconfile"] = str(ICON)

setup(
    name=APP_NAME,
    app=APP,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
