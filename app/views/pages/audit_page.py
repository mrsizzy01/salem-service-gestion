"""Page Journal d'audit (réservée à l'administrateur)."""

from __future__ import annotations

from PySide6.QtWidgets import QTableWidgetItem

from app.controllers.user_controller import UserController
from app.views.pages.base_page import BasePage


class AuditPage(BasePage):
    """Journal complet des actions réalisées dans l'application."""

    def __init__(self, user, parent=None):
        super().__init__("Journal des actions", user, parent)

        self.add_action("Actualiser", self.refresh, primary=True)

        self.table = self.make_table(["Date et heure", "Utilisateur", "Action", "Détails"])
        self.main_layout.addWidget(self.table)
        self.refresh()

    def set_search(self, text: str) -> None:
        self._search = text
        self.refresh()

    def refresh(self) -> None:
        logs = UserController.list_audit_logs(1000)
        if self._search.strip():
            needle = self._search.strip().lower()
            logs = [l for l in logs
                    if needle in l["action"].lower()
                    or needle in l["details"].lower()
                    or needle in l["username"].lower()]
        self.table.setRowCount(len(logs))
        for row, log in enumerate(logs):
            values = [
                log["created_at"].strftime("%d/%m/%Y %H:%M:%S"),
                log["username"],
                log["action"],
                log["details"] or "—",
            ]
            for col, value in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(value))
