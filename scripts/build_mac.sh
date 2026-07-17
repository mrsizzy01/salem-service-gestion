#!/bin/bash
# =====================================================================
# Construction complète de l'application macOS : .app + .dmg
#
# Prérequis : macOS 11+, Python 3.11+ (python.org ou Homebrew).
#
#   chmod +x scripts/build_mac.sh
#   ./scripts/build_mac.sh
#
# Résultat : dist/GestionCommerciale-1.0.0.dmg
# =====================================================================
set -euo pipefail

APP_NAME="Gestion Commerciale"
APP_SLUG="GestionCommerciale"
VERSION="1.0.0"

cd "$(dirname "$0")/.."
echo "==> Dossier projet : $(pwd)"

# ---- 1. Environnement virtuel ----------------------------------------
if [ ! -d ".venv" ]; then
    echo "==> Création de l'environnement virtuel"
    python3 -m venv .venv
fi
source .venv/bin/activate

echo "==> Installation des dépendances"
pip install --upgrade pip
pip install -r requirements.txt py2app

# ---- 2. Icône (facultative) -------------------------------------------
echo "==> Génération de l'icône"
python scripts/make_icon.py || echo "    (icône ignorée : PIL indisponible)"
if [ -d "resources/AppIcon.iconset" ] && command -v iconutil >/dev/null 2>&1; then
    iconutil -c icns resources/AppIcon.iconset -o resources/AppIcon.icns
    echo "    AppIcon.icns généré"
fi

# ---- 3. Bundle .app ----------------------------------------------------
echo "==> Construction du bundle .app (py2app)"
rm -rf build dist
python setup.py py2app

# ---- 4. Image disque .dmg ----------------------------------------------
echo "==> Création de l'image disque .dmg"
DMG_DIR="dist/dmg"
mkdir -p "$DMG_DIR"
cp -R "dist/${APP_NAME}.app" "$DMG_DIR/"
ln -sf /Applications "$DMG_DIR/Applications"

hdiutil create \
    -volname "$APP_NAME" \
    -srcfolder "$DMG_DIR" \
    -ov -format UDZO \
    "dist/${APP_SLUG}-${VERSION}.dmg"

rm -rf "$DMG_DIR"

echo ""
echo "==> Terminé !"
echo "    Application : dist/${APP_NAME}.app"
echo "    Installeur  : dist/${APP_SLUG}-${VERSION}.dmg"
