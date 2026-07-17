"""Contrôleur Promotions : remises, packs, 2ème à -50%."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import or_

from app.models.database import get_session
from app.models.entities import Product, Promotion, User
from app.services.audit_service import log_action


class PromotionController:
    """Gestion des promotions commerciales."""

    @staticmethod
    def list_promotions(active_only: bool = True) -> list[dict]:
        """Liste les promotions."""
        with get_session() as session:
            query = session.query(Promotion)
            if active_only:
                query = query.filter(Promotion.active.is_(True))
                query = query.filter(
                    or_(Promotion.end_date.is_(None), Promotion.end_date >= datetime.now())
                )
            rows = query.order_by(Promotion.created_at.desc()).all()
            return [
                {
                    "id": p.id, "label": p.label, "type": p.type,
                    "value": p.value, "product_id": p.product_id,
                    "category_id": p.category_id,
                    "start_date": p.start_date, "end_date": p.end_date,
                    "active": p.active,
                    "product": p.product.name if p.product else None,
                }
                for p in rows
            ]

    @staticmethod
    def create_promotion(data: dict, user: User | None = None) -> dict:
        """Crée une promotion.

        Types : remise_pct, remise_montant, 2eme_moitie, pack
        """
        if not data.get("label", "").strip():
            raise ValueError("Le libellé de la promotion est obligatoire.")
        with get_session() as session:
            promo = Promotion(
                label=data["label"].strip(),
                type=data.get("type", "remise_pct"),
                value=float(data.get("value", 0)),
                product_id=data.get("product_id"),
                category_id=data.get("category_id"),
                start_date=data.get("start_date") or datetime.now(),
                end_date=data.get("end_date"),
                active=True,
            )
            session.add(promo)
            session.commit()
            log_action("Création promotion", promo.label, user)
            return {"id": promo.id, "label": promo.label, "type": promo.type,
                    "value": promo.value}

    @staticmethod
    def delete_promotion(promotion_id: int, user: User | None = None) -> None:
        """Supprime une promotion."""
        with get_session() as session:
            promo = session.get(Promotion, promotion_id)
            if promo is None:
                raise ValueError("Promotion introuvable.")
            label = promo.label
            session.delete(promo)
            session.commit()
            log_action("Suppression promotion", label, user)

    @staticmethod
    def apply_promotions(items: list[dict]) -> tuple[list[dict], float]:
        """Applique les promotions actives sur les lignes de facture.

        Retourne (items modifiés, montant total des remises).
        """
        promotions = PromotionController.list_promotions(active_only=True)
        total_discount = 0.0
        modified_items = []

        for item in items:
            modified = dict(item)
            unit_price = item["unit_price"]
            qty = item["quantity"]
            line_discount = 0.0

            for promo in promotions:
                # Vérifier si la promo s'applique à ce produit
                applies = False
                if promo["product_id"] and promo["product_id"] == item.get("product_id"):
                    applies = True
                if promo["category_id"] and item.get("category_id") == promo["category_id"]:
                    applies = True
                if not promo["product_id"] and not promo["category_id"]:
                    applies = True  # Promo globale

                if not applies:
                    continue

                if promo["type"] == "remise_pct":
                    line_discount += unit_price * qty * (promo["value"] / 100)
                elif promo["type"] == "remise_montant":
                    line_discount += min(promo["value"] * qty, unit_price * qty)
                elif promo["type"] == "2eme_moitie" and qty >= 2:
                    # 2ème article à -50%
                    pairs = int(qty // 2)
                    line_discount += unit_price * 0.5 * pairs

            modified["discount"] = round(line_discount, 2)
            modified["unit_price_after_discount"] = round(
                (unit_price * qty - line_discount) / qty if qty > 0 else 0, 2
            )
            total_discount += line_discount
            modified_items.append(modified)

        return modified_items, round(total_discount, 2)
