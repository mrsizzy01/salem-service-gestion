"""Service de sauvegarde et de restauration de la base SQLite.

Sauvegarde : copie horodatée du fichier SQLite dans le dossier
``sauvegardes`` des données applicatives.

Restauration : remplacement du fichier courant par une copie choisie
par l'utilisateur. Le moteur SQLAlchemy est fermé avant remplacement ;
l'application doit ensuite être redémarrée (demandé à l'utilisateur).
"""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from app.config import backups_dir, database_path
from app.models.database import reset_engine


def create_backup() -> Path:
    """Crée une copie horodatée de la base et retourne son chemin."""
    src = database_path()
    if not src.exists():
        raise FileNotFoundError("La base de données n'existe pas encore.")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = backups_dir() / f"sauvegarde_{stamp}.db"
    shutil.copy2(src, dest)
    return dest


def list_backups() -> list[Path]:
    """Liste les sauvegardes disponibles, de la plus récente à la plus ancienne."""
    return sorted(backups_dir().glob("*.db"), reverse=True)


def restore_backup(source: str | Path) -> None:
    """Remplace la base courante par le fichier ``source``.

    Une copie de sécurité de la base actuelle est réalisée avant
    remplacement. L'application doit être redémarrée ensuite.
    """
    source = Path(source)
    if not source.exists():
        raise FileNotFoundError(f"Fichier introuvable : {source}")

    target = database_path()
    # Copie de sécurité de l'état actuel avant écrasement.
    if target.exists():
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(target, backups_dir() / f"avant_restauration_{stamp}.db")

    # Ferme proprement le moteur avant de remplacer le fichier.
    reset_engine()
    shutil.copy2(source, target)
