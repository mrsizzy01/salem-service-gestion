"""Contrôleur Fournisseurs."""

from __future__ import annotations

from app.models.database import get_session
from app.models.entities import Supplier, User
from app.services.audit_service import log_action


class SupplierController:
    """CRUD des fournisseurs."""

    @staticmethod
    def list_suppliers(search: str = "") -> list[dict]:
        """Liste les fournisseurs, filtrés par nom ou téléphone."""
        with get_session() as session:
            query = session.query(Supplier)
            if search.strip():
                pattern = f"%{search.strip()}%"
                query = query.filter(Supplier.name.ilike(pattern) | Supplier.phone.ilike(pattern))
            rows = query.order_by(Supplier.name).all()
            return [
                {
                    "id": s.id, "name": s.name, "phone": s.phone,
                    "email": s.email, "address": s.address,
                    "avenue": s.avenue, "quartier": s.quartier,
                    "commune": s.commune, "city": s.city,
                    "province": s.province,
                }
                for s in rows
            ]

    @staticmethod
    def save_supplier(data: dict, user: User | None = None,
                      supplier_id: int | None = None) -> dict:
        """Crée ou met à jour un fournisseur."""
        if not data.get("name", "").strip():
            raise ValueError("Le nom du fournisseur est obligatoire.")
        with get_session() as session:
            if supplier_id:
                supplier = session.get(Supplier, supplier_id)
                if supplier is None:
                    raise ValueError("Fournisseur introuvable.")
                action = "Modification fournisseur"
            else:
                supplier = Supplier()
                session.add(supplier)
                action = "Création fournisseur"
            supplier.name = data["name"].strip()
            supplier.phone = data.get("phone", "").strip()
            supplier.email = data.get("email", "").strip()
            supplier.address = data.get("address", "").strip()
            supplier.avenue = data.get("avenue", "").strip()
            supplier.quartier = data.get("quartier", "").strip()
            supplier.commune = data.get("commune", "").strip()
            supplier.city = data.get("city", "Lubumbashi").strip()
            supplier.province = data.get("province", "Haut-Katanga").strip()
            session.commit()
            log_action(action, supplier.name, user)
            return {
                "id": supplier.id, "name": supplier.name, "phone": supplier.phone,
                "email": supplier.email, "address": supplier.address,
                "avenue": supplier.avenue, "quartier": supplier.quartier,
                "commune": supplier.commune, "city": supplier.city,
                "province": supplier.province,
            }

    @staticmethod
    def delete_supplier(supplier_id: int, user: User | None = None) -> None:
        """Supprime un fournisseur."""
        with get_session() as session:
            supplier = session.get(Supplier, supplier_id)
            if supplier is None:
                raise ValueError("Fournisseur introuvable.")
            name = supplier.name
            session.delete(supplier)
            session.commit()
            log_action("Suppression fournisseur", name, user)
