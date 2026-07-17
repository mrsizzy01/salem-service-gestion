"""Entités SQLAlchemy de l'application (schéma de la base SQLite).

Toutes les tables sont créées automatiquement au premier lancement
par le gestionnaire de migrations (``migrations.py``).

Conventions :
- les montants sont stockés en ``Float`` arrondis à 2 décimales par la
  couche contrôleur (volume de boutique, précision suffisante) ;
- les dates sont en ``DateTime`` UTC locale naïve pour rester simples ;
- les suppressions de produits référencés par des ventes sont des
  suppressions logiques (``active=False``) afin de préserver
  l'historique des factures.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.database import Base


# ------------------------------------------------------------------
# Utilisateurs et sécurité
# ------------------------------------------------------------------
class User(Base):
    """Utilisateur de l'application (administrateur ou caissier)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), default="")
    role: Mapped[str] = mapped_column(String(20), default="caissier")  # admin | caissier
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    def __repr__(self) -> str:  # pragma: no cover - debug
        return f"<User {self.username} ({self.role})>"


class AuditLog(Base):
    """Journal complet des actions réalisées dans l'application."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    username: Mapped[str] = mapped_column(String(50), default="")  # dénormalisé (historique)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    details: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)


# ------------------------------------------------------------------
# Catalogue produits
# ------------------------------------------------------------------
class Category(Base):
    """Catégorie de produits."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)

    products: Mapped[list["Product"]] = relationship(back_populates="category")


class Product(Base):
    """Produit commercialisé par la boutique."""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    sku: Mapped[str] = mapped_column(String(60), default="", index=True)  # référence / code-barres
    barcode: Mapped[str] = mapped_column(String(20), default="", index=True)  # EAN-13
    category_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("categories.id"), nullable=True)
    purchase_price: Mapped[float] = mapped_column(Float, default=0.0)   # prix d'achat
    sale_price: Mapped[float] = mapped_column(Float, default=0.0)       # prix de vente
    stock_qty: Mapped[float] = mapped_column(Float, default=0.0)        # quantité en stock
    alert_threshold: Mapped[float] = mapped_column(Float, default=5.0)  # seuil d'alerte
    image_path: Mapped[str] = mapped_column(String(500), default="")    # photo facultative
    active: Mapped[bool] = mapped_column(Boolean, default=True)         # suppression logique
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    category: Mapped["Category"] = relationship(back_populates="products")

    @property
    def in_stock(self) -> bool:
        """Vrai si le produit est disponible (stock strictement positif)."""
        return self.stock_qty > 0


class StockMovement(Base):
    """Mouvement de stock (entrée, sortie ou ajustement d'inventaire)."""

    __tablename__ = "stock_movements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    move_type: Mapped[str] = mapped_column(String(20), nullable=False)  # entrée | sortie | ajustement
    quantity: Mapped[float] = mapped_column(Float, nullable=False)      # toujours positive
    stock_after: Mapped[float] = mapped_column(Float, default=0.0)      # stock résultant
    reason: Mapped[str] = mapped_column(String(300), default="")
    reference: Mapped[str] = mapped_column(String(60), default="")      # n° de facture éventuel
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)

    product: Mapped["Product"] = relationship()


# ------------------------------------------------------------------
# Tiers (clients facultatifs, fournisseurs)
# ------------------------------------------------------------------
class Customer(Base):
    """Client enregistré (facultatif : une facture peut exister sans client)."""

    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    phone: Mapped[str] = mapped_column(String(40), default="")
    email: Mapped[str] = mapped_column(String(120), default="")
    address: Mapped[str] = mapped_column(String(300), default="")
    avenue: Mapped[str] = mapped_column(String(100), default="")
    quartier: Mapped[str] = mapped_column(String(100), default="")
    commune: Mapped[str] = mapped_column(String(100), default="")
    city: Mapped[str] = mapped_column(String(100), default="Lubumbashi")
    province: Mapped[str] = mapped_column(String(100), default="Haut-Katanga")
    credit_limit: Mapped[float] = mapped_column(Float, default=0.0)  # limite de crédit
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class Supplier(Base):
    """Fournisseur de la boutique."""

    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    phone: Mapped[str] = mapped_column(String(40), default="")
    email: Mapped[str] = mapped_column(String(120), default="")
    address: Mapped[str] = mapped_column(String(300), default="")
    avenue: Mapped[str] = mapped_column(String(100), default="")
    quartier: Mapped[str] = mapped_column(String(100), default="")
    commune: Mapped[str] = mapped_column(String(100), default="")
    city: Mapped[str] = mapped_column(String(100), default="Lubumbashi")
    province: Mapped[str] = mapped_column(String(100), default="Haut-Katanga")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


# ------------------------------------------------------------------
# Ventes / facturation
# ------------------------------------------------------------------
class Sale(Base):
    """Vente validée, matérialisée par une facture numérotée unique."""

    __tablename__ = "sales"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)

    # Informations client saisies directement sur la facture
    # (l'enregistrement du client en base reste facultatif).
    customer_name: Mapped[str] = mapped_column(String(200), default="")
    customer_phone: Mapped[str] = mapped_column(String(40), default="")
    customer_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("customers.id"), nullable=True)

    subtotal: Mapped[float] = mapped_column(Float, default=0.0)
    tax_amount: Mapped[float] = mapped_column(Float, default=0.0)      # TVA
    discount_amount: Mapped[float] = mapped_column(Float, default=0.0)   # remise
    total: Mapped[float] = mapped_column(Float, default=0.0)
    amount_paid: Mapped[float] = mapped_column(Float, default=0.0)
    remaining: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(10), default="CDF")   # CDF | USD
    exchange_rate: Mapped[float] = mapped_column(Float, default=1.0)    # taux de change

    status: Mapped[str] = mapped_column(String(20), default="validée", index=True)
    pdf_path: Mapped[str] = mapped_column(String(500), default="")
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)

    items: Mapped[list["SaleItem"]] = relationship(
        back_populates="sale", cascade="all, delete-orphan", lazy="joined"
    )


class SaleItem(Base):
    """Ligne de facture (produit enregistré ou saisi manuellement)."""

    __tablename__ = "sale_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sale_id: Mapped[int] = mapped_column(Integer, ForeignKey("sales.id"), nullable=False, index=True)
    product_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("products.id"), nullable=True)
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)  # dénormalisé
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    line_total: Mapped[float] = mapped_column(Float, nullable=False)
    unit_cost: Mapped[float] = mapped_column(Float, default=0.0)  # coût d'achat au moment de la vente
    discount_pct: Mapped[float] = mapped_column(Float, default=0.0)  # remise % sur la ligne
    is_manual: Mapped[bool] = mapped_column(Boolean, default=False)

    sale: Mapped["Sale"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship()


# ------------------------------------------------------------------
# Crédit client / dettes
# ------------------------------------------------------------------
class CustomerDebt(Base):
    """Suivi des dettes clients (crédit accordé)."""

    __tablename__ = "customer_debts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    sale_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("sales.id"), nullable=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)        # montant total de la dette
    paid: Mapped[float] = mapped_column(Float, default=0.0)               # montant déjà payé
    remaining: Mapped[float] = mapped_column(Float, default=0.0)         # reste à payer
    due_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # date d'échéance
    notes: Mapped[str] = mapped_column(String(500), default="")
    status: Mapped[str] = mapped_column(String(20), default="actif")    # actif | payé | retard
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class DebtPayment(Base):
    """Paiement partiel d'une dette client."""

    __tablename__ = "debt_payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    debt_id: Mapped[int] = mapped_column(Integer, ForeignKey("customer_debts.id"), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    payment_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    notes: Mapped[str] = mapped_column(String(300), default="")
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)


# ------------------------------------------------------------------
# Commandes fournisseurs
# ------------------------------------------------------------------
class PurchaseOrder(Base):
    """Bon de commande fournisseur."""

    __tablename__ = "purchase_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    supplier_id: Mapped[int] = mapped_column(Integer, ForeignKey("suppliers.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="brouillon")  # brouillon | envoyé | reçu | annulé
    subtotal: Mapped[float] = mapped_column(Float, default=0.0)
    tax_amount: Mapped[float] = mapped_column(Float, default=0.0)
    total: Mapped[float] = mapped_column(Float, default=0.0)
    notes: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    received_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)

    items: Mapped[list["PurchaseOrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


class PurchaseOrderItem(Base):
    """Ligne de bon de commande."""

    __tablename__ = "purchase_order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("purchase_orders.id"), nullable=False)
    product_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("products.id"), nullable=True)
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    line_total: Mapped[float] = mapped_column(Float, nullable=False)
    received_qty: Mapped[float] = mapped_column(Float, default=0.0)  # quantité reçue
    order: Mapped["PurchaseOrder"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship()


# ------------------------------------------------------------------
# Promotions
# ------------------------------------------------------------------
class Promotion(Base):
    """Promotion active sur un produit ou une catégorie."""

    __tablename__ = "promotions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[str] = mapped_column(String(30), nullable=False)  # remise_pct | remise_montant | 2eme_moitie | pack
    value: Mapped[float] = mapped_column(Float, default=0.0)         # % ou montant
    product_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("products.id"), nullable=True)
    category_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("categories.id"), nullable=True)
    start_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    end_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


# ------------------------------------------------------------------
# Dépenses
# ------------------------------------------------------------------
class Expense(Base):
    """Dépense de l'entreprise (loyer, transport, salaires, etc.)."""

    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(80), default="Divers")
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    spent_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
    note: Mapped[str] = mapped_column(Text, default="")
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)


# ------------------------------------------------------------------
# Paramètres et compteurs internes
# ------------------------------------------------------------------
class CompanySettings(Base):
    """Paramètres de l'entreprise (une seule ligne, id = 1)."""

    __tablename__ = "company_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), default="Salem Service")
    address: Mapped[str] = mapped_column(String(300), default="")
    avenue: Mapped[str] = mapped_column(String(100), default="")
    quartier: Mapped[str] = mapped_column(String(100), default="")
    commune: Mapped[str] = mapped_column(String(100), default="")
    city: Mapped[str] = mapped_column(String(100), default="Lubumbashi")
    province: Mapped[str] = mapped_column(String(100), default="Haut-Katanga")
    phone: Mapped[str] = mapped_column(String(60), default="")
    email: Mapped[str] = mapped_column(String(120), default="")
    currency: Mapped[str] = mapped_column(String(10), default="CDF")
    secondary_currency: Mapped[str] = mapped_column(String(10), default="USD")
    exchange_rate: Mapped[float] = mapped_column(Float, default=2800.0)  # CDF/USD
    tax_rate: Mapped[float] = mapped_column(Float, default=16.0)        # TVA %
    logo_path: Mapped[str] = mapped_column(String(500), default="")
    thanks_message: Mapped[str] = mapped_column(
        String(300), default="Merci de votre confiance !"
    )
    # Identifiants fiscaux RDC
    id_nat: Mapped[str] = mapped_column(String(30), default="")       # Numéro d'identification nationale
    rccm: Mapped[str] = mapped_column(String(30), default="")          # Registre du commerce
    nif: Mapped[str] = mapped_column(String(30), default="")           # Numéro d'identification fiscale
    tax_center: Mapped[str] = mapped_column(String(100), default="")  # Centre des impôts


class Counter(Base):
    """Compteurs internes (numérotation des factures par année)."""

    __tablename__ = "counters"

    key: Mapped[str] = mapped_column(String(60), primary_key=True)
    value: Mapped[int] = mapped_column(Integer, default=0)
