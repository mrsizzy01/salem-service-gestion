#!/usr/bin/env bash
# =====================================================================
#  build_mac.sh — Build Salem Service.app pour macOS
# =====================================================================
#  Pré-requis :
#    • macOS 11+ (Big Sur ou plus récent)
#    • Python 3.11 ou 3.12  (https://www.python.org/downloads/)
#    • Xcode Command Line Tools : xcode-select --install
#
#  Usage :
#    chmod +x build_mac.sh
#    ./build_mac.sh
#
#  Résultat :
#    dist/SalemService.app   → glisser dans /Applications
#    dist/SalemService.dmg   → fichier d'installation partageable
# =====================================================================

set -euo pipefail

PYTHON=python3
VENV_DIR=".venv_mac_build"
APP_NAME="SalemService"
DIST_DIR="dist"

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║     Build Salem Service — macOS .app bundle      ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# --- 1. Vérification Python -------------------------------------------
if ! command -v $PYTHON &>/dev/null; then
    echo "❌  Python 3 introuvable. Installe-le depuis https://www.python.org/"
    exit 1
fi
PY_VER=$($PYTHON -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "✅  Python $PY_VER détecté"

# --- 2. Environnement virtuel ----------------------------------------
if [ ! -d "$VENV_DIR" ]; then
    echo "📦  Création de l'environnement virtuel …"
    $PYTHON -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
echo "✅  Environnement virtuel activé"

# --- 3. Installation des dépendances ---------------------------------
echo "📥  Installation des dépendances …"
pip install --upgrade pip --quiet
pip install \
    "PySide6>=6.6.0" \
    "SQLAlchemy>=2.0.0" \
    "reportlab>=4.0.0" \
    "openpyxl>=3.1.0" \
    "matplotlib>=3.8.0" \
    "pyinstaller>=6.0.0" \
    --quiet
echo "✅  Dépendances installées"

# --- 4. Nettoyage du build précédent ---------------------------------
echo "🧹  Nettoyage des builds précédents …"
rm -rf build "$DIST_DIR/$APP_NAME" "$DIST_DIR/${APP_NAME}.app"

# --- 5. Build PyInstaller --------------------------------------------
echo "🔨  Compilation du bundle .app …"
pyinstaller SalemService.spec --noconfirm
echo "✅  Bundle créé : dist/${APP_NAME}.app"

# --- 6. Création du DMG (optionnel — nécessite hdiutil) -------------
DMG_PATH="$DIST_DIR/${APP_NAME}.dmg"
if command -v hdiutil &>/dev/null; then
    echo "💽  Création du fichier .dmg …"
    rm -f "$DMG_PATH"
    hdiutil create \
        -volname "Salem Service" \
        -srcfolder "$DIST_DIR/${APP_NAME}.app" \
        -ov -format UDZO \
        "$DMG_PATH"
    echo "✅  Fichier DMG créé : $DMG_PATH"
else
    echo "⚠️  hdiutil introuvable — DMG non créé (étape ignorée)"
fi

# --- 7. Résumé --------------------------------------------------------
echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║                Build terminé ! ✅                ║"
echo "╠══════════════════════════════════════════════════╣"
if [ -f "$DMG_PATH" ]; then
echo "║  📦  $DMG_PATH"
fi
echo "║  📂  dist/${APP_NAME}.app"
echo "╠══════════════════════════════════════════════════╣"
echo "║  Pour installer : glisse .app dans /Applications ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
