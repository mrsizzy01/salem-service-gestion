"""Page Rapports : quotidiens, hebdomadaires, mensuels, annuels.

Export possible en PDF (ReportLab) et en Excel (OpenPyXL).
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.config import reports_dir
from app.controllers.report_controller import ReportController
from app.controllers.settings_controller import SettingsController
from app.services.excel_service import export_report
from app.services.pdf_service import generate_report_pdf
from app.utils.helpers import day_range, format_money, month_range, week_range, year_range
from app.views.pages.base_page import BasePage
from app.views.widgets import StatCard


class ReportsPage(BasePage):
    """Rapports d'activité périodiques."""

    def __init__(self, user, parent=None):
        super().__init__("Rapports", user, parent)
        self.company = SettingsController.get_company()
        self.currency = self.company.get("currency", "FCFA")
        self._report: dict | None = None

        # ---- Sélecteurs de période -------------------------------------
        period_row = QHBoxLayout()
        period_row.setSpacing(8)
        self.period_combo = QComboBox()
        self.period_combo.addItem("Quotidien", "daily")
        self.period_combo.addItem("Hebdomadaire", "weekly")
        self.period_combo.addItem("Mensuel", "monthly")
        self.period_combo.addItem("Annuel", "yearly")
        self.period_combo.addItem("Personnalisé", "custom")
        self.period_combo.setCurrentIndex(2)  # mensuel par défaut
        self.period_combo.currentIndexChanged.connect(self._on_period_changed)

        self.date_from = QDateEdit(QDate.currentDate())
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("dd/MM/yyyy")
        self.date_to = QDateEdit(QDate.currentDate())
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("dd/MM/yyyy")
        for widget in (self.date_from, self.date_to):
            widget.setVisible(False)
            widget.dateChanged.connect(lambda _d: self.refresh())

        period_row.addWidget(QLabel("Période :"))
        period_row.addWidget(self.period_combo)
        period_row.addWidget(self.date_from)
        period_row.addWidget(QLabel("au"))
        period_row.addWidget(self.date_to)
        period_row.addStretch()
        self.main_layout.addLayout(period_row)

        btn = self.add_action("📊 Générer", self.refresh, primary=True)
        btn.setMinimumHeight(36)
        self.add_action("📄 Exporter PDF", self._export_pdf).setMinimumHeight(34)
        self.add_action("📊 Exporter Excel", self._export_excel).setMinimumHeight(34)

        # ---- Cartes de synthèse -----------------------------------------
        cards_row = QHBoxLayout()
        cards_row.setSpacing(12)
        self.card_count = StatCard("Ventes", "invoice", "#0A84FF")
        self.card_total = StatCard("Chiffre d'affaires", "money", "#30D158")
        self.card_expenses = StatCard("Dépenses", "expenses", "#FF9F0A")
        self.card_net = StatCard("Résultat net estimé", "reports", "#BF5AF2")
        for card in (self.card_count, self.card_total, self.card_expenses, self.card_net):
            cards_row.addWidget(card)
        self.main_layout.addLayout(cards_row)

        # ---- Tableaux ----------------------------------------------------
        tables_row = QHBoxLayout()
        tables_row.setSpacing(12)

        sales_frame, sales_layout = self._panel("Détail des ventes")
        self.sales_table = self.make_table(["N°", "Date", "Client", "Total", "Payé", "Reste"])
        sales_layout.addWidget(self.sales_table)
        tables_row.addWidget(sales_frame, 3)

        top_frame, top_layout = self._panel("Meilleurs produits")
        self.top_table = self.make_table(["Produit", "Quantité", "Montant"])
        top_layout.addWidget(self.top_table)
        tables_row.addWidget(top_frame, 2)

        tables_widget = QWidget()
        tables_widget.setLayout(tables_row)
        tables_row.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(tables_widget, 1)

        self.refresh()

    # ------------------------------------------------------------------
    # Période
    # ------------------------------------------------------------------
    def _panel(self, title: str):
        """Crée une carte avec un titre de section."""
        frame = QFrame()
        frame.setObjectName("Card")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 12, 14, 12)
        label = QLabel(title)
        label.setStyleSheet("font-weight: 700; font-size: 13px;")
        layout.addWidget(label)
        return frame, layout

    def _on_period_changed(self, _index: int) -> None:
        """Affiche les dates personnalisées uniquement si nécessaire."""
        custom = self.period_combo.currentData() == "custom"
        self.date_from.setVisible(custom)
        self.date_to.setVisible(custom)
        self.refresh()

    def _compute_period(self) -> tuple[datetime, datetime, str, str]:
        """Retourne (début, fin, titre, libellé) de la période choisie."""
        kind = self.period_combo.currentData()
        today = date.today()
        if kind == "daily":
            start, end = day_range(today)
            return start, end, "Rapport quotidien", today.strftime("%d/%m/%Y")
        if kind == "weekly":
            start, end = week_range(today)
            label = f"Semaine du {start:%d/%m/%Y} au {end:%d/%m/%Y}"
            return start, end, "Rapport hebdomadaire", label
        if kind == "monthly":
            start, end = month_range(today.year, today.month)
            return start, end, "Rapport mensuel", today.strftime("%m/%Y")
        if kind == "yearly":
            start, end = year_range(today.year)
            return start, end, "Rapport annuel", str(today.year)
        # Personnalisé
        start = datetime.combine(self.date_from.date().toPython(), datetime.min.time())
        end = datetime.combine(self.date_to.date().toPython(), datetime.max.time())
        label = f"Du {start:%d/%m/%Y} au {end:%d/%m/%Y}"
        return start, end, "Rapport personnalisé", label

    # ------------------------------------------------------------------
    # Données
    # ------------------------------------------------------------------
    def refresh(self) -> None:
        """Génère le rapport de la période sélectionnée."""
        self.company = SettingsController.get_company()
        self.currency = self.company.get("currency", "FCFA")
        start, end, title, label = self._compute_period()
        if start > end:
            self.show_error("La date de début doit précéder la date de fin.")
            return
        self._report = ReportController.build_report(start, end, title, label, self.currency)

        totals = self._report["totals"]
        self.card_count.set_value(str(totals["count"]))
        self.card_total.set_value(format_money(totals["total"], self.currency))
        self.card_expenses.set_value(format_money(totals["expenses"], self.currency))
        self.card_net.set_value(format_money(totals["net_profit"], self.currency))

        self.sales_table.setRowCount(len(self._report["sales"]))
        for row, values in enumerate(self._report["sales"]):
            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if col >= 3:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.sales_table.setItem(row, col, item)

        self.top_table.setRowCount(len(self._report["top_products"]))
        for row, values in enumerate(self._report["top_products"]):
            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if col > 0:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.top_table.setItem(row, col, item)

    # ------------------------------------------------------------------
    # Exports
    # ------------------------------------------------------------------
    def _ask_path(self, suffix: str, filter_: str) -> str | None:
        """Demande un chemin de sauvegarde à l'utilisateur."""
        default = str(reports_dir() / f"rapport_{datetime.now():%Y%m%d_%H%M%S}.{suffix}")
        path, _ = QFileDialog.getSaveFileName(self, "Exporter le rapport", default, filter_)
        if path and not path.endswith(f".{suffix}"):
            path += f".{suffix}"
        return path or None

    def _export_pdf(self) -> None:
        if not self._report:
            self.refresh()
        path = self._ask_path("pdf", "PDF (*.pdf)")
        if not path:
            return
        generate_report_pdf(self._report, self.company, Path(path))
        QMessageBox.information(self, "Export PDF", f"Rapport exporté :\n{path}")

    def _export_excel(self) -> None:
        if not self._report:
            self.refresh()
        path = self._ask_path("xlsx", "Excel (*.xlsx)")
        if not path:
            return
        export_report(self._report, Path(path))
        QMessageBox.information(self, "Export Excel", f"Rapport exporté :\n{path}")
