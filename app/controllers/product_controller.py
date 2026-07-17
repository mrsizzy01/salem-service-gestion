"""Contrôleur Produits : catalogue, catégories et images."""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from sqlalchemy import func, or_

from app.config import images_dir
from app.models.database import get_session
from app.models.entities import Category, Product, SaleItem, StockMovement, User
from app.services.audit_service import log_action
from app.utils.helpers import round2


class ProductController:
    """Opérations sur les produits et leurs catégories."""

    # ------------------------------------------------------------------
    # Images
    # ------------------------------------------------------------------
    @staticmethod
    def import_image(source_path: str) -> str:
        """Copie une image dans le dossier applicatif, retourne le chemin."""
        src = Path(source_path)
        if not src.exists():
            raise FileNotFoundError(f"Image introuvable : {source_path}")
        dest = images_dir() / f"produit_{uuid.uuid4().hex[:12]}{src.suffix.lower()}"
        shutil.copy2(src, dest)
        return str(dest)

    # ------------------------------------------------------------------
    # Catégories
    # ------------------------------------------------------------------
    @staticmethod
    def list_categories() -> list[dict]:
        """Retourne toutes les catégories (id + nom), triées par nom."""
        with get_session() as session:
            rows = session.query(Category).order_by(Category.name).all()
            return [{"id": c.id, "name": c.name} for c in rows]

    @staticmethod
    def create_category(name: str, user: User | None = None) -> dict:
        """Crée une catégorie (ou retourne l'existante du même nom)."""
        name = name.strip()
        if not name:
            raise ValueError("Le nom de la catégorie est obligatoire.")
        with get_session() as session:
            existing = session.query(Category).filter(func.lower(Category.name) == name.lower()).first()
            if existing:
                return {"id": existing.id, "name": existing.name}
            category = Category(name=name)
            session.add(category)
            session.commit()
            log_action("Création catégorie", name, user)
            return {"id": category.id, "name": category.name}

    # ------------------------------------------------------------------
    # Produits
    # ------------------------------------------------------------------
    @staticmethod
    def list_products(search: str = "", category_id: int | None = None,
                      include_inactive: bool = False) -> list[dict]:
        """Liste les produits filtrés par recherche et/ou catégorie."""
        with get_session() as session:
            query = session.query(Product)
            if not include_inactive:
                query = query.filter(Product.active.is_(True))
            if category_id:
                query = query.filter(Product.category_id == category_id)
            if search.strip():
                pattern = f"%{search.strip()}%"
                query = query.filter(or_(Product.name.ilike(pattern), Product.sku.ilike(pattern)))
            query = query.order_by(Product.name)
            return [ProductController._to_dict(p) for p in query.all()]

    @staticmethod
    def get_product(product_id: int) -> dict | None:
        """Retourne un produit par identifiant (None si absent)."""
        with get_session() as session:
            product = session.get(Product, product_id)
            return ProductController._to_dict(product) if product else None

    @staticmethod
    def create_product(data: dict, user: User | None = None) -> dict:
        """Crée un produit.

        :param data: name, sku, category_id, purchase_price, sale_price,
                     stock_qty, alert_threshold, image_path.
        """
        if not data.get("name", "").strip():
            raise ValueError("Le nom du produit est obligatoire.")
        with get_session() as session:
            product = Product(
                name=data["name"].strip(),
                sku=data.get("sku", "").strip(),
                category_id=data.get("category_id"),
                purchase_price=round2(data.get("purchase_price", 0)),
                sale_price=round2(data.get("sale_price", 0)),
                stock_qty=float(data.get("stock_qty", 0)),
                alert_threshold=float(data.get("alert_threshold", 5)),
                image_path=data.get("image_path", ""),
                active=True,
            )
            session.add(product)
            session.commit()
            log_action("Création produit", f"{product.name} (#{product.id})", user)
            return ProductController._to_dict(product)

    @staticmethod
    def update_product(product_id: int, data: dict, user: User | None = None) -> dict:
        """Met à jour un produit existant."""
        with get_session() as session:
            product = session.get(Product, product_id)
            if product is None:
                raise ValueError("Produit introuvable.")
            if "name" in data:
                product.name = data["name"].strip()
            if "sku" in data:
                product.sku = data["sku"].strip()
            if "category_id" in data:
                product.category_id = data["category_id"]
            if "purchase_price" in data:
                product.purchase_price = round2(data["purchase_price"])
            if "sale_price" in data:
                product.sale_price = round2(data["sale_price"])
            if "stock_qty" in data:
                product.stock_qty = float(data["stock_qty"])
            if "alert_threshold" in data:
                product.alert_threshold = float(data["alert_threshold"])
            if "image_path" in data:
                product.image_path = data["image_path"]
            session.commit()
            log_action("Modification produit", f"{product.name} (#{product.id})", user)
            return ProductController._to_dict(product)

    @staticmethod
    def delete_product(product_id: int, user: User | None = None) -> None:
        """Supprime un produit.

        Suppression logique (``active=False``) si le produit est référencé
        par des ventes ou des mouvements, afin de préserver l'historique ;
        suppression physique sinon.
        """
        with get_session() as session:
            product = session.get(Product, product_id)
            if product is None:
                raise ValueError("Produit introuvable.")
            used = (
                session.query(SaleItem).filter(SaleItem.product_id == product_id).first()
                or session.query(StockMovement).filter(StockMovement.product_id == product_id).first()
            )
            name = product.name
            if used:
                product.active = False
            else:
                session.delete(product)
            session.commit()
            log_action("Suppression produit", f"{name} (#{product_id})", user)

    # ------------------------------------------------------------------
    # Statistiques rapides
    # ------------------------------------------------------------------
    @staticmethod
    def stock_counts() -> tuple[int, int]:
        """Retourne (produits en stock, produits en rupture)."""
        with get_session() as session:
            base = session.query(Product).filter(Product.active.is_(True))
            in_stock = base.filter(Product.stock_qty > 0).count()
            out_stock = base.filter(Product.stock_qty <= 0).count()
            return in_stock, out_stock

    # ------------------------------------------------------------------
    # Conversion
    # ------------------------------------------------------------------
    @staticmethod
    def _to_dict(product: Product) -> dict:
        """Convertit un produit ORM en dictionnaire simple."""
        return {
            "id": product.id,
            "name": product.name,
            "sku": product.sku,
            "category_id": product.category_id,
            "category": product.category.name if product.category else "",
            "purchase_price": product.purchase_price,
            "sale_price": product.sale_price,
            "stock_qty": product.stock_qty,
            "alert_threshold": product.alert_threshold,
            "image_path": product.image_path,
            "active": product.active,
        }
