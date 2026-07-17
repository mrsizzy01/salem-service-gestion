"""Fenêtre principale : barre latérale, barre supérieure et pages."""

from __future__ import annotations

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QMainWindow, QMessageBox, QStackedWidget, QVBoxLayout, QWidget

from app.config import APP_NAME, ORG_NAME, ROLE_ADMIN
from app.controllers.user_controller import UserController
from app.utils import theme as theme_module
from app.utils.icons import icon
from app.views.dialogs import ChangePasswordDialog
from app.views.pages.audit_page import AuditPage
from app.views.pages.customers_page import CustomersPage
from app.views.pages.dashboard_page import DashboardPage
from app.views.pages.expenses_page import ExpensesPage
from app.views.pages.invoicing_page import InvoicingPage
from app.views.pages.products_page import ProductsPage
from app.views.pages.reports_page import ReportsPage
from app.views.pages.settings_page import SettingsPage
from app.views.pages.stock_page import StockPage
from app.views.pages.suppliers_page import SuppliersPage
from app.views.pages.users_page import UsersPage
from app.views.widgets import Sidebar, TopBar

# Définition des modules : clé → (titre, icône, classe, admin uniquement).
PAGES = {
    "dashboard": ("Tableau de bord", "dashboard", DashboardPage, False),
    "invoicing": ("Facturation", "invoice", InvoicingPage, False),
    "products": ("Produits", "box", ProductsPage, False),
    "stock": ("Stock", "stock", StockPage, False),
    "customers": ("Clients", "customers", CustomersPage, False),
    "suppliers": ("Fournisseurs", "suppliers", SuppliersPage, True),
    "expenses": ("Dépenses", "expenses", ExpensesPage, True),
    "reports": ("Rapports", "reports", ReportsPage, False),
    "users": ("Utilisateurs", "users", UsersPage, True),
    "audit": ("Journal", "history", AuditPage, True),
    "settings": ("Paramètres", "settings", SettingsPage, True),
}


class MainWindow(QMainWindow):
    """Fenêtre principale de l'application."""

    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.was_logout = False  # vrai si fermeture suite à « Déconnexion »
        self.settings = QSettings(ORG_NAME, APP_NAME)
        self.theme = self.settings.value("theme", theme_module.THEME_LIGHT)

        self.setWindowTitle(APP_NAME)
        self.resize(1280, 800)
        self.setMinimumSize(1024, 640)

        # ---- Structure générale --------------------------------------
        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.setCentralWidget(central)

        self.sidebar = Sidebar()
        root.addWidget(self.sidebar)

        right = QFrame()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        self.topbar = TopBar()
        right_layout.addWidget(self.topbar)
        self.stack = QStackedWidget()
        right_layout.addWidget(self.stack, 1)
        root.addWidget(right, 1)

        # ---- Pages accessibles selon le rôle --------------------------
        self.pages: dict[str, QWidget] = {}
        self.icon_map: dict[str, str] = {}
        is_admin = user.role == ROLE_ADMIN
        for key, (title, icon_name, page_class, admin_only) in PAGES.items():
            if admin_only and not is_admin:
                continue
            page = page_class(user)
            self.stack.addWidget(page)
            self.pages[key] = page
            self.icon_map[key] = icon_name
            self.sidebar.add_page(key, title, icon_name)

        # ---- Connexions -------------------------------------------------
        self.sidebar.page_requested.connect(self.show_page)
        self.topbar.search_changed.connect(self._on_search)
        self.topbar.theme_toggle_requested.connect(self._toggle_theme)
        self.topbar.logout_requested.connect(self._logout)
        self.topbar.set_user(user.full_name or user.username, user.role)

        self.apply_theme()
        self.show_page("dashboard")

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------
    def show_page(self, key: str) -> None:
        """Affiche la page demandée et la recharge."""
        page = self.pages.get(key)
        if page is None:
            return
        self.stack.setCurrentWidget(page)
        self.sidebar.set_current(key)
        self.topbar.title_label.setText(PAGES[key][0])
        self.topbar.search_edit.clear()
        page.refresh()

    def _on_search(self, text: str) -> None:
        """Transmet la recherche globale à la page courante."""
        page = self.stack.currentWidget()
        if hasattr(page, "set_search"):
            page.set_search(text)

    # ------------------------------------------------------------------
    # Thème
    # ------------------------------------------------------------------
    def apply_theme(self) -> None:
        """Applique le thème courant à toute l'application."""
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app:
            app.setStyleSheet(theme_module.get_stylesheet(self.theme))
        dark = self.theme == theme_module.THEME_DARK
        self.topbar.set_theme_icon(dark)
        icon_color = "#B0B0B5" if dark else "#55555A"
        self.sidebar.refresh_icons(icon_color, self.icon_map)

    def _toggle_theme(self) -> None:
        """Bascule entre thème clair et thème sombre (persistant)."""
        self.theme = (theme_module.THEME_DARK if self.theme == theme_module.THEME_LIGHT
                      else theme_module.THEME_LIGHT)
        self.settings.setValue("theme", self.theme)
        self.apply_theme()

    # ------------------------------------------------------------------
    # Session
    # ------------------------------------------------------------------
    def _logout(self) -> None:
        """Ferme la session et revient à l'écran de connexion."""
        self.was_logout = True
        self.close()

    def change_password(self) -> None:
        """Permet à l'utilisateur connecté de changer son mot de passe."""
        dialog = ChangePasswordDialog(self)
        if dialog.exec():
            data = dialog.data()
            try:
                UserController.change_own_password(self.user.id, data["old"], data["new"])
            except ValueError as exc:
                QMessageBox.warning(self, "Mot de passe", str(exc))
                return
            QMessageBox.information(self, "Mot de passe", "Mot de passe modifié.")
