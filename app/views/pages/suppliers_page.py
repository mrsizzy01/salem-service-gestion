"""Page Fournisseurs."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTableWidgetItem

from app.controllers.supplier_controller import SupplierController
from app.views.dialogs import PersonDialog
from app.views.pages.base_page import BasePage


class SuppliersPage(BasePage):
    """Gestion des fournisseurs."""

    def __init__(self, user, parent=None):
        super().__init__("Fournisseurs", user, parent)

        self.add_action("＋ Ajouter", self._add, primary=True)
        self.add_action("✎ Modifier", self._edit)
        self.add_action("🗑 Supprimer", self._delete, danger=True)

        self.table = self.make_table(["Nom", "Téléphone", "Email", "Adresse / Commune"])
        self.table.doubleClicked.connect(lambda _i: self._edit())
        self.main_layout.addWidget(self.table)
        self.refresh()

    def set_search(self, text: str) -> None:
        self._search = text
        self.refresh()

    def refresh(self) -> None:
        suppliers = SupplierController.list_suppliers(self._search)
        self.table.setRowCount(len(suppliers))
        for row, supplier in enumerate(suppliers):
            addr_parts = []
            if supplier.get("address"):
                addr_parts.append(supplier["address"])
            if supplier.get("commune"):
                addr_parts.append(supplier["commune"])
            elif supplier.get("city"):
                addr_parts.append(supplier["city"])
            full_addr = ", ".join(addr_parts) or "—"

            values = [
                supplier["name"],
                supplier["phone"] or "—",
                supplier["email"] or "—",
                full_addr
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, supplier["id"])
                self.table.setItem(row, col, item)

    def _add(self) -> None:
        dialog = PersonDialog("fournisseur", self)
        if dialog.exec():
            try:
                SupplierController.save_supplier(dialog.data(), self.user)
            except ValueError as exc:
                self.show_error(str(exc))
            self.refresh()

    def _edit(self) -> None:
        supplier_id = self.selected_row_id(self.table)
        if supplier_id is None:
            self.show_error("Sélectionnez un fournisseur à modifier.")
            return
        supplier = next((s for s in SupplierController.list_suppliers()
                         if s["id"] == supplier_id), None)
        if supplier is None:
            self.show_error("Fournisseur introuvable.")
            return
        dialog = PersonDialog("fournisseur", self, supplier)
        if dialog.exec():
            try:
                SupplierController.save_supplier(dialog.data(), self.user, supplier_id)
            except ValueError as exc:
                self.show_error(str(exc))
            self.refresh()

    def _delete(self) -> None:
        supplier_id = self.selected_row_id(self.table)
        if supplier_id is None:
            self.show_error("Sélectionnez un fournisseur à supprimer.")
            return
        if not self.confirm("Supprimer ce fournisseur ?"):
            return
        try:
            SupplierController.delete_supplier(supplier_id, self.user)
        except ValueError as exc:
            self.show_error(str(exc))
        self.refresh()
