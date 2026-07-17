"""Tests de la logique métier : base, ventes, stock, sécurité, documents."""

from __future__ import annotations

from datetime import datetime

import pytest

from app.controllers.expense_controller import ExpenseController
from app.controllers.product_controller import ProductController
from app.controllers.report_controller import ReportController
from app.controllers.sale_controller import SaleController
from app.controllers.settings_controller import SettingsController
from app.controllers.stock_controller import StockController
from app.controllers.user_controller import UserController
from app.models.database import get_session
from app.models.entities import AuditLog, Product, Sale
from app.services.auth_service import authenticate, ensure_default_admin
from app.services.excel_service import export_report
from app.services.pdf_service import generate_invoice_pdf, generate_report_pdf
from app.services.backup_service import create_backup, list_backups


# ------------------------------------------------------------------
# Démarrage / migrations / sécurité
# ------------------------------------------------------------------
class TestStartup:
    def test_migrations_create_tables(self, fresh_db):
        with get_session() as session:
            assert session.query(Product).count() == 0

    def test_default_admin_created(self, fresh_db):
        assert ensure_default_admin() is True
        assert ensure_default_admin() is False  # une seule fois
        user = authenticate("admin", "admin123")
        assert user is not None and user.role == "admin"

    def test_authentication_rejects_bad_password(self, fresh_db):
        ensure_default_admin()
        assert authenticate("admin", "mauvais") is None

    def test_company_settings_defaults(self, fresh_db):
        company = SettingsController.get_company()
        assert company["name"]
        assert company["currency"] in ("FCFA", "CDF")


# ------------------------------------------------------------------
# Produits et stock
# ------------------------------------------------------------------
class TestProductsStock:
    def _make_product(self) -> dict:
        cat = ProductController.create_category("Boissons")
        return ProductController.create_product({
            "name": "Jus de mangue", "sku": "JM-01", "category_id": cat["id"],
            "purchase_price": 500, "sale_price": 1000, "stock_qty": 20,
        })

    def test_create_and_search_product(self, fresh_db):
        product = self._make_product()
        results = ProductController.list_products(search="mangue")
        assert len(results) == 1 and results[0]["id"] == product["id"]
        assert results[0]["category"] == "Boissons"

    def test_stock_entry_exit_adjust(self, fresh_db):
        product = self._make_product()
        StockController.add_entry(product["id"], 10, "Livraison")
        StockController.add_exit(product["id"], 5, "Casse")
        StockController.adjust(product["id"], 30, "Inventaire")
        assert ProductController.get_product(product["id"])["stock_qty"] == 30
        history = StockController.history(product["id"])
        assert len(history) == 3

    def test_stock_counts(self, fresh_db):
        product = self._make_product()
        in_stock, out_stock = ProductController.stock_counts()
        assert (in_stock, out_stock) == (1, 0)
        StockController.adjust(product["id"], 0)
        in_stock, out_stock = ProductController.stock_counts()
        assert (in_stock, out_stock) == (0, 1)


# ------------------------------------------------------------------
# Facturation
# ------------------------------------------------------------------
class TestSales:
    def _setup(self):
        product = ProductController.create_product({
            "name": "Riz 25kg", "purchase_price": 15000,
            "sale_price": 20000, "stock_qty": 10,
        })
        return product

    def test_full_sale_flow(self, fresh_db):
        product = self._setup()
        sale = SaleController.create_sale({
            "customer_name": "Awa Diop", "customer_phone": "770000000",
            "amount_paid": 30000,
            "items": [
                {"product_id": product["id"], "name": product["name"],
                 "quantity": 2, "unit_price": 20000, "is_manual": False},
                {"product_id": None, "name": "Livraison", "quantity": 1,
                 "unit_price": 5000, "is_manual": True},
            ],
        })
        # Totaux calculés automatiquement.
        assert sale["subtotal"] == 45000
        assert sale["total"] == 45000
        assert sale["remaining"] == 15000
        # Numéro de facture unique.
        assert sale["number"].startswith("FAC-")
        # Stock mis à jour pour le produit enregistré uniquement.
        assert ProductController.get_product(product["id"])["stock_qty"] == 8

    def test_invoice_numbers_are_unique_and_sequential(self, fresh_db):
        product = self._setup()
        numbers = set()
        for _ in range(5):
            sale = SaleController.create_sale({
                "customer_name": "", "customer_phone": "", "amount_paid": 0,
                "items": [{"product_id": product["id"], "name": product["name"],
                           "quantity": 1, "unit_price": 20000, "is_manual": False}],
            })
            numbers.add(sale["number"])
        assert len(numbers) == 5

    def test_sale_validation_rejects_empty(self, fresh_db):
        with pytest.raises(ValueError):
            SaleController.create_sale({"items": [], "amount_paid": 0})

    def test_cancel_sale_restores_stock(self, fresh_db):
        product = self._setup()
        sale = SaleController.create_sale({
            "customer_name": "X", "amount_paid": 20000,
            "items": [{"product_id": product["id"], "name": product["name"],
                       "quantity": 3, "unit_price": 20000, "is_manual": False}],
        })
        assert ProductController.get_product(product["id"])["stock_qty"] == 7
        SaleController.cancel_sale(sale["id"])
        assert ProductController.get_product(product["id"])["stock_qty"] == 10
        with get_session() as session:
            assert session.get(Sale, sale["id"]).status == "annulée"

    def test_devis_flow_and_conversion(self, fresh_db):
        product = self._setup()
        sale = SaleController.create_sale({
            "customer_name": "Devis client", "customer_phone": "12345",
            "amount_paid": 0,
            "status": "devis",
            "items": [{"product_id": product["id"], "name": product["name"],
                       "quantity": 3, "unit_price": 20000, "is_manual": False}],
        })
        assert sale["status"] == "devis"
        # Stock is NOT decremented for devis
        assert ProductController.get_product(product["id"])["stock_qty"] == 10

        # Convert to invoice
        converted = SaleController.convert_devis_to_invoice(sale["id"])
        assert converted["status"] == "validée"
        # Stock IS decremented after conversion
        assert ProductController.get_product(product["id"])["stock_qty"] == 7

    def test_today_cash_summary(self, fresh_db):
        product = self._setup()
        # Create sales with different payment methods
        SaleController.create_sale({
            "amount_paid": 10000, "payment_method": "Cash",
            "items": [{"product_id": product["id"], "name": product["name"],
                       "quantity": 1, "unit_price": 20000, "is_manual": False}],
        })
        SaleController.create_sale({
            "amount_paid": 15000, "payment_method": "Mobile Money",
            "items": [{"product_id": product["id"], "name": product["name"],
                       "quantity": 1, "unit_price": 20000, "is_manual": False}],
        })
        SaleController.create_sale({
            "amount_paid": 5000, "payment_method": "Chèque",
            "items": [{"product_id": product["id"], "name": product["name"],
                       "quantity": 1, "unit_price": 20000, "is_manual": False}],
        })
        summary = ReportController.today_cash_summary()
        assert summary["Cash"] == 10000.0
        assert summary["Mobile Money"] == 15000.0
        assert summary["Chèque"] == 5000.0

    def test_audit_log_written(self, fresh_db):
        product = self._setup()
        SaleController.create_sale({
            "customer_name": "", "amount_paid": 0,
            "items": [{"product_id": product["id"], "name": product["name"],
                       "quantity": 1, "unit_price": 20000, "is_manual": False}],
        })
        with get_session() as session:
            actions = [a.action for a in session.query(AuditLog).all()]
        assert "Création produit" in actions
        assert "Vente validée" in actions


# ------------------------------------------------------------------
# Rapports, PDF, Excel, sauvegarde
# ------------------------------------------------------------------
class TestDocuments:
    def _sale(self):
        product = ProductController.create_product({
            "name": "Huile 5L", "purchase_price": 8000,
            "sale_price": 12000, "stock_qty": 15,
        })
        return SaleController.create_sale({
            "customer_name": "Client Test", "amount_paid": 12000,
            "items": [{"product_id": product["id"], "name": product["name"],
                       "quantity": 1, "unit_price": 12000, "is_manual": False}],
        })

    def test_invoice_pdf_generated(self, fresh_db, tmp_path):
        sale = self._sale()
        company = SettingsController.get_company()
        path = tmp_path / "facture.pdf"
        generate_invoice_pdf(sale, company, path)
        assert path.exists() and path.stat().st_size > 1000

    def test_report_data_and_exports(self, fresh_db, tmp_path):
        sale = self._sale()
        ExpenseController.save_expense({"label": "Loyer", "amount": 5000})
        start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        end = datetime.now().replace(hour=23, minute=59, second=59)
        report = ReportController.build_report(start, end, "Rapport test",
                                               "Aujourd'hui", "FCFA")
        assert report["totals"]["count"] == 1
        assert report["totals"]["total"] == 12000
        assert report["totals"]["expenses"] == 5000
        # Marge brute : (12000 - 8000) x 1 = 4000 ; net = 4000 - 5000 = -1000.
        assert report["totals"]["gross_profit"] == 4000
        assert report["totals"]["net_profit"] == -1000

        pdf_path = tmp_path / "rapport.pdf"
        generate_report_pdf(report, SettingsController.get_company(), pdf_path)
        assert pdf_path.exists() and pdf_path.stat().st_size > 1000

        xlsx_path = tmp_path / "rapport.xlsx"
        export_report(report, xlsx_path)
        assert xlsx_path.exists() and xlsx_path.stat().st_size > 1000

    def test_backup_created(self, fresh_db):
        self._sale()
        backup = create_backup()
        assert backup.exists()
        assert backup in list_backups()


# ------------------------------------------------------------------
# Utilisateurs
# ------------------------------------------------------------------
class TestUsers:
    def test_create_and_login(self, fresh_db):
        ensure_default_admin()
        UserController.create_user({
            "username": "caisse1", "full_name": "Caissier Un",
            "role": "caissier", "password": "secret",
        })
        user = authenticate("caisse1", "secret")
        assert user is not None and user.role == "caissier"

    def test_cannot_remove_last_admin(self, fresh_db):
        ensure_default_admin()
        admin = authenticate("admin", "admin123")
        with pytest.raises(ValueError):
            UserController.set_active(admin.id, False, admin)
        with pytest.raises(ValueError):
            UserController.delete_user(admin.id, admin)
