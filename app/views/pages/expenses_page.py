"""Page Dépenses de l'entreprise."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QTableWidgetItem

from app.controllers.expense_controller import ExpenseController
from app.controllers.settings_controller import SettingsController
from app.utils.helpers import format_money
from app.views.dialogs import ExpenseDialog
from app.views.pages.base_page import BasePage


class ExpensesPage(BasePage):
    """Gestion des dépenses."""

    def __init__(self, user, parent=None):
        super().__init__("Dépenses", user, parent)
        self.currency = SettingsController.get_company().get("currency", "FCFA")

        self.add_action("＋ Ajouter", self._add, primary=True)
        self.add_action("✎ Modifier", self._edit)
        self.add_action("🗑 Supprimer", self._delete, danger=True)

        self.total_label = QLabel()
        self.total_label.setObjectName("muted")
        self.main_layout.addWidget(self.total_label)

        self.table = self.make_table(["Date", "Libellé", "Catégorie", "Montant", "Note"])
        self.table.doubleClicked.connect(lambda _i: self._edit())
        self.main_layout.addWidget(self.table)
        self.refresh()

    def set_search(self, text: str) -> None:
        self._search = text
        self.refresh()

    def refresh(self) -> None:
        expenses = ExpenseController.list_expenses(search=self._search)
        total = sum(e["amount"] for e in expenses)
        self.total_label.setText(
            f"{len(expenses)} dépense(s) — Total : {format_money(total, self.currency)}")
        self.table.setRowCount(len(expenses))
        for row, expense in enumerate(expenses):
            values = [
                expense["spent_at"].strftime("%d/%m/%Y"),
                expense["label"],
                expense["category"],
                format_money(expense["amount"], self.currency),
                expense["note"] or "—",
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 3:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, expense["id"])
                self.table.setItem(row, col, item)

    def _add(self) -> None:
        dialog = ExpenseDialog(self)
        if dialog.exec():
            try:
                ExpenseController.save_expense(dialog.data(), self.user)
            except ValueError as exc:
                self.show_error(str(exc))
            self.refresh()

    def _edit(self) -> None:
        expense_id = self.selected_row_id(self.table)
        if expense_id is None:
            self.show_error("Sélectionnez une dépense à modifier.")
            return
        expense = next((e for e in ExpenseController.list_expenses()
                        if e["id"] == expense_id), None)
        if expense is None:
            self.show_error("Dépense introuvable.")
            return
        dialog = ExpenseDialog(self, expense)
        if dialog.exec():
            try:
                ExpenseController.save_expense(dialog.data(), self.user, expense_id)
            except ValueError as exc:
                self.show_error(str(exc))
            self.refresh()

    def _delete(self) -> None:
        expense_id = self.selected_row_id(self.table)
        if expense_id is None:
            self.show_error("Sélectionnez une dépense à supprimer.")
            return
        if not self.confirm("Supprimer cette dépense ?"):
            return
        try:
            ExpenseController.delete_expense(expense_id, self.user)
        except ValueError as exc:
            self.show_error(str(exc))
        self.refresh()
