"""Page Clients (module facultatif).

L'enregistrement des clients n'est jamais obligatoire : les informations
saisies sur la facture suffisent. Cette page sert à fidéliser les
clients réguliers et à pré-remplir les factures.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QTableWidgetItem

from app.controllers.customer_controller import CustomerController
from app.views.dialogs import PersonDialog
from app.views.pages.base_page import BasePage


class CustomersPage(BasePage):
    """Gestion des clients enregistrés."""

    def __init__(self, user, parent=None):
        super().__init__("Clients", user, parent)

        note = QLabel("L'enregistrement des clients est facultatif : les informations "
                      "peuvent être saisies directement sur chaque facture.")
        note.setObjectName("muted")
        note.setWordWrap(True)
        self.main_layout.addWidget(note)

        self.add_action("＋ Ajouter", self._add, primary=True)
        self.add_action("✎ Modifier", self._edit)
        self.add_action("🗑 Supprimer", self._delete, danger=True)

        self.table = self.make_table(["Nom", "Téléphone", "Email", "Adresse / Commune", "Limite de crédit"])
        self.table.doubleClicked.connect(lambda _i: self._edit())
        self.main_layout.addWidget(self.table)
        self.refresh()

    def set_search(self, text: str) -> None:
        self._search = text
        self.refresh()

    def refresh(self) -> None:
        from app.utils.helpers import format_money
        customers = CustomerController.list_customers(self._search)
        self.table.setRowCount(len(customers))
        for row, customer in enumerate(customers):
            addr_parts = []
            if customer.get("address"):
                addr_parts.append(customer["address"])
            if customer.get("commune"):
                addr_parts.append(customer["commune"])
            elif customer.get("city"):
                addr_parts.append(customer["city"])
            full_addr = ", ".join(addr_parts) or "—"

            values = [
                customer["name"],
                customer["phone"] or "—",
                customer["email"] or "—",
                full_addr,
                format_money(customer["credit_limit"], "USD")
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 4:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, customer["id"])
                self.table.setItem(row, col, item)

    def _add(self) -> None:
        dialog = PersonDialog("client", self)
        if dialog.exec():
            try:
                CustomerController.save_customer(dialog.data(), self.user)
            except ValueError as exc:
                self.show_error(str(exc))
            self.refresh()

    def _edit(self) -> None:
        customer_id = self.selected_row_id(self.table)
        if customer_id is None:
            self.show_error("Sélectionnez un client à modifier.")
            return
        customer = next((c for c in CustomerController.list_customers()
                         if c["id"] == customer_id), None)
        if customer is None:
            self.show_error("Client introuvable.")
            return
        dialog = PersonDialog("client", self, customer)
        if dialog.exec():
            try:
                CustomerController.save_customer(dialog.data(), self.user, customer_id)
            except ValueError as exc:
                self.show_error(str(exc))
            self.refresh()

    def _delete(self) -> None:
        customer_id = self.selected_row_id(self.table)
        if customer_id is None:
            self.show_error("Sélectionnez un client à supprimer.")
            return
        if not self.confirm("Supprimer ce client ?\n"
                            "Les factures existantes conservent ses informations."):
            return
        try:
            CustomerController.delete_customer(customer_id, self.user)
        except ValueError as exc:
            self.show_error(str(exc))
        self.refresh()
