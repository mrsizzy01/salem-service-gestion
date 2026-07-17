"""Contrôleur Dépenses de l'entreprise."""

from __future__ import annotations

from datetime import datetime

from app.models.database import get_session
from app.models.entities import Expense, User
from app.services.audit_service import log_action
from app.utils.helpers import round2

# Catégories de dépenses proposées par défaut (liste libre).
EXPENSE_CATEGORIES = ["Loyer", "Salaires", "Transport", "Fournitures",
                      "Électricité/Eau", "Communication", "Divers"]


class ExpenseController:
    """CRUD des dépenses."""

    @staticmethod
    def list_expenses(start: datetime | None = None, end: datetime | None = None,
                      search: str = "") -> list[dict]:
        """Liste les dépenses sur une période, de la plus récente à la plus ancienne."""
        with get_session() as session:
            query = session.query(Expense)
            if start:
                query = query.filter(Expense.spent_at >= start)
            if end:
                query = query.filter(Expense.spent_at <= end)
            if search.strip():
                pattern = f"%{search.strip()}%"
                query = query.filter(Expense.label.ilike(pattern) | Expense.category.ilike(pattern))
            rows = query.order_by(Expense.spent_at.desc()).all()
            return [
                {"id": e.id, "label": e.label, "category": e.category,
                 "amount": e.amount, "spent_at": e.spent_at, "note": e.note}
                for e in rows
            ]

    @staticmethod
    def save_expense(data: dict, user: User | None = None,
                     expense_id: int | None = None) -> dict:
        """Crée ou met à jour une dépense."""
        if not data.get("label", "").strip():
            raise ValueError("Le libellé de la dépense est obligatoire.")
        amount = round2(data.get("amount", 0))
        if amount <= 0:
            raise ValueError("Le montant doit être supérieur à zéro.")
        with get_session() as session:
            if expense_id:
                expense = session.get(Expense, expense_id)
                if expense is None:
                    raise ValueError("Dépense introuvable.")
                action = "Modification dépense"
            else:
                expense = Expense(user_id=user.id if user else None)
                session.add(expense)
                action = "Création dépense"
            expense.label = data["label"].strip()
            expense.category = data.get("category", "Divers")
            expense.amount = amount
            expense.spent_at = data.get("spent_at") or datetime.now()
            expense.note = data.get("note", "")
            session.commit()
            log_action(action, f"{expense.label} — {expense.amount:g}", user)
            return {"id": expense.id, "label": expense.label, "category": expense.category,
                    "amount": expense.amount, "spent_at": expense.spent_at, "note": expense.note}

    @staticmethod
    def delete_expense(expense_id: int, user: User | None = None) -> None:
        """Supprime une dépense."""
        with get_session() as session:
            expense = session.get(Expense, expense_id)
            if expense is None:
                raise ValueError("Dépense introuvable.")
            label = expense.label
            session.delete(expense)
            session.commit()
            log_action("Suppression dépense", label, user)
