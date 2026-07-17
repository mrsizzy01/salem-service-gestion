"""Paquet principal de l'application de gestion commerciale.

Architecture MVC :
- ``app.models``       : modèles SQLAlchemy + gestion de la base SQLite.
- ``app.controllers``  : logique métier (aucune dépendance Qt).
- ``app.services``     : services techniques (PDF, Excel, sauvegarde, auth).
- ``app.views``        : interface graphique PySide6 (aucune logique métier).
- ``app.utils``        : thèmes, icônes et helpers d'affichage.
"""

__version__ = "1.0.0"
