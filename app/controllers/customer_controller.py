"""Contrôleur Clients (enregistrement facultatif)."""

from __future__ import annotations

from app.models.database import get_session
from app.models.entities import Customer, User
from app.services.audit_service import log_action


class CustomerController:
    """CRUD des clients.

    Rappel : l'enregistrement d'un client est facultatif — les
    informations saisies sur une facture suffisent à la facturation.
    """

    @staticmethod
    def list_customers(search: str = "") -> list[dict]:
        """Liste les clients, filtrés par nom ou téléphone."""
        with get_session() as session:
            query = session.query(Customer)
            if search.strip():
                pattern = f"%{search.strip()}%"
                query = query.filter(Customer.name.ilike(pattern) | Customer.phone.ilike(pattern))
            rows = query.order_by(Customer.name).all()
            return [
                {
                    "id": c.id, "name": c.name, "phone": c.phone,
                    "email": c.email, "address": c.address,
                    "avenue": c.avenue, "quartier": c.quartier,
                    "commune": c.commune, "city": c.city,
                    "province": c.province, "credit_limit": c.credit_limit,
                }
                for c in rows
            ]

    @staticmethod
    def save_customer(data: dict, user: User | None = None,
                      customer_id: int | None = None) -> dict:
        """Crée ou met à jour un client."""
        if not data.get("name", "").strip():
            raise ValueError("Le nom du client est obligatoire.")
        with get_session() as session:
            if customer_id:
                customer = session.get(Customer, customer_id)
                if customer is None:
                    raise ValueError("Client introuvable.")
                action = "Modification client"
            else:
                customer = Customer()
                session.add(customer)
                action = "Création client"
            customer.name = data["name"].strip()
            customer.phone = data.get("phone", "").strip()
            customer.email = data.get("email", "").strip()
            customer.address = data.get("address", "").strip()
            customer.avenue = data.get("avenue", "").strip()
            customer.quartier = data.get("quartier", "").strip()
            customer.commune = data.get("commune", "").strip()
            customer.city = data.get("city", "Lubumbashi").strip()
            customer.province = data.get("province", "Haut-Katanga").strip()
            customer.credit_limit = float(data.get("credit_limit", 0.0))
            session.commit()
            log_action(action, customer.name, user)
            return {
                "id": customer.id, "name": customer.name, "phone": customer.phone,
                "email": customer.email, "address": customer.address,
                "avenue": customer.avenue, "quartier": customer.quartier,
                "commune": customer.commune, "city": customer.city,
                "province": customer.province, "credit_limit": customer.credit_limit,
            }

    @staticmethod
    def delete_customer(customer_id: int, user: User | None = None) -> None:
        """Supprime un client (les factures existantes conservent leurs infos)."""
        with get_session() as session:
            customer = session.get(Customer, customer_id)
            if customer is None:
                raise ValueError("Client introuvable.")
            name = customer.name
            session.delete(customer)
            session.commit()
            log_action("Suppression client", name, user)
