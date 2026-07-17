"""Page Crédits Clients : suivi des dettes et échéanciers."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QDoubleSpinBox, QFormLayout, QLineEdit, QMessageBox, QTableWidgetItem, QVBoxLayout, QWidget

from app.controllers.customer_controller import CustomerController
from app.controllers.debt_controller import DebtController
from app.controllers.settings_controller import SettingsController
from app.utils.helpers import format_money
from app.views.pages.base_page import BasePage


class DebtsPage(BasePage):
    """Gestion des dettes clients (crédit accordé)."""

    def __init__(self, user, parent=None):
        super().__init__("Crédit Clients", user, parent)
        self.currency = SettingsController.get_company().get("currency", "CDF")

        self.add_action("＋ Nouvelle dette", self._add, primary=True)
        self.add_action("💰 Paiement", self._pay)
        self.add_action("🔄 Actualiser", self.refresh)

        # Résumé
        self.summary_label = QLabel()
        self.summary_label.setObjectName("muted")
        self.summary_label.setStyleSheet("font-size: 14px; padding: 10px;")
        self.main_layout.addWidget(self.summary_label)

        self.table = self.make_table([
            "Client", "Montant", "Payé", "Reste", "Échéance", "Statut", "Notes"
        ])
        self.main_layout.addWidget(self.table)
        self.refresh()

    def refresh(self) -> None:
        debts = DebtController.list_debts()
        summary = DebtController.get_debt_summary()
        self.summary_label.setText(
            f"💳 Total crédits : <b>{format_money(summary['total'], self.currency)}</b>  |  "
            f"💰 Payé : <b>{format_money(summary['paid'], self.currency)}</b>  |  "
            f"📋 Restant : <b>{format_money(summary['remaining'], self.currency)}</b>  |  "
            f"⚠️ En retard : <b>{summary['overdue_count']}</b>"
        )

        self.table.setRowCount(len(debts))
        for row, debt in enumerate(debts):
            values = [
                debt["customer"],
                format_money(debt["amount"], self.currency),
                format_money(debt["paid"], self.currency),
                format_money(debt["remaining"], self.currency),
                debt["due_date"].strftime("%d/%m/%Y") if debt["due_date"] else "—",
                debt["status"].upper(),
                debt["notes"] or "—",
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col in (1, 2, 3):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, debt["id"])
                if col == 5:
                    color = "#FF3B30" if debt["status"] == "retard" else "#28A745" if debt["status"] == "payé" else "#FF9500"
                    item.setForeground(QColor(color))
                    item.setFont(item.font())
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                self.table.setItem(row, col, item)

    def _add(self) -> None:
        self.show_error("Création de dette : utilisez la facturation avec paiement partiel.")

    def _pay(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            self.show_error("Sélectionnez une dette à payer.")
            return
        debt_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        if debt_id is None:
            self.show_error("Impossible de trouver l'identifiant de la dette.")
            return

        from PySide6.QtWidgets import QDialog, QDialogButtonBox
        dialog = QDialog(self)
        dialog.setWindowTitle("Paiement de dette")
        dialog.setMinimumWidth(350)

        layout = QVBoxLayout(dialog)
        form = QFormLayout()

        amount_spin = QDoubleSpinBox()
        amount_spin.setRange(0, 999999999)
        amount_spin.setValue(0)
        amount_spin.setDecimals(0 if self.currency == "CDF" else 2)

        notes_edit = QLineEdit()
        notes_edit.setPlaceholderText("Notes (facultatif)")

        form.addRow("Montant", amount_spin)
        form.addRow("Notes", notes_edit)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec():
            try:
                DebtController.add_payment(debt_id, amount_spin.value(), notes_edit.text(), self.user)
                self.refresh()
                QMessageBox.information(self, "Paiement", "Paiement enregistré avec succès.")
            except ValueError as exc:
                self.show_error(str(exc))
