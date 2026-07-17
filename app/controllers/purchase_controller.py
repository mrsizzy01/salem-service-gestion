"""Contrôleur Commandes Fournisseurs : bons de commande et réception."""

from __future__ import annotations

from datetime import datetime

from app.config import MOVE_IN
from app.models.database import get_session
from app.models.entities import Counter, Product, PurchaseOrder, PurchaseOrderItem, StockMovement, Supplier, User
from app.services.audit_service import log_action
from app.utils.helpers import round2


class PurchaseController:
    """Gestion des bons de commande fournisseurs."""

    @staticmethod
    def _next_po_number(session) -> str:
        """Génère le prochain numéro de commande : BC-ANNÉE-NNNNN."""
        year = datetime.now().year
        key = f"po:{year}"
        counter = session.get(Counter, key)
        if counter is None:
            counter = Counter(key=key, value=0)
            session.add(counter)
        counter.value += 1
        return f"BC-{year}-{counter.value:05d}"

    @staticmethod
    def create_order(data: dict, user: User | None = None) -> dict:
        """Crée un bon de commande."""
        items = data.get("items", [])
        if not items:
            raise ValueError("La commande doit contenir au moins un article.")

        with get_session() as session:
            number = PurchaseController._next_po_number(session)
            order = PurchaseOrder(
                number=number,
                supplier_id=data["supplier_id"],
                status="brouillon",
                notes=data.get("notes", ""),
                user_id=user.id if user else None,
            )
            session.add(order)

            subtotal = 0.0
            for item_data in items:
                line_total = round2(item_data["quantity"] * item_data["unit_price"])
                subtotal += line_total
                session.add(PurchaseOrderItem(
                    order=order,
                    product_id=item_data.get("product_id"),
                    product_name=item_data["name"],
                    quantity=item_data["quantity"],
                    unit_price=item_data["unit_price"],
                    line_total=line_total,
                ))

            order.subtotal = subtotal
            order.total = subtotal
            session.commit()
            log_action("Création commande", number, user)
            return {"id": order.id, "number": number, "total": order.total}

    @staticmethod
    def receive_order(order_id: int, received_items: dict[int, float],
                     user: User | None = None) -> dict:
        """Réceptionne une commande et met à jour le stock."""
        with get_session() as session:
            order = session.get(PurchaseOrder, order_id)
            if order is None:
                raise ValueError("Commande introuvable.")
            if order.status == "annulé":
                raise ValueError("Cette commande est annulée.")

            for item in order.items:
                received_qty = received_items.get(item.id, 0)
                if received_qty > 0:
                    item.received_qty += received_qty
                    if item.product_id:
                        product = session.get(Product, item.product_id)
                        if product:
                            product.stock_qty += received_qty
                            session.add(StockMovement(
                                product_id=product.id,
                                move_type=MOVE_IN,
                                quantity=received_qty,
                                stock_after=product.stock_qty,
                                reason=f"Réception commande {order.number}",
                                reference=order.number,
                                user_id=user.id if user else None,
                            ))

            all_received = all(item.received_qty >= item.quantity for item in order.items)
            order.status = "reçu" if all_received else "partiel"
            order.received_at = datetime.now()
            session.commit()
            log_action("Réception commande", order.number, user)
            return {"id": order.id, "status": order.status}

    @staticmethod
    def cancel_order(order_id: int, user: User | None = None) -> None:
        """Annule une commande."""
        with get_session() as session:
            order = session.get(PurchaseOrder, order_id)
            if order is None:
                raise ValueError("Commande introuvable.")
            if order.status == "reçu":
                raise ValueError("Impossible d'annuler une commande déjà reçue.")
            order.status = "annulé"
            session.commit()
            log_action("Annulation commande", order.number, user)

    @staticmethod
    def list_orders(supplier_id: int | None = None, status: str | None = None) -> list[dict]:
        """Liste les commandes fournisseurs."""
        with get_session() as session:
            query = session.query(PurchaseOrder)
            if supplier_id:
                query = query.filter(PurchaseOrder.supplier_id == supplier_id)
            if status:
                query = query.filter(PurchaseOrder.status == status)
            rows = query.order_by(PurchaseOrder.created_at.desc()).all()
            return [
                {
                    "id": o.id, "number": o.number,
                    "supplier": o.supplier.name if o.supplier else "—",
                    "supplier_id": o.supplier_id,
                    "status": o.status, "subtotal": o.subtotal,
                    "tax_amount": o.tax_amount, "total": o.total,
                    "created_at": o.created_at, "received_at": o.received_at,
                    "notes": o.notes,
                }
                for o in rows
            ]

    @staticmethod
    def get_order(order_id: int) -> dict | None:
        """Retourne une commande complète avec ses lignes."""
        with get_session() as session:
            order = session.get(PurchaseOrder, order_id)
            if order is None:
                return None
            return {
                "id": order.id, "number": order.number,
                "supplier_id": order.supplier_id,
                "supplier": order.supplier.name if order.supplier else "—",
                "status": order.status, "subtotal": order.subtotal,
                "total": order.total, "notes": order.notes,
                "created_at": order.created_at, "received_at": order.received_at,
                "items": [
                    {
                        "id": item.id, "product_id": item.product_id,
                        "product_name": item.product_name,
                        "quantity": item.quantity, "unit_price": item.unit_price,
                        "line_total": item.line_total,
                        "received_qty": item.received_qty,
                    }
                    for item in order.items
                ],
            }
