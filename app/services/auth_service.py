"""Service d'authentification : hachage PBKDF2 et vérification.

Aucune dépendance externe : utilisation de ``hashlib.pbkdf2_hmac``
(SHA-256, 200 000 itérations, sel aléatoire de 16 octets).
Le hash stocké a la forme ``iterations$sel_hex$hash_hex``.
"""

from __future__ import annotations

import hashlib
import hmac
import os

from app.config import ROLE_ADMIN
from app.models.database import get_session
from app.models.entities import User

_ITERATIONS = 200_000


def hash_password(password: str) -> str:
    """Retourne le hash PBKDF2 d'un mot de passe (format stockable)."""
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
    return f"{_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Vérifie un mot de passe contre le hash stocké (temps constant)."""
    try:
        iterations_s, salt_hex, hash_hex = stored.split("$")
        iterations = int(iterations_s)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
    except (ValueError, TypeError):
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(digest, expected)


def authenticate(username: str, password: str) -> User | None:
    """Retourne l'utilisateur si les identifiants sont valides, sinon None."""
    with get_session() as session:
        user = (
            session.query(User)
            .filter(User.username == username.strip(), User.active.is_(True))
            .first()
        )
        if user and verify_password(password, user.password_hash):
            # Détache l'objet pour une utilisation hors session.
            session.expunge(user)
            return user
    return None


def ensure_default_admin() -> bool:
    """Crée le compte administrateur par défaut au premier lancement.

    Identifiants : ``admin`` / ``admin123`` (à changer immédiatement).

    :return: True si le compte a été créé.
    """
    with get_session() as session:
        count = session.query(User).count()
        if count == 0:
            admin = User(
                username="admin",
                password_hash=hash_password("admin123"),
                full_name="Administrateur",
                role=ROLE_ADMIN,
                active=True,
            )
            session.add(admin)
            session.commit()
            return True
    return False
