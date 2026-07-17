"""Contrôleur Paramètres : informations de l'entreprise et logo."""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from app.config import images_dir
from app.models.database import get_session
from app.models.entities import CompanySettings, User
from app.services.audit_service import log_action


class SettingsController:
    """Lecture et mise à jour des paramètres de l'entreprise (ligne unique)."""

    @staticmethod
    def get_company() -> dict:
        """Retourne les paramètres de l'entreprise (créés si absents)."""
        with get_session() as session:
            settings = session.get(CompanySettings, 1)
            if settings is None:
                settings = CompanySettings(id=1)
                session.add(settings)
                session.commit()
            return SettingsController._to_dict(settings)

    @staticmethod
    def update_company(data: dict, user: User | None = None) -> dict:
        """Met à jour les informations de l'entreprise."""
        with get_session() as session:
            settings = session.get(CompanySettings, 1)
            if settings is None:
                settings = CompanySettings(id=1)
                session.add(settings)
            for field in ("name", "address", "phone", "email", "currency",
                          "thanks_message", "logo_path"):
                if field in data:
                    setattr(settings, field, str(data[field]).strip())
            session.commit()
            log_action("Mise à jour paramètres", settings.name, user)
            return SettingsController._to_dict(settings)

    @staticmethod
    def import_logo(source_path: str) -> str:
        """Copie le logo choisi dans le dossier applicatif."""
        src = Path(source_path)
        if not src.exists():
            raise FileNotFoundError(f"Logo introuvable : {source_path}")
        dest = images_dir() / f"logo_{uuid.uuid4().hex[:8]}{src.suffix.lower()}"
        shutil.copy2(src, dest)
        return str(dest)

    @staticmethod
    def _to_dict(settings: CompanySettings) -> dict:
        """Convertit les paramètres en dictionnaire simple."""
        return {
            "name": settings.name,
            "address": settings.address,
            "phone": settings.phone,
            "email": settings.email,
            "currency": settings.currency,
            "logo_path": settings.logo_path,
            "thanks_message": settings.thanks_message,
        }
