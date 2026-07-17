"""Test de fumée de l'interface graphique (mode Qt « offscreen »).

Instancie la fenêtre principale, navigue sur toutes les pages, bascule
le thème et ouvre les dialogues principaux — sans affichage réel.

Usage :  QT_QPA_PLATFORM=offscreen python tests/smoke_gui.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# Base temporaire isolée.
os.environ["GESTION_DATA_DIR"] = tempfile.mkdtemp(prefix="smoke_gui_")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtWidgets import QApplication  # noqa: E402

from app.controllers.product_controller import ProductController  # noqa: E402
from app.controllers.sale_controller import SaleController  # noqa: E402
from app.models.database import init_engine  # noqa: E402
from app.models.migrations import run_migrations  # noqa: E402
from app.services.auth_service import authenticate, ensure_default_admin  # noqa: E402
from app.views.main_window import MainWindow  # noqa: E402
from app.views.dialogs import (  # noqa: E402
    ChangePasswordDialog,
    ExpenseDialog,
    PersonDialog,
    ProductDialog,
    StockAdjustDialog,
    StockMovementDialog,
    UserDialog,
)


def main() -> int:
    """Exécute le test de fumée et affiche le résultat."""
    app = QApplication(sys.argv)
    engine = init_engine()
    run_migrations(engine)
    ensure_default_admin()

    # Données de test : catégorie, produits, une vente.
    cat = ProductController.create_category("Épicerie")
    product = ProductController.create_product({
        "name": "Sucre 1kg", "sku": "SUC-1", "category_id": cat["id"],
        "purchase_price": 600, "sale_price": 900, "stock_qty": 50,
    })
    SaleController.create_sale({
        "customer_name": "Client Démo", "customer_phone": "0600000000",
        "amount_paid": 900,
        "items": [{"product_id": product["id"], "name": product["name"],
                   "quantity": 1, "unit_price": 900, "is_manual": False}],
    })

    user = authenticate("admin", "admin123")
    assert user is not None

    # Fenêtre principale + navigation sur toutes les pages.
    window = MainWindow(user)
    window.show()
    for key in window.pages:
        window.show_page(key)
        app.processEvents()
    print(f"Pages OK : {', '.join(window.pages.keys())}")

    # Bascule de thème dans les deux sens.
    window._toggle_theme()
    app.processEvents()
    window._toggle_theme()
    app.processEvents()
    print("Thèmes OK")

    # Recherche globale sur les pages filtrables.
    for key in ("products", "invoicing", "customers", "audit"):
        window.show_page(key)
        window._on_search("test")
        app.processEvents()
    print("Recherche OK")

    # Instanciation des dialogues (sans les exécuter).
    dialogs = [
        ProductDialog(window),
        ProductDialog(window, ProductController.get_product(product["id"])),
        StockMovementDialog("entrée", ProductController.list_products(), window),
        StockMovementDialog("sortie", ProductController.list_products(), window),
        StockAdjustDialog(ProductController.list_products(), window),
        PersonDialog("client", window),
        PersonDialog("fournisseur", window),
        ExpenseDialog(window),
        UserDialog(window),
        ChangePasswordDialog(window),
    ]
    print(f"Dialogues OK : {len(dialogs)}")

    # Session caissier : pages restreintes.
    window.close()
    from app.controllers.user_controller import UserController

    UserController.create_user({"username": "caisse", "full_name": "Caissier",
                                "role": "caissier", "password": "1234"})
    cashier = authenticate("caisse", "1234")
    window2 = MainWindow(cashier)
    window2.show()
    for key in window2.pages:
        window2.show_page(key)
        app.processEvents()
    restricted = {"suppliers", "expenses", "users", "audit", "settings"}
    assert restricted.isdisjoint(window2.pages), "Pages admin visibles par le caissier !"
    print(f"Rôle caissier OK : {', '.join(window2.pages.keys())}")

    print("SMOKE GUI : SUCCÈS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
