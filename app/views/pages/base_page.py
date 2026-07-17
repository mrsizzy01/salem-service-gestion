"""Base commune des pages : en-tête standard et tableaux configurés."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)


class BasePage(QFrame):
    """Page générique : boutons d'action en haut, contenu dessous.

    Les sous-classes implémentent ``refresh()`` et, si elles gèrent la
    recherche globale, ``set_search(text)``.
    """

    def __init__(self, title: str, user, parent: QWidget | None = None):
        super().__init__(parent)
        self.user = user                    # utilisateur connecté
        self._title = title                 # utilisé pour les dialogues
        self._search = ""                   # filtre de recherche global
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(24, 16, 24, 20)
        self.main_layout.setSpacing(14)

        # En-tête : boutons d'action alignés à droite
        # (le titre de la page est affiché dans la barre supérieure).
        header = QHBoxLayout()
        header.addStretch()
        self.actions_layout = QHBoxLayout()
        self.actions_layout.setSpacing(10)
        header.addLayout(self.actions_layout)
        self.main_layout.addLayout(header)

    # ------------------------------------------------------------------
    # Helpers d'interface
    # ------------------------------------------------------------------
    def add_action(self, label: str, callback, primary: bool = False,
                   danger: bool = False) -> QPushButton:
        """Ajoute un bouton d'action dans l'en-tête de la page."""
        button = QPushButton(label)
        if primary:
            button.setObjectName("PrimaryButton")
        if danger:
            button.setObjectName("DangerButton")
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setMinimumWidth(120)
        button.setMinimumHeight(34)
        button.setStyleSheet(button.styleSheet() + "QPushButton { padding: 8px 16px; font-size: 13px; }")
        button.clicked.connect(callback)
        self.actions_layout.addWidget(button)
        return button

    @staticmethod
    def make_table(headers: list[str]) -> QTableWidget:
        """Crée un tableau configuré de façon homogène."""
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(40)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setShowGrid(False)
        return table

    def selected_row_id(self, table: QTableWidget, column: int = 0) -> int | None:
        """Retourne l'identifiant (texte de la colonne) de la ligne choisie."""
        row = table.currentRow()
        if row < 0:
            return None
        item = table.item(row, column)
        if item is None:
            return None
        try:
            return int(item.data(Qt.ItemDataRole.UserRole) or item.text())
        except (TypeError, ValueError):
            return None

    # ------------------------------------------------------------------
    # Messages standard
    # ------------------------------------------------------------------
    def show_error(self, message: str) -> None:
        """Affiche une erreur métier."""
        QMessageBox.warning(self, self._title, message)

    def confirm(self, message: str) -> bool:
        """Demande une confirmation à l'utilisateur."""
        answer = QMessageBox.question(
            self, self._title, message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    # ------------------------------------------------------------------
    # Contrats des pages
    # ------------------------------------------------------------------
    def refresh(self) -> None:
        """Recharge les données affichées. À redéfinir."""

    def set_search(self, text: str) -> None:
        """Applique le filtre de recherche global. À redéfinir si utile."""
        self._search = text
