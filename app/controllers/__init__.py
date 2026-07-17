"""Couche contrôleurs : logique métier, indépendante de l'interface Qt.

Chaque contrôleur expose des méthodes de classe/statiques qui ouvrent
une session SQLAlchemy, réalisent l'opération dans une transaction,
journalisent l'action et retournent des dictionnaires simples.
"""

from app.controllers.customer_controller import CustomerController  # noqa: F401
from app.controllers.expense_controller import ExpenseController  # noqa: F401
from app.controllers.product_controller import ProductController  # noqa: F401
from app.controllers.report_controller import ReportController  # noqa: F401
from app.controllers.sale_controller import SaleController  # noqa: F401
from app.controllers.settings_controller import SettingsController  # noqa: F401
from app.controllers.stock_controller import StockController  # noqa: F401
from app.controllers.supplier_controller import SupplierController  # noqa: F401
from app.controllers.user_controller import UserController  # noqa: F401
