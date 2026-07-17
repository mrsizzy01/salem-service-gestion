"""Contrôleur Utilisateurs : gestion des comptes et des rôles."""

from __future__ import annotations

from app.config import ROLE_ADMIN
from app.models.database import get_session
from app.models.entities import AuditLog, User
from app.services.audit_service import log_action
from app.services.auth_service import hash_password


class UserController:
    """CRUD des utilisateurs (réservé à l'administrateur)."""

    @staticmethod
    def list_users() -> list[dict]:
        """Liste tous les comptes utilisateurs."""
        with get_session() as session:
            rows = session.query(User).order_by(User.username).all()
            return [
                {"id": u.id, "username": u.username, "full_name": u.full_name,
                 "role": u.role, "active": u.active, "created_at": u.created_at}
                for u in rows
            ]

    @staticmethod
    def create_user(data: dict, current_user: User | None = None) -> dict:
        """Crée un compte. ``data`` : username, full_name, role, password."""
        username = data.get("username", "").strip()
        if not username:
            raise ValueError("Le nom d'utilisateur est obligatoire.")
        if len(data.get("password", "")) < 4:
            raise ValueError("Le mot de passe doit contenir au moins 4 caractères.")
        with get_session() as session:
            if session.query(User).filter(User.username == username).first():
                raise ValueError(f"Le nom d'utilisateur « {username} » existe déjà.")
            user = User(
                username=username,
                full_name=data.get("full_name", "").strip(),
                role=data.get("role") if data.get("role") in ("admin", "caissier") else "caissier",
                password_hash=hash_password(data["password"]),
                active=True,
            )
            session.add(user)
            session.commit()
            log_action("Création utilisateur", username, current_user)
            return {"id": user.id, "username": user.username, "full_name": user.full_name,
                    "role": user.role, "active": user.active}

    @staticmethod
    def update_user(user_id: int, data: dict, current_user: User | None = None) -> None:
        """Met à jour nom complet et rôle d'un compte."""
        with get_session() as session:
            user = session.get(User, user_id)
            if user is None:
                raise ValueError("Utilisateur introuvable.")
            if "full_name" in data:
                user.full_name = data["full_name"].strip()
            if "role" in data and data["role"] in ("admin", "caissier"):
                UserController._guard_last_admin(session, user, new_role=data["role"])
                user.role = data["role"]
            session.commit()
            log_action("Modification utilisateur", user.username, current_user)

    @staticmethod
    def set_password(user_id: int, new_password: str,
                     current_user: User | None = None) -> None:
        """Réinitialise le mot de passe d'un compte."""
        if len(new_password) < 4:
            raise ValueError("Le mot de passe doit contenir au moins 4 caractères.")
        with get_session() as session:
            user = session.get(User, user_id)
            if user is None:
                raise ValueError("Utilisateur introuvable.")
            user.password_hash = hash_password(new_password)
            session.commit()
            log_action("Réinitialisation mot de passe", user.username, current_user)

    @staticmethod
    def set_active(user_id: int, active: bool, current_user: User | None = None) -> None:
        """Active ou désactive un compte (avec garde-fous)."""
        with get_session() as session:
            user = session.get(User, user_id)
            if user is None:
                raise ValueError("Utilisateur introuvable.")
            if not active:
                if current_user and user.id == current_user.id:
                    raise ValueError("Vous ne pouvez pas désactiver votre propre compte.")
                UserController._guard_last_admin(session, user, disabling=True)
            user.active = active
            session.commit()
            log_action(("Activation" if active else "Désactivation") + " utilisateur",
                       user.username, current_user)

    @staticmethod
    def delete_user(user_id: int, current_user: User | None = None) -> None:
        """Supprime un compte (avec garde-fous)."""
        with get_session() as session:
            user = session.get(User, user_id)
            if user is None:
                raise ValueError("Utilisateur introuvable.")
            if current_user and user.id == current_user.id:
                raise ValueError("Vous ne pouvez pas supprimer votre propre compte.")
            UserController._guard_last_admin(session, user, disabling=True)
            username = user.username
            session.delete(user)
            session.commit()
            log_action("Suppression utilisateur", username, current_user)

    @staticmethod
    def change_own_password(user_id: int, old_password: str, new_password: str) -> None:
        """Permet à un utilisateur de changer son propre mot de passe."""
        from app.services.auth_service import verify_password

        if len(new_password) < 4:
            raise ValueError("Le nouveau mot de passe doit contenir au moins 4 caractères.")
        with get_session() as session:
            user = session.get(User, user_id)
            if user is None or not verify_password(old_password, user.password_hash):
                raise ValueError("L'ancien mot de passe est incorrect.")
            user.password_hash = hash_password(new_password)
            session.commit()
            log_action("Changement de mot de passe", user.username, user)

    # ------------------------------------------------------------------
    # Journal d'audit
    # ------------------------------------------------------------------
    @staticmethod
    def list_audit_logs(limit: int = 1000) -> list[dict]:
        """Retourne le journal des actions, du plus récent au plus ancien."""
        with get_session() as session:
            rows = session.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()
            return [
                {"created_at": a.created_at, "username": a.username,
                 "action": a.action, "details": a.details}
                for a in rows
            ]

    # ------------------------------------------------------------------
    # Garde-fou : toujours conserver au moins un administrateur actif
    # ------------------------------------------------------------------
    @staticmethod
    def _guard_last_admin(session, user: User, new_role: str | None = None,
                          disabling: bool = False) -> None:
        """Empêche de retirer le dernier administrateur actif."""
        if user.role != ROLE_ADMIN or not user.active:
            return
        would_lose_admin = disabling or (new_role is not None and new_role != ROLE_ADMIN)
        if not would_lose_admin:
            return
        admins = (
            session.query(User)
            .filter(User.role == ROLE_ADMIN, User.active.is_(True), User.id != user.id)
            .count()
        )
        if admins == 0:
            raise ValueError("Impossible : il doit rester au moins un administrateur actif.")
