"""Contrôleur Ventes / Facturation.

Cycle de vie d'une facture :
1. ``create_sale`` valide la vente dans UNE transaction :
   numéro unique, lignes, mise à jour du stock, mouvements, audit ;
2. le service PDF génère la facture A4 ;
3. ``cancel_sale`` (administrateur) annule et réapprovisionne le stock.

Le stock peut devenir négatif (vente avant réapprovisionnement) : il est
alors affiché en rouge et compté parmi les ruptures.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, or_

from app.config import MOVE_IN, MOVE_OUT, SALE_CANCELLED, SALE_VALIDATED
from app.models.database import get_session
from app.models.entities import Counter, Product, Sale, SaleItem, StockMovement, User
from app.services.audit_service import log_action
from app.utils.helpers import round2


class SaleController:
    """Opérations de facturation."""

    # ------------------------------------------------------------------
    # Numérotation
    # ------------------------------------------------------------------
    @staticmethod
    def _next_invoice_number(session) -> str:
        """Génère le prochain numéro de facture : FAC-ANNÉE-NNNNN.

        Un compteur par année est conservé dans la table ``counters`` ;
        l'incrément se fait dans la transaction de la vente, ce qui
        garantit l'unicité même en cas d'utilisation simultanée.
        """
        year = datetime.now().year
        key = f"invoice:{year}"
        counter = session.get(Counter, key)
        if counter is None:
            counter = Counter(key=key, value=0)
            session.add(counter)
        counter.value += 1
        return f"FAC-{year}-{counter.value:05d}"

    # ------------------------------------------------------------------
    # Création / validation
    # ------------------------------------------------------------------
    @staticmethod
    def create_sale(data: dict, user: User | None = None) -> dict:
        """Valide une vente et retourne la facture complète (dict).

        :param data:
            customer_name, customer_phone, customer_id (facultatif),
            amount_paid,
            items : liste de dicts ``product_id`` (None si manuel),
                    ``name``, ``quantity``, ``unit_price``, ``is_manual``.
        :raises ValueError: si les données sont invalides.
        """
        items_data = data.get("items") or []
        if not items_data:
            raise ValueError("La facture doit contenir au moins un produit.")

        # Validation préalable des lignes.
        for item in items_data:
            if not str(item.get("name", "")).strip():
                raise ValueError("Chaque ligne doit avoir un nom de produit.")
            if float(item.get("quantity", 0)) <= 0:
                raise ValueError(f"Quantité invalide pour « {item.get('name')} ».")
            if float(item.get("unit_price", 0)) < 0:
                raise ValueError(f"Prix unitaire invalide pour « {item.get('name')} ».")

        amount_paid = max(0.0, float(data.get("amount_paid", 0)))

        with get_session() as session:
            number = SaleController._next_invoice_number(session)

            sale = Sale(
                number=number,
                customer_name=(data.get("customer_name") or "").strip(),
                customer_phone=(data.get("customer_phone") or "").strip(),
                customer_id=data.get("customer_id"),
                amount_paid=0.0,  # calculés après les lignes
                subtotal=0.0,
                total=0.0,
                remaining=0.0,
                status=SALE_VALIDATED,
                user_id=user.id if user else None,
            )
            session.add(sale)

            subtotal = 0.0
            for item_data in items_data:
                product_id = item_data.get("product_id")
                quantity = float(item_data["quantity"])
                unit_price = round2(item_data["unit_price"])
                line_total = round2(quantity * unit_price)
                subtotal = round2(subtotal + line_total)

                product = session.get(Product, product_id) if product_id else None
                unit_cost = product.purchase_price if product else 0.0

                session.add(SaleItem(
                    sale=sale,
                    product_id=product.id if product else None,
                    product_name=str(item_data["name"]).strip(),
                    quantity=quantity,
                    unit_price=unit_price,
                    line_total=line_total,
                    unit_cost=unit_cost,
                    is_manual=bool(item_data.get("is_manual")) or product is None,
                ))

                # Mise à jour du stock pour les produits enregistrés.
                if product is not None:
                    product.stock_qty -= quantity
                    session.add(StockMovement(
                        product_id=product.id,
                        move_type=MOVE_OUT,
                        quantity=quantity,
                        stock_after=product.stock_qty,
                        reason="Vente",
                        reference=number,
                        user_id=user.id if user else None,
                    ))

            sale.subtotal = subtotal
            sale.total = subtotal
            sale.amount_paid = round2(amount_paid)
            sale.remaining = max(0.0, round2(sale.total - sale.amount_paid))

            # Création automatique de la dette si montant restant et client enregistré
            if sale.remaining > 0 and sale.customer_id:
                from app.models.entities import CustomerDebt
                from datetime import timedelta
                session.flush()  # Assigne l'id de la vente
                debt = CustomerDebt(
                    customer_id=sale.customer_id,
                    sale_id=sale.id,
                    amount=sale.remaining,
                    paid=0.0,
                    remaining=sale.remaining,
                    due_date=datetime.now() + timedelta(days=30),
                    notes=f"Créée automatiquement suite à la facture {number}",
                    status="actif"
                )
                session.add(debt)

            session.commit()
            log_action(
                "Vente validée",
                f"{number} — total {sale.total:g} — {len(items_data)} article(s)",
                user,
            )
            return SaleController._to_dict(sale)

    # ------------------------------------------------------------------
    # Annulation (administrateur)
    # ------------------------------------------------------------------
    @staticmethod
    def cancel_sale(sale_id: int, user: User | None = None) -> None:
        """Annule une facture et réintègre les produits dans le stock."""
        with get_session() as session:
            sale = session.get(Sale, sale_id)
            if sale is None:
                raise ValueError("Facture introuvable.")
            if sale.status == SALE_CANCELLED:
                raise ValueError("Cette facture est déjà annulée.")

            for item in sale.items:
                if item.product_id:
                    product = session.get(Product, item.product_id)
                    if product is not None:
                        product.stock_qty += item.quantity
                        session.add(StockMovement(
                            product_id=product.id,
                            move_type=MOVE_IN,
                            quantity=item.quantity,
                            stock_after=product.stock_qty,
                            reason=f"Annulation de la facture {sale.number}",
                            reference=sale.number,
                            user_id=user.id if user else None,
                        ))

            # Suppression de la dette associée si elle existe
            from app.models.entities import CustomerDebt
            debt = session.query(CustomerDebt).filter(CustomerDebt.sale_id == sale.id).first()
            if debt:
                # Supprimer également tous les paiements associés à cette dette
                from app.models.entities import DebtPayment
                session.query(DebtPayment).filter(DebtPayment.debt_id == debt.id).delete()
                session.delete(debt)

            sale.status = SALE_CANCELLED
            session.commit()
            log_action("Vente annulée", sale.number, user)

    # ------------------------------------------------------------------
    # Consultation
    # ------------------------------------------------------------------
    @staticmethod
    def get_sale(sale_id: int) -> dict | None:
        """Retourne une facture complète par identifiant."""
        with get_session() as session:
            sale = session.get(Sale, sale_id)
            return SaleController._to_dict(sale) if sale else None

    @staticmethod
    def list_sales(search: str = "", start: datetime | None = None,
                   end: datetime | None = None, include_cancelled: bool = True,
                   limit: int = 500) -> list[dict]:
        """Liste les factures (résumés), de la plus récente à la plus ancienne."""
        with get_session() as session:
            query = session.query(Sale)
            if not include_cancelled:
                query = query.filter(Sale.status == SALE_VALIDATED)
            if start:
                query = query.filter(Sale.created_at >= start)
            if end:
                query = query.filter(Sale.created_at <= end)
            if search.strip():
                pattern = f"%{search.strip()}%"
                query = query.filter(or_(Sale.number.ilike(pattern),
                                         Sale.customer_name.ilike(pattern)))
            rows = query.order_by(Sale.created_at.desc()).limit(limit).all()
            return [SaleController._summary(s) for s in rows]

    @staticmethod
    def today_stats() -> tuple[int, float]:
        """Retourne (nombre de factures du jour, chiffre d'affaires du jour)."""
        now = datetime.now()
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        with get_session() as session:
            count, total = (
                session.query(func.count(Sale.id), func.coalesce(func.sum(Sale.total), 0.0))
                .filter(Sale.created_at >= start, Sale.status == SALE_VALIDATED)
                .one()
            )
            return int(count), float(total)

    @staticmethod
    def set_pdf_path(sale_id: int, path: str) -> None:
        """Mémorise le chemin du PDF généré pour une facture."""
        with get_session() as session:
            sale = session.get(Sale, sale_id)
            if sale is not None:
                sale.pdf_path = path
                session.commit()

    # ------------------------------------------------------------------
    # Conversions
    # ------------------------------------------------------------------
    @staticmethod
    def _summary(sale: Sale) -> dict:
        """Résumé d'une facture (pour les listes)."""
        return {
            "id": sale.id,
            "number": sale.number,
            "created_at": sale.created_at,
            "customer_name": sale.customer_name,
            "customer_phone": sale.customer_phone,
            "total": sale.total,
            "amount_paid": sale.amount_paid,
            "remaining": sale.remaining,
            "status": sale.status,
            "pdf_path": sale.pdf_path,
        }

    @staticmethod
    def _to_dict(sale: Sale) -> dict:
        """Facture complète avec ses lignes (pour PDF et aperçu)."""
        data = SaleController._summary(sale)
        data.update({
            "customer_id": sale.customer_id,
            "subtotal": sale.subtotal,
            "items": [
                {
                    "product_id": item.product_id,
                    "product_name": item.product_name,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "line_total": item.line_total,
                    "is_manual": item.is_manual,
                }
                for item in sale.items
            ],
        })
        return data
