"""Page Stock : entrées, sorties, inventaire et historique."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFileDialog, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget

from app.config import MOVE_IN, reports_dir
from app.controllers.product_controller import ProductController
from app.controllers.settings_controller import SettingsController
from app.controllers.stock_controller import StockController
from app.services.excel_service import export_products
from app.utils.helpers import format_money, format_qty
from app.views.dialogs import StockAdjustDialog, StockMovementDialog
from app.views.pages.base_page import BasePage


class StockPage(BasePage):
    """Gestion des mouvements et de l'inventaire."""

    def __init__(self, user, parent=None):
        super().__init__("Stock", user, parent)
        self.currency = SettingsController.get_company().get("currency", "FCFA")

        btn = self.add_action("⬇ Entrée", self._entry, primary=True)
        btn.setMinimumHeight(36)
        self.add_action("⬆ Sortie", self._exit).setMinimumHeight(34)
        self.add_action("⚖ Ajustement", self._adjust).setMinimumHeight(34)
        self.add_action("📊 Exporter Excel", self._export).setMinimumHeight(34)

        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.tabs)

        # ---- Onglet Inventaire --------------------------------------
        inventory_widget = QWidget()
        inventory_layout = QVBoxLayout(inventory_widget)
        inventory_layout.setContentsMargins(8, 8, 8, 8)
        self.inventory_table = self.make_table(
            ["Produit", "Catégorie", "Stock", "Seuil", "Valeur du stock", "Statut"]
        )
        inventory_layout.addWidget(self.inventory_table)
        self.tabs.addTab(inventory_widget, "Inventaire")

        # ---- Onglet Historique --------------------------------------
        history_widget = QWidget()
        history_layout = QVBoxLayout(history_widget)
        history_layout.setContentsMargins(8, 8, 8, 8)
        self.history_table = self.make_table(
            ["Date", "Produit", "Type", "Quantité", "Stock après", "Motif", "Référence"]
        )
        history_layout.addWidget(self.history_table)
        self.tabs.addTab(history_widget, "Historique des mouvements")

        self.refresh()

    # ------------------------------------------------------------------
    # Données
    # ------------------------------------------------------------------
    def set_search(self, text: str) -> None:
        self._search = text
        self.refresh()

    def refresh(self) -> None:
        """Recharge inventaire et historique."""
        # Inventaire.
        inventory = StockController.inventory()
        if self._search.strip():
            needle = self._search.strip().lower()
            inventory = [p for p in inventory if needle in p["name"].lower()]
        self.inventory_table.setRowCount(len(inventory))
        total_value = 0.0
        for row, product in enumerate(inventory):
            total_value += product["stock_value"]
            out = product["stock_qty"] <= 0
            low = 0 < product["stock_qty"] <= product["alert_threshold"]
            status = "Rupture" if out else ("Stock faible" if low else "En stock")
            values = [
                product["name"], product["category"] or "—",
                format_qty(product["stock_qty"]), format_qty(product["alert_threshold"]),
                format_money(product["stock_value"], self.currency), status,
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col in (2, 3, 4):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, product["id"])
                if col in (2, 5):
                    if out:
                        item.setForeground(QColor("#FF3B30"))
                    elif low:
                        item.setForeground(QColor("#FF9500"))
                    elif col == 5:
                        item.setForeground(QColor("#28A745"))
                self.inventory_table.setItem(row, col, item)
        self.tabs.setTabText(0, f"Inventaire — valeur {format_money(total_value, self.currency)}")

        # Historique.
        history = StockController.history(limit=300)
        if self._search.strip():
            needle = self._search.strip().lower()
            history = [m for m in history if needle in m["product"].lower()]
        self.history_table.setRowCount(len(history))
        for row, move in enumerate(history):
            sign = "+" if move["move_type"] == MOVE_IN else ("±" if move["move_type"] == "ajustement" else "−")
            values = [
                move["created_at"].strftime("%d/%m/%Y %H:%M"),
                move["product"], move["move_type"].capitalize(),
                f"{sign}{format_qty(move['quantity'])}",
                format_qty(move["stock_after"]),
                move["reason"] or "—", move["reference"] or "—",
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col in (3, 4):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if col == 3:
                    item.setForeground(QColor("#28A745" if sign == "+" else "#FF3B30" if sign == "−" else "#FF9500"))
                self.history_table.setItem(row, col, item)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _products(self) -> list[dict]:
        """Produits actifs pour les listes déroulantes."""
        return ProductController.list_products()

    def _entry(self) -> None:
        dialog = StockMovementDialog(MOVE_IN, self._products(), self)
        if dialog.exec():
            data = dialog.data()
            try:
                StockController.add_entry(data["product_id"], data["quantity"],
                                          data["reason"], self.user)
            except ValueError as exc:
                self.show_error(str(exc))
            self.refresh()

    def _exit(self) -> None:
        dialog = StockMovementDialog("sortie", self._products(), self)
        if dialog.exec():
            data = dialog.data()
            try:
                StockController.add_exit(data["product_id"], data["quantity"],
                                         data["reason"], self.user)
            except ValueError as exc:
                self.show_error(str(exc))
            self.refresh()

    def _adjust(self) -> None:
        product_id = self.selected_row_id(self.inventory_table)
        dialog = StockAdjustDialog(self._products(), self, product_id)
        if dialog.exec():
            data = dialog.data()
            try:
                StockController.adjust(data["product_id"], data["quantity"],
                                       data["reason"], self.user)
            except ValueError as exc:
                self.show_error(str(exc))
            self.refresh()

    def _export(self) -> None:
        """Exporte l'inventaire courant en Excel."""
        default = str(reports_dir() / "inventaire.xlsx")
        path, _ = QFileDialog.getSaveFileName(
            self, "Exporter l'inventaire", default, "Excel (*.xlsx)"
        )
        if not path:
            return
        if not path.endswith(".xlsx"):
            path += ".xlsx"
        products = ProductController.list_products()
        export_products(products, Path(path))
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.information(self, "Export", f"Inventaire exporté :\n{path}")
