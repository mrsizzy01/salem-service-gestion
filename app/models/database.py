"""Connexion à la base SQLite et fabrique de sessions SQLAlchemy.

Le moteur est initialisé une seule fois au démarrage (``init_engine``).
Les contrôleurs obtiennent ensuite des sessions unitaires via
``get_session()`` utilisées en gestionnaire de contexte :

    with get_session() as session:
        session.add(obj)
        session.commit()
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

# Base déclarative commune à tous les modèles.
Base = declarative_base()

_engine: Optional[Engine] = None
_session_factory: Optional[sessionmaker] = None


def init_engine(db_path: Optional[Path] = None) -> Engine:
    """Initialise le moteur SQLAlchemy (une seule fois).

    :param db_path: chemin alternatif (tests). Par défaut, le chemin
                    standard de ``config.database_path()``.
    """
    global _engine, _session_factory
    if _engine is not None:
        return _engine

    if db_path is None:
        from app.config import database_path

        db_path = database_path()

    # check_same_thread=False : Qt peut utiliser plusieurs threads.
    _engine = create_engine(
        f"sqlite:///{db_path}", echo=False, future=True, connect_args={"check_same_thread": False}
    )

    # Active les clés étrangères SQLite à chaque connexion.
    @event.listens_for(_engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # expire_on_commit=False : les objets restent lisibles après commit,
    # ce qui simplifie le rafraîchissement de l'interface.
    _session_factory = sessionmaker(bind=_engine, expire_on_commit=False, future=True)
    return _engine


def get_engine() -> Engine:
    """Retourne le moteur courant (l'initialise si nécessaire)."""
    if _engine is None:
        init_engine()
    return _engine


def get_session() -> Session:
    """Retourne une nouvelle session liée au moteur courant."""
    if _session_factory is None:
        init_engine()
    return _session_factory()


def reset_engine() -> None:
    """Ferme le moteur et réinitialise la fabrique.

    Utilisé par les tests et avant une restauration de sauvegarde.
    """
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None
