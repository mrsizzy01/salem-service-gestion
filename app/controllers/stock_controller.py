"""Contrôleur Stock : entrées, sorties, ajustements et historique."""

from __future__ import annotations

from datetime import datetime

from app.config import MOVE_ADJUST, MOVE_IN, MOVE_OUT
from app.models.database import get_session
from app.models.entities import Product, StockMovement, User
from app.services.audit_service import log_action


class StockController:
    """Gestion des mouvements de stock.

    Chaque mouvement met à jour ``Product.stock_qty`` et crée une ligne
    d'historique ``StockMovement`` dans la même transaction.
    """

    @staticmethod
    def add_entry(product_id: int, quantity: float, reason: str = "",
                  user: User | None = None) -> None:
        """Enregistre une entrée de stock (approvisionnement)."""
        StockController._apply_movement(product_id, MOVE_IN, abs(float(quantity)),
                                        reason or "Approvisionnement", user)

    @staticmethod
    def add_exit(product_id: int, quantity: float, reason: str = "",
                 user: User | None = None) -> None:
        """Enregistre une sortie de stock (casse, usage interne…)."""
        StockController._apply_movement(product_id, MOVE_OUT, abs(float(quantity)),
                                        reason or "Sortie manuelle", user)

    @staticmethod
    def adjust(product_id: int, new_quantity: float, reason: str = "",
               user: User | None = None) -> None:
        """Ajuste le stock à une quantité exacte (inventaire physique)."""
        new_quantity = float(new_quantity)
        with get_session() as session:
            product = session.get(Product, product_id)
            if product is None:
                raise ValueError("Produit introuvable.")
            difference = new_quantity - product.stock_qty
            product.stock_qty = new_quantity
            movement = StockMovement(
                product_id=product_id,
                move_type=MOVE_ADJUST,
                quantity=abs(difference),
                stock_after=new_quantity,
                reason=reason or "Ajustement d'inventaire",
                user_id=user.id if user else None,
            )
            session.add(movement)
            session.commit()
            log_action(
                "Ajustement stock",
                f"{product.name} : {difference:+g} → stock {new_quantity:g}",
                user,
            )

    @staticmethod
    def history(product_id: int | None = None, limit: int = 500,
                start: datetime | None = None, end: datetime | None = None) -> list[dict]:
        """Retourne l'historique des mouvements, du plus récent au plus ancien."""
        with get_session() as session:
            query = session.query(StockMovement).join(Product)
            if product_id:
                query = query.filter(StockMovement.product_id == product_id)
            if start:
                query = query.filter(StockMovement.created_at >= start)
            if end:
                query = query.filter(StockMovement.created_at <= end)
            rows = query.order_by(StockMovement.created_at.desc()).limit(limit).all()
            return [
                {
                    "id": m.id,
                    "product": m.product.name,
                    "move_type": m.move_type,
                    "quantity": m.quantity,
                    "stock_after": m.stock_after,
                    "reason": m.reason,
                    "reference": m.reference,
                    "created_at": m.created_at,
                }
                for m in rows
            ]

    @staticmethod
    def inventory() -> list[dict]:
        """État du stock de tous les produits actifs (pour l'inventaire)."""
        with get_session() as session:
            products = session.query(Product).filter(Product.active.is_(True)).order_by(Product.name).all()
            return [
                {
                    "id": p.id,
                    "name": p.name,
                    "sku": p.sku,
                    "category": p.category.name if p.category else "",
                    "stock_qty": p.stock_qty,
                    "alert_threshold": p.alert_threshold,
                    "sale_price": p.sale_price,
                    "stock_value": round(p.sale_price * p.stock_qty, 2),
                }
                for p in products
            ]

    # ------------------------------------------------------------------
    # Mécanique interne
    # ------------------------------------------------------------------
    @staticmethod
    def _apply_movement(product_id: int, move_type: str, quantity: float,
                        reason: str, user: User | None,
                        reference: str = "") -> None:
        """Applique une entrée ou une sortie dans une seule transaction."""
        if quantity <= 0:
            raise ValueError("La quantité doit être supérieure à zéro.")
        with get_session() as session:
            product = session.get(Product, product_id)
            if product is None:
                raise ValueError("Produit introuvable.")
            if move_type == MOVE_IN:
                product.stock_qty += quantity
            else:
                product.stock_qty -= quantity
            movement = StockMovement(
                product_id=product_id,
                move_type=move_type,
                quantity=quantity,
                stock_after=product.stock_qty,
                reason=reason,
                reference=reference,
                user_id=user.id if user else None,
            )
            session.add(movement)
            session.commit()
            log_action(
                f"{move_type.capitalize()} stock",
                f"{product.name} : {quantity:g} (stock {product.stock_qty:g})",
                user,
            )
