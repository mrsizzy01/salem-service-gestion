"""Widgets réutilisables : barre latérale, barre supérieure, cartes.

Ces composants ne contiennent aucune logique métier ; ils émettent des
signaux consommés par la fenêtre principale.
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.utils.icons import icon

# Couleurs d'accent par défaut des pictogrammes (adaptées au thème par
# la fenêtre principale via ``ICON_COLOR``).
ICON_COLOR = "#6E6E73"


# ------------------------------------------------------------------
# Carte de statistique (tableau de bord)
# ------------------------------------------------------------------
class StatCard(QFrame):
    """Carte affichant un indicateur : icône, titre et valeur."""

    def __init__(self, title: str, icon_name: str, accent: str = "#0A84FF",
                 parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("StatCard")
        self.setMinimumHeight(96)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        # Pastille d'icône colorée.
        badge = QLabel()
        badge.setFixedSize(44, 44)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setPixmap(icon(icon_name, "#FFFFFF", 22).pixmap(QSize(22, 22)))
        badge.setStyleSheet(f"background-color: {accent}; border-radius: 12px;")
        layout.addWidget(badge)

        texts = QVBoxLayout()
        texts.setSpacing(2)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("StatTitle")
        self.value_label = QLabel("—")
        self.value_label.setObjectName("StatValue")
        texts.addWidget(self.title_label)
        texts.addWidget(self.value_label)
        layout.addLayout(texts, 1)

    def set_value(self, value: str) -> None:
        """Met à jour la valeur affichée (élidée si trop longue)."""
        metrics = self.value_label.fontMetrics()
        available = max(self.value_label.width(), 120)
        self.value_label.setText(metrics.elidedText(
            value, Qt.TextElideMode.ElideRight, available))
        self.value_label.setToolTip(value)


# ------------------------------------------------------------------
# Barre latérale
# ------------------------------------------------------------------
class Sidebar(QFrame):
    """Barre latérale de navigation (logo + boutons de modules)."""

    page_requested = Signal(str)  # clé de la page demandée

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(260)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(14, 18, 14, 14)
        self._layout.setSpacing(4)

        # En-tête : nom de l'application.
        name = QLabel("Salem\nService")
        name.setObjectName("AppName")
        subtitle = QLabel("Gestion Commerciale")
        subtitle.setObjectName("AppSubtitle")
        self._layout.addWidget(name)
        self._layout.addWidget(subtitle)
        self._layout.addSpacing(18)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons: dict[str, QToolButton] = {}
        self._icon_map: dict[str, str] = {}
        self._icon_color = ICON_COLOR
        self._layout.addStretch()

    def add_page(self, key: str, label: str, icon_name: str) -> None:
        """Ajoute un bouton de navigation pour une page."""
        button = QToolButton()
        button.setObjectName("NavButton")
        button.setText(f"  {label}")
        button.setIcon(icon(icon_name, ICON_COLOR, 18))
        button.setIconSize(QSize(18, 18))
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        button.setMinimumHeight(40)
        button.setStyleSheet("QToolButton { padding: 10px 14px; font-size: 13px; }")
        button.setCheckable(True)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setSizePolicy(button.sizePolicy().horizontalPolicy().Expanding,
                             button.sizePolicy().verticalPolicy().Fixed)
        # Insère avant l'étirement final.
        self._layout.insertWidget(self._layout.count() - 1, button)
        self._group.addButton(button)
        self._buttons[key] = button
        self._icon_map[key] = icon_name
        button.clicked.connect(lambda _checked=False, k=key: self.page_requested.emit(k))

    def set_current(self, key: str) -> None:
        """Coche le bouton actif et met son icône en blanc."""
        for name, button in self._buttons.items():
            active = name == key
            button.setChecked(active)
            color = "#FFFFFF" if active else self._icon_color
            button.setIcon(icon(self._icon_map[name], color, 18))

    def refresh_icons(self, color: str, icon_map: dict[str, str] | None = None) -> None:
        """Met à jour la couleur des icônes lors d'un changement de thème."""
        self._icon_color = color
        for key, button in self._buttons.items():
            effective = "#FFFFFF" if button.isChecked() else color
            button.setIcon(icon(self._icon_map[key], effective, 18))


# ------------------------------------------------------------------
# Barre supérieure
# ------------------------------------------------------------------
class TopBar(QFrame):
    """Barre supérieure : titre de page, recherche globale, thème, utilisateur."""

    search_changed = Signal(str)
    theme_toggle_requested = Signal()
    logout_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("TopBar")
        self.setFixedHeight(60)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(12)

        self.title_label = QLabel("Tableau de bord")
        self.title_label.setObjectName("title")
        layout.addWidget(self.title_label)
        layout.addStretch()

        # Champ de recherche global avec pictogramme intégré.
        search_container = QFrame()
        search_container.setFixedWidth(280)
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(0, 0, 0, 0)
        self.search_edit = QLineEdit()
        self.search_edit.setObjectName("SearchEdit")
        self.search_edit.setPlaceholderText("Rechercher…")
        self.search_edit.setClearButtonEnabled(True)
        self.search_icon = QLabel(self.search_edit)
        self.search_icon.setPixmap(icon("search", "#8E8E93", 16).pixmap(QSize(16, 16)))
        self.search_icon.move(9, 9)
        search_layout.addWidget(self.search_edit)
        layout.addWidget(search_container)
        self.search_edit.textChanged.connect(self.search_changed)

        # Bouton thème clair / sombre.
        self.theme_button = QToolButton()
        self.theme_button.setMinimumSize(36, 36)
        self.theme_button.setObjectName("IconButton")
        self.theme_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_button.setToolTip("Basculer clair / sombre")
        self.theme_button.clicked.connect(self.theme_toggle_requested)
        layout.addWidget(self.theme_button)

        # Utilisateur connecté + déconnexion.
        self.user_label = QLabel()
        self.user_label.setObjectName("muted")
        layout.addWidget(self.user_label)
        self.logout_button = QPushButton("Déconnexion")
        self.logout_button.setMinimumHeight(34)
        self.logout_button.setMinimumWidth(110)
        self.logout_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.logout_button.clicked.connect(self.logout_requested)
        layout.addWidget(self.logout_button)

    def set_user(self, full_name: str, role: str) -> None:
        """Affiche l'utilisateur connecté et son rôle."""
        role_label = "Administrateur" if role == "admin" else "Caissier"
        self.user_label.setText(f"{full_name} · {role_label}")

    def set_theme_icon(self, dark: bool) -> None:
        """Adapte le pictogramme au thème courant."""
        name = "sun" if dark else "moon"
        self.theme_button.setIcon(icon(name, "#6E6E73", 18))
