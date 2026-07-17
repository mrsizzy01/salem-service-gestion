"""Service de journalisation : enregistre chaque action importante."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.database import get_session
from app.models.entities import AuditLog, User


def log_action(action: str, details: str = "", user: User | None = None,
               session: Session | None = None) -> None:
    """Écrit une entrée dans le journal d'audit.

    :param action:  libellé court (ex. « Création produit »).
    :param details: informations complémentaires (ex. « Produit #12 »).
    :param user:    utilisateur à l'origine de l'action (facultatif).
    :param session: session SQLAlchemy existante pour participer à la
                    transaction en cours (sinon session autonome).
    """
    entry = AuditLog(
        user_id=user.id if user else None,
        username=user.username if user else "système",
        action=action,
        details=details,
    )
    if session is not None:
        session.add(entry)
    else:
        with get_session() as s:
            s.add(entry)
            s.commit()
