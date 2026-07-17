"""Point d'entrée de l'application de gestion commerciale.

Séquence de démarrage :
1. création de l'application Qt ;
2. initialisation du moteur SQLite + migrations automatiques ;
3. création du compte administrateur par défaut si besoin ;
4. boucle connexion → fenêtre principale → (déconnexion → connexion…).

Lancer en développement :  ``python main.py``
"""

from __future__ import annotations

import logging
import sys

from PySide6.QtWidgets import QApplication, QDialog

from app.config import APP_NAME, ORG_NAME
from app.controllers.settings_controller import SettingsController
from app.models.database import init_engine
from app.models.migrations import run_migrations
from app.services.auth_service import ensure_default_admin
from app.utils import theme as theme_module
from app.views.login_dialog import LoginDialog
from app.views.main_window import MainWindow


def main() -> int:
    """Lance l'application de bureau."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s : %(message)s",
    )

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(ORG_NAME)

    # ---- Initialisation des données ------------------------------------
    engine = init_engine()
    applied = run_migrations(engine)
    if applied:
        logging.getLogger(__name__).info("Migrations appliquées : %s", applied)
    ensure_default_admin()
    SettingsController.get_company()  # crée les paramètres par défaut

    # Thème persisté (clair par défaut).
    from PySide6.QtCore import QSettings

    saved_theme = QSettings(ORG_NAME, APP_NAME).value("theme", theme_module.THEME_LIGHT)
    app.setStyleSheet(theme_module.get_stylesheet(saved_theme))

    # ---- Boucle connexion / session ------------------------------------
    while True:
        login = LoginDialog()
        if login.exec() != QDialog.DialogCode.Accepted:
            break  # fermeture de la fenêtre de connexion → quitter
        window = MainWindow(login.user)
        window.show()
        app.exec()
        if not window.was_logout:
            break  # fenêtre fermée normalement → quitter
        # sinon : déconnexion → nouvelle boucle de connexion

    return 0


if __name__ == "__main__":
    sys.exit(main())
