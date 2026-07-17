"""Page Tableau de bord : indicateurs clés et graphiques."""

from __future__ import annotations

from datetime import datetime

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from app.controllers.report_controller import ReportController
from app.controllers.settings_controller import SettingsController
from app.utils.helpers import format_money
from app.views.pages.base_page import BasePage
from app.views.widgets import StatCard

# Couleurs des graphiques (harmonisées avec le thème).
ACCENT = "#0A84FF"
GREEN = "#30D158"
ORANGE = "#FF9F0A"
PURPLE = "#BF5AF2"
RED = "#FF453A"


class DashboardPage(BasePage):
    """Vue d'ensemble : ventes, chiffre d'affaires, stock, graphiques."""

    def __init__(self, user, parent=None):
        super().__init__("Tableau de bord", user, parent)
        self.company = SettingsController.get_company()
        self.currency = self.company.get("currency", "FCFA")

        btn = self.add_action("🔄 Actualiser", self.refresh, primary=True)
        btn.setMinimumHeight(36)

        # ---- Cartes d'indicateurs ----------------------------------
        cards_row = QHBoxLayout()
        cards_row.setSpacing(12)
        self.card_today = StatCard("Factures du jour", "invoice", ACCENT)
        self.card_revenue = StatCard("C.A. du jour", "money", GREEN)
        self.card_month = StatCard("C.A. du mois", "reports", PURPLE)
        self.card_stock = StatCard("Produits en stock", "box", ORANGE)
        self.card_out = StatCard("En rupture", "warning", RED)
        for card in (self.card_today, self.card_revenue, self.card_month,
                     self.card_stock, self.card_out):
            cards_row.addWidget(card)
        self.main_layout.addLayout(cards_row)

        # ---- Graphiques --------------------------------------------
        charts_row = QHBoxLayout()
        charts_row.setSpacing(12)

        self.days_canvas, self.days_ax = self._make_chart("Ventes — 14 derniers jours")
        self.category_canvas, self.category_ax = self._make_chart("C.A. par catégorie — 30 jours")
        charts_row.addWidget(self._wrap(self.days_canvas), 3)
        charts_row.addWidget(self._wrap(self.category_canvas), 2)
        self.main_layout.addLayout(charts_row, 1)

        charts_row2 = QHBoxLayout()
        charts_row2.setSpacing(12)
        self.month_canvas, self.month_ax = self._make_chart(f"C.A. mensuel — {datetime.now().year}")
        charts_row2.addWidget(self._wrap(self.month_canvas), 3)

        # Dernières factures.
        recent_frame, recent_layout = self._panel("Dernières factures")
        self.recent_table = self.make_table(["N°", "Date", "Client", "Total"])
        from PySide6.QtWidgets import QHeaderView

        recent_header = self.recent_table.horizontalHeader()
        for col in (0, 1, 3):
            recent_header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        recent_header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        recent_layout.addWidget(self.recent_table)
        charts_row2.addWidget(recent_frame, 2)
        self.main_layout.addLayout(charts_row2, 1)

        self.refresh()

    # ------------------------------------------------------------------
    # Construction des graphiques
    # ------------------------------------------------------------------
    def _make_chart(self, title: str):
        """Crée un canvas matplotlib intégré dans une carte."""
        figure = Figure(figsize=(4, 2.6), tight_layout=True)
        figure.patch.set_alpha(0.0)
        canvas = FigureCanvasQTAgg(figure)
        ax = figure.add_subplot(111)
        ax.set_title(title, fontsize=10, fontweight="bold")
        return canvas, ax

    def _wrap(self, canvas) -> QFrame:
        """Encapsule un canvas dans une carte."""
        frame = QFrame()
        frame.setObjectName("Card")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.addWidget(canvas)
        return frame

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

    def _style_ax(self, ax) -> None:
        """Applique un style épuré aux axes."""
        ax.set_facecolor("none")
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        ax.spines["left"].set_color("#C7C7CC")
        ax.spines["bottom"].set_color("#C7C7CC")
        ax.tick_params(colors="#8E8E93", labelsize=8)
        ax.grid(axis="y", color="#E5E5EA", linewidth=0.6)

    # ------------------------------------------------------------------
    # Données
    # ------------------------------------------------------------------
    def refresh(self) -> None:
        """Recharge indicateurs et graphiques."""
        self.company = SettingsController.get_company()
        self.currency = self.company.get("currency", "FCFA")

        cards = ReportController.dashboard_cards()
        self.card_today.set_value(str(cards["today_count"]))
        self.card_revenue.set_value(format_money(cards["today_total"], self.currency))
        self.card_month.set_value(format_money(cards["month_total"], self.currency))
        self.card_stock.set_value(str(cards["in_stock"]))
        self.card_out.set_value(str(cards["out_stock"]))

        # Graphique des ventes quotidiennes.
        data = ReportController.sales_last_days(14)
        self.days_ax.clear()
        self.days_ax.set_title("Ventes — 14 derniers jours", fontsize=10, fontweight="bold")
        labels = [d for d, _ in data]
        values = [v for _, v in data]
        self.days_ax.bar(labels, values, color=ACCENT, width=0.65)
        self.days_ax.set_xticks(range(0, len(labels), 2))
        self.days_ax.set_xticklabels([labels[i] for i in range(0, len(labels), 2)],
                                     rotation=45, ha="right")
        self._style_ax(self.days_ax)
        self.days_canvas.draw_idle()

        # Répartition par catégorie.
        cat_data = ReportController.sales_by_category(30)
        self.category_ax.clear()
        self.category_ax.set_title("C.A. par catégorie — 30 jours", fontsize=10, fontweight="bold")
        if cat_data:
            names = [n for n, _ in cat_data]
            amounts = [v for _, v in cat_data]
            colors = [ACCENT, GREEN, ORANGE, PURPLE, RED, "#64D2FF", "#FFD60A"]
            self.category_ax.pie(
                amounts, labels=names, autopct="%1.0f%%",
                colors=colors[: len(amounts)], textprops={"fontsize": 8, "color": "#8E8E93"},
                wedgeprops={"linewidth": 1, "edgecolor": "white"},
            )
        else:
            self.category_ax.text(0.5, 0.5, "Aucune vente catégorisée",
                                  ha="center", va="center", color="#8E8E93", fontsize=9)
            self.category_ax.axis("off")
        self.category_canvas.draw_idle()

        # Ventes mensuelles.
        month_data = ReportController.sales_by_month(datetime.now().year)
        self.month_ax.clear()
        self.month_ax.set_title(f"C.A. mensuel — {datetime.now().year}",
                                fontsize=10, fontweight="bold")
        mlabels = [m for m, _ in month_data]
        mvalues = [v for _, v in month_data]
        self.month_ax.plot(mlabels, mvalues, color=ACCENT, marker="o",
                           linewidth=2, markersize=4)
        self.month_ax.fill_between(mlabels, mvalues, color=ACCENT, alpha=0.12)
        self._style_ax(self.month_ax)
        self.month_canvas.draw_idle()

        # Dernières factures.
        recent = ReportController.recent_sales(8)
        self.recent_table.setRowCount(len(recent))
        for row, sale in enumerate(recent):
            values = [
                sale["number"],
                sale["created_at"].strftime("%d/%m/%Y %H:%M"),
                sale["customer_name"] or "Client comptant",
                format_money(sale["total"], self.currency),
            ]
            for col, value in enumerate(values):
                from PySide6.QtWidgets import QTableWidgetItem

                item = QTableWidgetItem(value)
                if col == 3:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if sale["status"] == "annulée":
                    item.setForeground(Qt.GlobalColor.gray)
                self.recent_table.setItem(row, col, item)
