"""Contrôleur Rapports et statistiques du tableau de bord."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy import func

from app.config import SALE_VALIDATED
from app.models.database import get_session
from app.models.entities import Category, Expense, Product, Sale, SaleItem
from app.utils.helpers import format_money, format_qty


class ReportController:
    """Agrégations pour les rapports périodiques et le tableau de bord."""

    # ------------------------------------------------------------------
    # Rapport d'activité sur une période
    # ------------------------------------------------------------------
    @staticmethod
    def build_report(start: datetime, end: datetime, title: str,
                     period_label: str, currency: str = "FCFA") -> dict:
        """Construit les données d'un rapport (UI, PDF et Excel).

        :return: dict « title, period_label, totals{…}, summary,
                 sales, top_products » — les listes ``summary``, ``sales``
                 et ``top_products`` sont pré-formatées pour l'affichage.
        """
        with get_session() as session:
            sales = (
                session.query(Sale)
                .filter(Sale.created_at >= start, Sale.created_at <= end,
                        Sale.status == SALE_VALIDATED)
                .order_by(Sale.created_at)
                .all()
            )
            expenses_total = (
                session.query(func.coalesce(func.sum(Expense.amount), 0.0))
                .filter(Expense.spent_at >= start, Expense.spent_at <= end)
                .scalar()
            )
            items = (
                session.query(SaleItem)
                .join(Sale)
                .filter(Sale.created_at >= start, Sale.created_at <= end,
                        Sale.status == SALE_VALIDATED)
                .all()
            )

        total_sales = round(sum(s.total for s in sales), 2)
        total_paid = round(sum(s.amount_paid for s in sales), 2)
        total_remaining = round(sum(s.remaining for s in sales), 2)
        # Marge brute : (prix de vente − coût d'achat) par ligne connue ;
        # les produits manuels (coût inconnu = 0) comptent pour leur marge totale.
        gross_profit = round(
            sum((i.unit_price - i.unit_cost) * i.quantity for i in items), 2
        )
        expenses_total = round(float(expenses_total), 2)
        net_profit = round(gross_profit - expenses_total, 2)

        totals = {
            "count": len(sales),
            "total": total_sales,
            "paid": total_paid,
            "remaining": total_remaining,
            "expenses": expenses_total,
            "gross_profit": gross_profit,
            "net_profit": net_profit,
        }

        summary = [
            ["Nombre de ventes", str(len(sales))],
            ["Chiffre d'affaires", format_money(total_sales, currency)],
            ["Montants encaissés", format_money(total_paid, currency)],
            ["Restes à encaisser", format_money(total_remaining, currency)],
            ["Marge brute estimée", format_money(gross_profit, currency)],
            ["Dépenses", format_money(expenses_total, currency)],
            ["Résultat net estimé", format_money(net_profit, currency)],
        ]

        sales_rows = [
            [
                s.number,
                s.created_at.strftime("%d/%m/%Y %H:%M"),
                s.customer_name or "Client comptant",
                format_money(s.total, currency),
                format_money(s.amount_paid, currency),
                format_money(s.remaining, currency),
            ]
            for s in sales
        ]

        # Meilleurs produits (par montant).
        by_product: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0])
        for i in items:
            by_product[i.product_name][0] += i.quantity
            by_product[i.product_name][1] += i.line_total
        top = sorted(by_product.items(), key=lambda kv: kv[1][1], reverse=True)[:10]
        top_rows = [
            [name, format_qty(values[0]), format_money(values[1], currency)]
            for name, values in top
        ]

        return {
            "title": title,
            "period_label": period_label,
            "totals": totals,
            "summary": summary,
            "sales": sales_rows,
            "top_products": top_rows,
        }

    # ------------------------------------------------------------------
    # Tableau de bord
    # ------------------------------------------------------------------
    @staticmethod
    def dashboard_cards() -> dict:
        """Indicateurs des cartes du tableau de bord."""
        now = datetime.now()
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        with get_session() as session:
            today_count, today_total = (
                session.query(func.count(Sale.id), func.coalesce(func.sum(Sale.total), 0.0))
                .filter(Sale.created_at >= day_start, Sale.status == SALE_VALIDATED)
                .one()
            )
            month_total = (
                session.query(func.coalesce(func.sum(Sale.total), 0.0))
                .filter(Sale.created_at >= month_start, Sale.status == SALE_VALIDATED)
                .scalar()
            )
            all_count = (
                session.query(func.count(Sale.id))
                .filter(Sale.status == SALE_VALIDATED)
                .scalar()
            )
            base = session.query(Product).filter(Product.active.is_(True))
            in_stock = base.filter(Product.stock_qty > 0).count()
            out_stock = base.filter(Product.stock_qty <= 0).count()
        return {
            "today_count": int(today_count),
            "today_total": float(today_total),
            "month_total": float(month_total),
            "all_count": int(all_count),
            "in_stock": int(in_stock),
            "out_stock": int(out_stock),
        }

    @staticmethod
    def sales_last_days(days: int = 14) -> list[tuple[str, float]]:
        """Chiffre d'affaires quotidien des ``days`` derniers jours."""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        start = today - timedelta(days=days - 1)
        with get_session() as session:
            rows = (
                session.query(Sale.created_at, Sale.total)
                .filter(Sale.created_at >= start, Sale.status == SALE_VALIDATED)
                .all()
            )
        per_day: dict[str, float] = defaultdict(float)
        for created, total in rows:
            per_day[created.strftime("%d/%m")] += total
        result = []
        for offset in range(days):
            label = (start + timedelta(days=offset)).strftime("%d/%m")
            result.append((label, round(per_day.get(label, 0.0), 2)))
        return result

    @staticmethod
    def sales_by_month(year: int) -> list[tuple[str, float]]:
        """Chiffre d'affaires mensuel d'une année (12 points)."""
        with get_session() as session:
            rows = (
                session.query(Sale.created_at, Sale.total)
                .filter(Sale.created_at >= datetime(year, 1, 1),
                        Sale.created_at <= datetime(year, 12, 31, 23, 59, 59),
                        Sale.status == SALE_VALIDATED)
                .all()
            )
        per_month: dict[int, float] = defaultdict(float)
        for created, total in rows:
            per_month[created.month] += total
        labels = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin",
                  "Juil", "Août", "Sep", "Oct", "Nov", "Déc"]
        return [(labels[m - 1], round(per_month.get(m, 0.0), 2)) for m in range(1, 13)]

    @staticmethod
    def sales_by_category(days: int = 30) -> list[tuple[str, float]]:
        """Répartition du chiffre d'affaires par catégorie (``days`` jours)."""
        start = datetime.now() - timedelta(days=days)
        with get_session() as session:
            rows = (
                session.query(Category.name, func.sum(SaleItem.line_total))
                .select_from(SaleItem)
                .join(Sale, SaleItem.sale_id == Sale.id)
                .join(Product, SaleItem.product_id == Product.id)
                .join(Category, Product.category_id == Category.id)
                .filter(Sale.created_at >= start, Sale.status == SALE_VALIDATED)
                .group_by(Category.name)
                .all()
            )
        return [(name, round(float(total), 2)) for name, total in rows if total]

    @staticmethod
    def recent_sales(limit: int = 8) -> list[dict]:
        """Dernières factures (pour le tableau du tableau de bord)."""
        with get_session() as session:
            rows = (
                session.query(Sale)
                .order_by(Sale.created_at.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "number": s.number,
                    "created_at": s.created_at,
                    "customer_name": s.customer_name,
                    "total": s.total,
                    "status": s.status,
                }
                for s in rows
            ]

    @staticmethod
    def low_stock_products(limit: int = 8) -> list[dict]:
        """Produits en rupture ou sous le seuil d'alerte."""
        with get_session() as session:
            rows = (
                session.query(Product)
                .filter(Product.active.is_(True), Product.stock_qty <= Product.alert_threshold)
                .order_by(Product.stock_qty)
                .limit(limit)
                .all()
            )
            return [{"name": p.name, "stock_qty": p.stock_qty,
                     "alert_threshold": p.alert_threshold} for p in rows]
