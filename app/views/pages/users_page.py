"""Page Utilisateurs (réservée à l'administrateur)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QTableWidgetItem

from app.controllers.user_controller import UserController
from app.views.dialogs import UserDialog
from app.views.pages.base_page import BasePage


class UsersPage(BasePage):
    """Gestion des comptes utilisateurs et de leurs rôles."""

    def __init__(self, user, parent=None):
        super().__init__("Utilisateurs", user, parent)

        self.add_action("＋ Ajouter", self._add, primary=True)
        self.add_action("✎ Modifier", self._edit)
        self.add_action("Activer / Désactiver", self._toggle_active)
        self.add_action("🗑 Supprimer", self._delete, danger=True)

        self.table = self.make_table(
            ["Nom d'utilisateur", "Nom complet", "Rôle", "Statut", "Créé le"]
        )
        self.table.doubleClicked.connect(lambda _i: self._edit())
        self.main_layout.addWidget(self.table)
        self.refresh()

    def refresh(self) -> None:
        users = UserController.list_users()
        self.table.setRowCount(len(users))
        for row, user in enumerate(users):
            values = [
                user["username"],
                user["full_name"] or "—",
                "Administrateur" if user["role"] == "admin" else "Caissier",
                "Actif" if user["active"] else "Désactivé",
                user["created_at"].strftime("%d/%m/%Y"),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, user["id"])
                if col == 3:
                    item.setForeground(QColor("#28A745" if user["active"] else "#FF3B30"))
                self.table.setItem(row, col, item)

    def _add(self) -> None:
        dialog = UserDialog(self)
        if dialog.exec():
            try:
                UserController.create_user(dialog.data(), self.user)
            except ValueError as exc:
                self.show_error(str(exc))
            self.refresh()

    def _edit(self) -> None:
        user_id = self.selected_row_id(self.table)
        if user_id is None:
            self.show_error("Sélectionnez un utilisateur à modifier.")
            return
        target = next((u for u in UserController.list_users() if u["id"] == user_id), None)
        if target is None:
            self.show_error("Utilisateur introuvable.")
            return
        dialog = UserDialog(self, target)
        if dialog.exec():
            data = dialog.data()
            try:
                UserController.update_user(
                    user_id, {"full_name": data["full_name"], "role": data["role"]}, self.user)
                if data["password"]:
                    UserController.set_password(user_id, data["password"], self.user)
            except ValueError as exc:
                self.show_error(str(exc))
            self.refresh()

    def _toggle_active(self) -> None:
        user_id = self.selected_row_id(self.table)
        if user_id is None:
            self.show_error("Sélectionnez un utilisateur.")
            return
        target = next((u for u in UserController.list_users() if u["id"] == user_id), None)
        if target is None:
            return
        try:
            UserController.set_active(user_id, not target["active"], self.user)
        except ValueError as exc:
            self.show_error(str(exc))
        self.refresh()

    def _delete(self) -> None:
        user_id = self.selected_row_id(self.table)
        if user_id is None:
            self.show_error("Sélectionnez un utilisateur à supprimer.")
            return
        if not self.confirm("Supprimer définitivement ce compte ?"):
            return
        try:
            UserController.delete_user(user_id, self.user)
        except ValueError as exc:
            self.show_error(str(exc))
        self.refresh()
