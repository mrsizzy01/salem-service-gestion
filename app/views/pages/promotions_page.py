"""Page Promotions : remises et offres commerciales."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QComboBox, QDateTimeEdit, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QTableWidgetItem, QVBoxLayout, QWidget

from app.controllers.product_controller import ProductController
from app.controllers.promotion_controller import PromotionController
from app.views.pages.base_page import BasePage


class PromotionsPage(BasePage):
    """Gestion des promotions commerciales."""

    def __init__(self, user, parent=None):
        super().__init__("Promotions", user, parent)

        self.add_action("＋ Nouvelle promotion", self._add, primary=True)
        self.add_action("🗑 Supprimer", self._delete, danger=True)
        self.add_action("Actualiser", self.refresh)

        self.table = self.make_table([
            "Libellé", "Type", "Valeur", "Produit/Catégorie", "Début", "Fin", "Active"
        ])
        self.main_layout.addWidget(self.table)
        self.refresh()

    def refresh(self) -> None:
        promos = PromotionController.list_promotions(active_only=False)
        self.table.setRowCount(len(promos))
        for row, promo in enumerate(promos):
            type_label = {
                "remise_pct": "Remise %",
                "remise_montant": "Remise fixe",
                "2eme_moitie": "2ème à -50%",
                "pack": "Pack"
            }.get(promo["type"], promo["type"])

            value_str = f"{promo['value']:.0f}%" if promo["type"] == "remise_pct" else f"{promo['value']:.0f} CDF"

            values = [
                promo["label"],
                type_label,
                value_str,
                promo["product"] or "Tous les produits",
                promo["start_date"].strftime("%d/%m/%Y") if promo["start_date"] else "—",
                promo["end_date"].strftime("%d/%m/%Y") if promo["end_date"] else "—",
                "✓ Oui" if promo["active"] else "✗ Non",
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 6:
                    item.setForeground(QColor("#28A745" if promo["active"] else "#8E8E93"))
                self.table.setItem(row, col, item)

    def _add(self) -> None:
        from PySide6.QtWidgets import QDialog, QDialogButtonBox

        dialog = QDialog(self)
        dialog.setWindowTitle("Nouvelle promotion")
        dialog.setMinimumWidth(450)

        layout = QVBoxLayout(dialog)
        form = QFormLayout()

        label_edit = QLineEdit()
        label_edit.setPlaceholderText("Ex: Soldes été 2024")

        type_combo = QComboBox()
        type_combo.addItem("Remise en pourcentage", "remise_pct")
        type_combo.addItem("Remise en montant", "remise_montant")
        type_combo.addItem("2ème article à -50%", "2eme_moitie")
        type_combo.addItem("Pack promotionnel", "pack")

        value_spin = QDoubleSpinBox()
        value_spin.setRange(0, 999999)
        value_spin.setValue(10)

        product_combo = QComboBox()
        product_combo.addItem("Tous les produits", None)
        for p in ProductController.list_products():
            product_combo.addItem(p["name"], p["id"])

        form.addRow("Libellé *", label_edit)
        form.addRow("Type", type_combo)
        form.addRow("Valeur", value_spin)
        form.addRow("Produit", product_combo)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec():
            try:
                PromotionController.create_promotion({
                    "label": label_edit.text(),
                    "type": type_combo.currentData(),
                    "value": value_spin.value(),
                    "product_id": product_combo.currentData(),
                }, self.user)
                self.refresh()
            except ValueError as exc:
                self.show_error(str(exc))

    def _delete(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            self.show_error("Sélectionnez une promotion à supprimer.")
            return
        promo_name = self.table.item(row, 0).text()
        if not self.confirm(f"Supprimer la promotion "{promo_name}" ?"):
            return
        # Note: la suppression nécessite l'ID - à implémenter avec les données
        self.refresh()
