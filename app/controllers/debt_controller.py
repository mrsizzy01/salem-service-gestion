"""Contrôleur Crédit Client : suivi des dettes et échéanciers."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func

from app.models.database import get_session
from app.models.entities import CustomerDebt, DebtPayment, Sale, User
from app.services.audit_service import log_action
from app.utils.helpers import format_money


class DebtController:
    """Gestion des dettes clients (crédit accordé)."""

    @staticmethod
    def list_debts(customer_id: int | None = None, status: str | None = None) -> list[dict]:
        """Liste les dettes, filtrées par client et/ou statut."""
        with get_session() as session:
            query = session.query(CustomerDebt)
            if customer_id:
                query = query.filter(CustomerDebt.customer_id == customer_id)
            if status:
                query = query.filter(CustomerDebt.status == status)
            rows = query.order_by(CustomerDebt.created_at.desc()).all()
            return [
                {
                    "id": d.id,
                    "customer_id": d.customer_id,
                    "customer": d.customer.name if d.customer else "Client comptant",
                    "amount": d.amount,
                    "paid": d.paid,
                    "remaining": d.remaining,
                    "due_date": d.due_date,
                    "status": d.status,
                    "notes": d.notes,
                    "created_at": d.created_at,
                }
                for d in rows
            ]

    @staticmethod
    def create_debt(sale_id: int, amount: float, due_days: int = 30,
                    notes: str = "", user: User | None = None) -> dict:
        """Crée une dette à partir d'une vente."""
        with get_session() as session:
            sale = session.get(Sale, sale_id)
            if sale is None:
                raise ValueError("Vente introuvable.")
            if not sale.customer_id:
                raise ValueError("Impossible de créer une dette sans client enregistré.")

            debt = CustomerDebt(
                customer_id=sale.customer_id,
                sale_id=sale_id,
                amount=amount,
                paid=0.0,
                remaining=amount,
                due_date=datetime.now() + timedelta(days=due_days),
                notes=notes,
            )
            session.add(debt)
            session.commit()
            log_action(
                "Création dette client",
                f"{debt.customer.name} — {format_money(amount, 'CDF')}",
                user
            )
            return {
                "id": debt.id,
                "amount": amount,
                "remaining": amount,
                "customer": debt.customer.name,
            }

    @staticmethod
    def add_payment(debt_id: int, amount: float, notes: str = "",
                    user: User | None = None) -> dict:
        """Enregistre un paiement partiel sur une dette."""
        if amount <= 0:
            raise ValueError("Le montant doit être supérieur à zéro.")
        with get_session() as session:
            debt = session.get(CustomerDebt, debt_id)
            if debt is None:
                raise ValueError("Dette introuvable.")
            if amount > debt.remaining:
                raise ValueError(f"Le montant dépasse le solde restant ({debt.remaining:.2f}).")

            payment = DebtPayment(
                debt_id=debt_id,
                amount=amount,
                notes=notes,
                user_id=user.id if user else None,
            )
            session.add(payment)

            debt.paid += amount
            debt.remaining -= amount
            if debt.remaining <= 0:
                debt.status = "payé"
            elif debt.due_date and debt.due_date < datetime.now():
                debt.status = "retard"
            else:
                debt.status = "actif"

            session.commit()
            log_action(
                "Paiement dette",
                f"{debt.customer.name} — {format_money(amount, 'CDF')}",
                user
            )
            return {"id": payment.id, "debt_remaining": debt.remaining}

    @staticmethod
    def get_debt_summary(customer_id: int | None = None) -> dict:
        """Retourne un résumé des dettes (total, payé, restant)."""
        with get_session() as session:
            query = session.query(CustomerDebt)
            if customer_id:
                query = query.filter(CustomerDebt.customer_id == customer_id)

            total = query.with_entities(func.coalesce(func.sum(CustomerDebt.amount), 0.0)).scalar()
            paid = query.with_entities(func.coalesce(func.sum(CustomerDebt.paid), 0.0)).scalar()
            remaining = query.with_entities(func.coalesce(func.sum(CustomerDebt.remaining), 0.0)).scalar()
            overdue = query.filter(CustomerDebt.status == "retard").count()

            return {
                "total": float(total),
                "paid": float(paid),
                "remaining": float(remaining),
                "overdue_count": int(overdue),
            }

    @staticmethod
    def get_customer_debts(customer_id: int) -> list[dict]:
        """Retourne toutes les dettes d'un client spécifique."""
        return DebtController.list_debts(customer_id=customer_id)
