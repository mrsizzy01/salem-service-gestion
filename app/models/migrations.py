"""Gestionnaire de migrations de la base de données.

Principe : une table ``schema_version`` mémorise la version courante du
schéma. La liste ``MIGRATIONS`` contient, dans l'ordre, les migrations
``(version, description, fonction)``. Au démarrage, toutes les
migrations de version supérieure à la version courante sont exécutées
dans une transaction.

Pour faire évoluer le schéma :
1. modifier les entités dans ``entities.py`` ;
2. ajouter ici une nouvelle entrée ``(2, "...", _migration_002)`` qui
   applique les ``ALTER TABLE`` nécessaires (SQLite supporte
   ``ADD COLUMN``) — ne jamais modifier une migration déjà publiée.
"""

from __future__ import annotations

import logging
from typing import Callable

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.models.database import Base

log = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Migrations
# ------------------------------------------------------------------
def _migration_001(engine: Engine) -> None:
    """Version 1 : création initiale de toutes les tables."""
    # L'import des entités enregistre les tables dans Base.metadata.
    from app.models import entities  # noqa: F401

    Base.metadata.create_all(engine)


# Liste ordonnée des migrations : (version, description, callable).
def _migration_002(engine: Engine) -> None:
    """Version 2 : Ajout des colonnes manquantes et nouvelles tables."""
    from app.models import entities  # noqa: F401

    # 1. Création des nouvelles tables
    Base.metadata.create_all(engine)

    # 2. Ajout des colonnes aux tables existantes
    with engine.begin() as conn:
        # Table products
        try:
            conn.execute(text("ALTER TABLE products ADD COLUMN barcode VARCHAR(20) DEFAULT ''"))
        except Exception:
            pass

        # Table customers
        for col, col_type, default in [
            ("avenue", "VARCHAR(100)", "''"),
            ("quartier", "VARCHAR(100)", "''"),
            ("commune", "VARCHAR(100)", "''"),
            ("city", "VARCHAR(100)", "'Lubumbashi'"),
            ("province", "VARCHAR(100)", "'Haut-Katanga'"),
            ("credit_limit", "FLOAT", "0.0"),
        ]:
            try:
                conn.execute(text(f"ALTER TABLE customers ADD COLUMN {col} {col_type} DEFAULT {default}"))
            except Exception:
                pass

        # Table suppliers
        for col, col_type, default in [
            ("avenue", "VARCHAR(100)", "''"),
            ("quartier", "VARCHAR(100)", "''"),
            ("commune", "VARCHAR(100)", "''"),
            ("city", "VARCHAR(100)", "'Lubumbashi'"),
            ("province", "VARCHAR(100)", "'Haut-Katanga'"),
        ]:
            try:
                conn.execute(text(f"ALTER TABLE suppliers ADD COLUMN {col} {col_type} DEFAULT {default}"))
            except Exception:
                pass

        # Table sales
        for col, col_type, default in [
            ("tax_amount", "FLOAT", "0.0"),
            ("discount_amount", "FLOAT", "0.0"),
            ("currency", "VARCHAR(10)", "'CDF'"),
            ("exchange_rate", "FLOAT", "1.0"),
        ]:
            try:
                conn.execute(text(f"ALTER TABLE sales ADD COLUMN {col} {col_type} DEFAULT {default}"))
            except Exception:
                pass

        # Table sale_items
        try:
            conn.execute(text("ALTER TABLE sale_items ADD COLUMN discount_pct FLOAT DEFAULT 0.0"))
        except Exception:
            pass

        # Table company_settings
        for col, col_type, default in [
            ("avenue", "VARCHAR(100)", "''"),
            ("quartier", "VARCHAR(100)", "''"),
            ("commune", "VARCHAR(100)", "''"),
            ("city", "VARCHAR(100)", "'Lubumbashi'"),
            ("province", "VARCHAR(100)", "'Haut-Katanga'"),
            ("secondary_currency", "VARCHAR(10)", "'USD'"),
            ("exchange_rate", "FLOAT", "2800.0"),
            ("tax_rate", "FLOAT", "16.0"),
            ("id_nat", "VARCHAR(30)", "''"),
            ("rccm", "VARCHAR(30)", "''"),
            ("nif", "VARCHAR(30)", "''"),
            ("tax_center", "VARCHAR(100)", "''"),
        ]:
            try:
                conn.execute(text(f"ALTER TABLE company_settings ADD COLUMN {col} {col_type} DEFAULT {default}"))
            except Exception:
                pass


def _migration_003(engine: Engine) -> None:
    """Version 3 : Mise à jour du nom de l'entreprise par défaut à 'Salem Service'."""
    with engine.begin() as conn:
        # Si la ligne d'id 1 existe déjà, on met à jour son nom s'il a la valeur par défaut
        try:
            conn.execute(
                text(
                    "UPDATE company_settings "
                    "SET name = 'Salem Service' "
                    "WHERE id = 1 AND (name = 'Ma Maison de Vente' OR name = '' OR name IS NULL)"
                )
            )
        except Exception:
            pass


def _migration_004(engine: Engine) -> None:
    """Version 4 : Ajout de payment_method à sales et fidelity_points à customers."""
    with engine.begin() as conn:
        try:
            conn.execute(text("ALTER TABLE sales ADD COLUMN payment_method VARCHAR(40) DEFAULT 'Cash'"))
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE customers ADD COLUMN fidelity_points INTEGER DEFAULT 0"))
        except Exception:
            pass


MIGRATIONS: list[tuple[int, str, Callable[[Engine], None]]] = [
    (1, "Création initiale des tables", _migration_001),
    (2, "Mise à jour du schéma (colonnes et tables manquantes)", _migration_002),
    (3, "Mise à jour du nom de l'entreprise par défaut à Salem Service", _migration_003),
    (4, "Ajout de payment_method et fidelity_points", _migration_004),
]


# ------------------------------------------------------------------
# Moteur de migration
# ------------------------------------------------------------------
def _ensure_version_table(engine: Engine) -> None:
    """Crée la table de suivi des versions si elle n'existe pas."""
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS schema_version ("
                "  version INTEGER PRIMARY KEY,"
                "  description TEXT NOT NULL DEFAULT '',"
                "  applied_at TEXT NOT NULL DEFAULT (datetime('now'))"
                ")"
            )
        )


def current_version(engine: Engine) -> int:
    """Retourne la version actuellement appliquée (0 si aucune)."""
    _ensure_version_table(engine)
    with engine.begin() as conn:
        row = conn.execute(text("SELECT MAX(version) FROM schema_version")).scalar()
    return int(row or 0)


def run_migrations(engine: Engine) -> list[int]:
    """Applique toutes les migrations en attente.

    :return: la liste des versions nouvellement appliquées.
    """
    applied: list[int] = []
    version = current_version(engine)
    for mig_version, description, func in MIGRATIONS:
        if mig_version <= version:
            continue
        log.info("Application de la migration %s : %s", mig_version, description)
        func(engine)
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO schema_version (version, description) VALUES (:v, :d)"),
                {"v": mig_version, "d": description},
            )
        applied.append(mig_version)
    return applied
