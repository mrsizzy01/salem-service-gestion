"""Page Produits : catalogue, catégories, prix et stock."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QTableWidgetItem

from app.controllers.product_controller import ProductController
from app.controllers.settings_controller import SettingsController
from app.utils.helpers import format_money, format_qty
from app.views.dialogs import ProductDialog
from app.views.pages.base_page import BasePage


class ProductsPage(BasePage):
    """Gestion du catalogue produits."""

    def __init__(self, user, parent=None):
        super().__init__("Produits", user, parent)
        self.currency = SettingsController.get_company().get("currency", "FCFA")

        # Filtre par catégorie.
        self.category_filter = QComboBox()
        self.category_filter.setMinimumWidth(180)
        self.category_filter.currentIndexChanged.connect(lambda _i: self.refresh())
        self.actions_layout.addWidget(self.category_filter)

        self.add_action("＋ Ajouter", self._add, primary=True)
        self.add_action("✎ Modifier", self._edit)
        self.add_action("🗑 Supprimer", self._delete, danger=True)

        self.table = self.make_table(
            ["Produit", "Référence", "Catégorie", "Prix d'achat",
             "Prix de vente", "Stock", "Marge", "Statut"]
        )
        self.table.doubleClicked.connect(lambda _i: self._edit())
        self.main_layout.addWidget(self.table)

        self.refresh()

    # ------------------------------------------------------------------
    # Données
    # ------------------------------------------------------------------
    def set_search(self, text: str) -> None:
        """Filtre la recherche globale (nom / référence)."""
        self._search = text
        self.refresh()

    def refresh(self) -> None:
        """Recharge catégories et produits."""
        current_filter = self.category_filter.currentData()
        self.category_filter.blockSignals(True)
        self.category_filter.clear()
        self.category_filter.addItem("Toutes les catégories", None)
        for cat in ProductController.list_categories():
            self.category_filter.addItem(cat["name"], cat["id"])
        if current_filter:
            index = self.category_filter.findData(current_filter)
            if index >= 0:
                self.category_filter.setCurrentIndex(index)
        self.category_filter.blockSignals(False)

        products = ProductController.list_products(
            search=self._search, category_id=self.category_filter.currentData()
        )
        self.table.setRowCount(len(products))
        for row, product in enumerate(products):
            margin = product["sale_price"] - product["purchase_price"]
            in_stock = product["stock_qty"] > 0
            low = 0 < product["stock_qty"] <= product["alert_threshold"]
            status = "En stock" if in_stock else "Rupture"
            if low:
                status = "Stock faible"

            values = [
                product["name"],
                product["sku"] or "—",
                product["category"] or "—",
                format_money(product["purchase_price"], self.currency),
                format_money(product["sale_price"], self.currency),
                format_qty(product["stock_qty"]),
                format_money(margin, self.currency),
                status,
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col in (3, 4, 5, 6):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, product["id"])
                if col == 7:
                    if not in_stock:
                        item.setForeground(QColor("#FF3B30"))
                    elif low:
                        item.setForeground(QColor("#FF9500"))
                    else:
                        item.setForeground(QColor("#28A745"))
                if col == 5 and not in_stock:
                    item.setForeground(QColor("#FF3B30"))
                self.table.setItem(row, col, item)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _add(self) -> None:
        """Ouvre le formulaire de création."""
        dialog = ProductDialog(self)
        if dialog.exec():
            try:
                ProductController.create_product(dialog.data(), self.user)
            except ValueError as exc:
                self.show_error(str(exc))
            self.refresh()

    def _edit(self) -> None:
        """Ouvre le formulaire de modification du produit sélectionné."""
        product_id = self.selected_row_id(self.table)
        if product_id is None:
            self.show_error("Sélectionnez un produit à modifier.")
            return
        product = ProductController.get_product(product_id)
        if product is None:
            self.show_error("Produit introuvable.")
            return
        dialog = ProductDialog(self, product)
        if dialog.exec():
            try:
                ProductController.update_product(product_id, dialog.data(), self.user)
            except ValueError as exc:
                self.show_error(str(exc))
            self.refresh()

    def _delete(self) -> None:
        """Supprime le produit sélectionné après confirmation."""
        product_id = self.selected_row_id(self.table)
        if product_id is None:
            self.show_error("Sélectionnez un produit à supprimer.")
            return
        if not self.confirm("Supprimer ce produit ?\n"
                            "(S'il apparaît dans des factures, il sera archivé.)"):
            return
        try:
            ProductController.delete_product(product_id, self.user)
        except ValueError as exc:
            self.show_error(str(exc))
        self.refresh()
