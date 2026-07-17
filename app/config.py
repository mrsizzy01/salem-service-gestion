"""Configuration globale de l'application.

Centralise les chemins (base de données, factures, sauvegardes, images)
et les constantes. Les données sont stockées hors du bundle de
l'application afin de survivre aux mises à jour :

- macOS   : ~/Library/Application Support/GestionCommerciale/
- Windows : %APPDATA%/GestionCommerciale/
- Linux   : ~/.local/share/gestion-commerciale/

La variable d'environnement ``GESTION_DATA_DIR`` permet de forcer un
autre emplacement (utilisé par les tests).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# ------------------------------------------------------------------
# Constantes applicatives
# ------------------------------------------------------------------
APP_NAME = "Salem Service"
APP_SUBTITLE = "Gestion Commerciale"
ORG_NAME = "SalemService"          # utilisé par QSettings
DB_FILENAME = "gestion.db"
DATE_FORMAT = "%d/%m/%Y"
DATETIME_FORMAT = "%d/%m/%Y %H:%M"

# Rôles utilisateurs
ROLE_ADMIN = "admin"
ROLE_CAISSIER = "caissier"

# Statuts de vente
SALE_VALIDATED = "validée"
SALE_CANCELLED = "annulée"

# Types de mouvements de stock
MOVE_IN = "entrée"
MOVE_OUT = "sortie"
MOVE_ADJUST = "ajustement"


def data_dir() -> Path:
    """Retourne (et crée) le dossier de données de l'application."""
    override = os.environ.get("GESTION_DATA_DIR")
    if override:
        path = Path(override)
    elif sys.platform == "darwin":
        path = Path.home() / "Library" / "Application Support" / "GestionCommerciale"
    elif sys.platform == "win32":
        path = Path(os.environ.get("APPDATA", str(Path.home()))) / "GestionCommerciale"
    else:
        path = Path.home() / ".local" / "share" / "gestion-commerciale"
    path.mkdir(parents=True, exist_ok=True)
    return path


def database_path() -> Path:
    """Chemin complet du fichier SQLite."""
    return data_dir() / DB_FILENAME


def invoices_dir() -> Path:
    """Dossier de stockage des factures PDF générées."""
    path = data_dir() / "factures"
    path.mkdir(parents=True, exist_ok=True)
    return path


def reports_dir() -> Path:
    """Dossier d'export des rapports (PDF / Excel)."""
    path = data_dir() / "rapports"
    path.mkdir(parents=True, exist_ok=True)
    return path


def backups_dir() -> Path:
    """Dossier des sauvegardes de la base de données."""
    path = data_dir() / "sauvegardes"
    path.mkdir(parents=True, exist_ok=True)
    return path


def images_dir() -> Path:
    """Dossier des images (logo, photos produits)."""
    path = data_dir() / "images"
    path.mkdir(parents=True, exist_ok=True)
    return path
