"""Boîtes de dialogue (formulaires) de l'application.

Chaque dialogue :
- valide les saisies avant d'accepter ;
- expose les données via ``data()`` ou un attribut dédié ;
- n'appelle jamais directement la base : la page appelante utilise les
  contrôleurs.
"""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QDateTime, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDateTimeEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from app.controllers.expense_controller import EXPENSE_CATEGORIES
from app.controllers.product_controller import ProductController
from app.utils.helpers import format_money


# ------------------------------------------------------------------
# Base commune
# ------------------------------------------------------------------
class FormDialog(QDialog):
    """Dialogue de formulaire générique avec boutons OK / Annuler."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(580)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(20, 20, 20, 20)
        self._layout.setSpacing(14)
        self.form = QFormLayout()
        self.form.setSpacing(14)
        self.form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self._layout.addLayout(self.form)
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.button(QDialogButtonBox.StandardButton.Save).setText("Enregistrer")
        save_btn = self.buttons.button(QDialogButtonBox.StandardButton.Save)
        save_btn.setMinimumHeight(38)
        save_btn.setMinimumWidth(120)
        cancel_btn = self.buttons.button(QDialogButtonBox.StandardButton.Cancel)
        cancel_btn.setMinimumHeight(38)
        self.buttons.accepted.connect(self._on_accept)
        self.buttons.rejected.connect(self.reject)
        self._layout.addWidget(self.buttons)

    def _on_accept(self) -> None:
        """Valide le formulaire ; redéfini par les sous-classes."""
        self.accept()

    def warn(self, message: str) -> None:
        """Affiche un avertissement de validation."""
        QMessageBox.warning(self, self.windowTitle(), message)


def _double_spin(maximum: float = 999_999_999.0, decimals: int = 2) -> QDoubleSpinBox:
    """Crée un champ numérique standard."""
    spin = QDoubleSpinBox()
    spin.setRange(0.0, maximum)
    spin.setDecimals(decimals)
    spin.setGroupSeparatorShown(True)
    spin.setMinimumHeight(36)
    spin.setMinimumWidth(200)
    return spin


# ------------------------------------------------------------------
# Produit
# ------------------------------------------------------------------
class ProductDialog(FormDialog):
    """Formulaire d'ajout / modification d'un produit."""

    def __init__(self, parent=None, product: dict | None = None):
        super().__init__("Modifier le produit" if product else "Nouveau produit", parent)
        self._product = product
        self._image_path = product.get("image_path", "") if product else ""

        self.name_edit = QLineEdit(product["name"] if product else "")
        self.name_edit.setMinimumHeight(36)
        self.sku_edit = QLineEdit(product.get("sku", "") if product else "")
        self.sku_edit.setMinimumHeight(36)

        # Catégorie + création rapide.
        self.category_combo = QComboBox()
        self._load_categories(product.get("category_id") if product else None)
        category_row = QHBoxLayout()
        category_row.addWidget(self.category_combo, 1)
        add_cat = QPushButton("＋ Nouvelle")
        add_cat.setMinimumWidth(100)
        add_cat.setMinimumHeight(30)
        add_cat.setToolTip("Créer une nouvelle catégorie")
        add_cat.clicked.connect(self._create_category)
        category_row.addWidget(add_cat)
        category_widget = QDialog(self)  # simple conteneur
        category_widget.setLayout(category_row)
        category_row.setContentsMargins(0, 0, 0, 0)

        self.purchase_spin = _double_spin()
        self.sale_spin = _double_spin()
        self.stock_spin = _double_spin(decimals=0)
        self.threshold_spin = _double_spin(decimals=0)
        if product:
            self.purchase_spin.setValue(product.get("purchase_price", 0))
            self.sale_spin.setValue(product.get("sale_price", 0))
            self.stock_spin.setValue(product.get("stock_qty", 0))
            self.threshold_spin.setValue(product.get("alert_threshold", 5))
        else:
            self.threshold_spin.setValue(5)

        # Image du produit (facultative).
        self.image_label = QLabel("Aucune image")
        self.image_label.setObjectName("muted")
        self.image_preview = QLabel()
        self.image_preview.setFixedSize(64, 64)
        self.image_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_preview.setStyleSheet("border: 1px dashed #B0B0B5; border-radius: 8px;")
        self._update_image_preview()
        image_button = QPushButton("Choisir une image…")
        image_button.clicked.connect(self._choose_image)
        image_row = QHBoxLayout()
        image_row.addWidget(self.image_preview)
        image_row.addWidget(self.image_label, 1)
        image_row.addWidget(image_button)

        self.form.addRow("Nom *", self.name_edit)
        self.form.addRow("Référence", self.sku_edit)
        self.form.addRow("Catégorie", category_widget)
        self.form.addRow("Prix d'achat", self.purchase_spin)
        self.form.addRow("Prix de vente", self.sale_spin)
        self.form.addRow("Stock initial" if not product else "Stock", self.stock_spin)
        self.form.addRow("Seuil d'alerte", self.threshold_spin)
        self.form.addRow("Image", image_row)

    def _load_categories(self, selected_id: int | None = None) -> None:
        """Remplit la liste des catégories."""
        self.category_combo.clear()
        self.category_combo.addItem("— Sans catégorie —", None)
        for cat in ProductController.list_categories():
            self.category_combo.addItem(cat["name"], cat["id"])
        if selected_id:
            index = self.category_combo.findData(selected_id)
            if index >= 0:
                self.category_combo.setCurrentIndex(index)

    def _create_category(self) -> None:
        """Crée une catégorie à la volée depuis le formulaire."""
        from PySide6.QtWidgets import QInputDialog

        name, ok = QInputDialog.getText(self, "Nouvelle catégorie", "Nom de la catégorie :")
        if ok and name.strip():
            cat = ProductController.create_category(name.strip())
            self._load_categories(cat["id"])

    def _choose_image(self) -> None:
        """Sélectionne une image et la copie dans le dossier applicatif."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Image du produit", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp)"
        )
        if path:
            self._image_path = ProductController.import_image(path)
            self._update_image_preview()

    def _update_image_preview(self) -> None:
        """Met à jour la miniature et le libellé de l'image."""
        if self._image_path:
            pixmap = QPixmap(self._image_path)
            if not pixmap.isNull():
                self.image_preview.setPixmap(pixmap.scaled(
                    60, 60, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation))
                self.image_label.setText("Image sélectionnée")
                return
        self.image_label.setText("Aucune image")

    def _on_accept(self) -> None:
        if not self.name_edit.text().strip():
            self.warn("Le nom du produit est obligatoire.")
            return
        self.accept()

    def data(self) -> dict:
        """Retourne les données du formulaire."""
        return {
            "name": self.name_edit.text(),
            "sku": self.sku_edit.text(),
            "category_id": self.category_combo.currentData(),
            "purchase_price": self.purchase_spin.value(),
            "sale_price": self.sale_spin.value(),
            "stock_qty": self.stock_spin.value(),
            "alert_threshold": self.threshold_spin.value(),
            "image_path": self._image_path,
        }


# ------------------------------------------------------------------
# Mouvement de stock (entrée / sortie) et inventaire
# ------------------------------------------------------------------
class StockMovementDialog(FormDialog):
    """Formulaire d'entrée ou de sortie de stock."""

    def __init__(self, move_type: str, products: list[dict], parent=None,
                 product_id: int | None = None):
        title = "Entrée de stock" if move_type == "entrée" else "Sortie de stock"
        super().__init__(title, parent)
        self.move_type = move_type

        self.product_combo = QComboBox()
        for p in products:
            self.product_combo.addItem(f"{p['name']}  (stock : {p['stock_qty']:g})", p["id"])
        if product_id:
            index = self.product_combo.findData(product_id)
            if index >= 0:
                self.product_combo.setCurrentIndex(index)
        self.qty_spin = _double_spin(maximum=999_999_999.0, decimals=2)
        self.qty_spin.setValue(1)
        self.reason_edit = QLineEdit()
        self.reason_edit.setPlaceholderText(
            "Ex. : livraison fournisseur" if move_type == "entrée" else "Ex. : casse, usage interne")

        self.form.addRow("Produit *", self.product_combo)
        self.form.addRow("Quantité *", self.qty_spin)
        self.form.addRow("Motif", self.reason_edit)

    def _on_accept(self) -> None:
        if self.product_combo.currentData() is None:
            self.warn("Aucun produit sélectionné.")
            return
        if self.qty_spin.value() <= 0:
            self.warn("La quantité doit être supérieure à zéro.")
            return
        self.accept()

    def data(self) -> dict:
        return {
            "product_id": self.product_combo.currentData(),
            "quantity": self.qty_spin.value(),
            "reason": self.reason_edit.text(),
        }


class StockAdjustDialog(FormDialog):
    """Ajustement d'inventaire : fixe le stock à une valeur exacte."""

    def __init__(self, products: list[dict], parent=None, product_id: int | None = None):
        super().__init__("Ajustement d'inventaire", parent)
        self.product_combo = QComboBox()
        for p in products:
            self.product_combo.addItem(f"{p['name']}  (stock actuel : {p['stock_qty']:g})", p["id"])
        if product_id:
            index = self.product_combo.findData(product_id)
            if index >= 0:
                self.product_combo.setCurrentIndex(index)
        self.qty_spin = _double_spin(decimals=2)
        self.reason_edit = QLineEdit("Inventaire physique")
        self.form.addRow("Produit *", self.product_combo)
        self.form.addRow("Nouveau stock *", self.qty_spin)
        self.form.addRow("Motif", self.reason_edit)

    def _on_accept(self) -> None:
        if self.product_combo.currentData() is None:
            self.warn("Aucun produit sélectionné.")
            return
        self.accept()

    def data(self) -> dict:
        return {
            "product_id": self.product_combo.currentData(),
            "quantity": self.qty_spin.value(),
            "reason": self.reason_edit.text(),
        }


# ------------------------------------------------------------------
# Client / Fournisseur (formulaires identiques)
# ------------------------------------------------------------------
class PersonDialog(FormDialog):
    """Formulaire générique client ou fournisseur."""

    def __init__(self, kind: str, parent=None, person: dict | None = None):
        super().__init__(f"{'Modifier' if person else 'Nouveau'} {kind}", parent)
        self.kind = kind
        person = person or {}

        self.name_edit = QLineEdit(person.get("name", ""))
        self.name_edit.setMinimumHeight(36)
        self.phone_edit = QLineEdit(person.get("phone", ""))
        self.phone_edit.setMinimumHeight(36)
        self.email_edit = QLineEdit(person.get("email", ""))
        self.email_edit.setMinimumHeight(36)
        self.address_edit = QLineEdit(person.get("address", ""))
        self.address_edit.setMinimumHeight(36)

        # Nouveaux champs d'adresse détaillés
        self.avenue_edit = QLineEdit(person.get("avenue", ""))
        self.avenue_edit.setMinimumHeight(36)
        self.quartier_edit = QLineEdit(person.get("quartier", ""))
        self.quartier_edit.setMinimumHeight(36)
        self.commune_edit = QLineEdit(person.get("commune", ""))
        self.commune_edit.setMinimumHeight(36)
        self.city_edit = QLineEdit(person.get("city", "Lubumbashi"))
        self.city_edit.setMinimumHeight(36)
        self.province_edit = QLineEdit(person.get("province", "Haut-Katanga"))
        self.province_edit.setMinimumHeight(36)

        self.form.addRow("Nom *", self.name_edit)
        self.form.addRow("Téléphone", self.phone_edit)
        self.form.addRow("Email", self.email_edit)
        self.form.addRow("Adresse (Générale)", self.address_edit)
        self.form.addRow("Avenue", self.avenue_edit)
        self.form.addRow("Quartier", self.quartier_edit)
        self.form.addRow("Commune", self.commune_edit)
        self.form.addRow("Ville", self.city_edit)
        self.form.addRow("Province", self.province_edit)

        # Limite de crédit uniquement pour les clients
        if kind == "client":
            self.credit_spin = _double_spin(maximum=999_999_999.0, decimals=2)
            self.credit_spin.setValue(person.get("credit_limit", 0.0))
            self.form.addRow("Limite de crédit", self.credit_spin)

    def _on_accept(self) -> None:
        if not self.name_edit.text().strip():
            self.warn("Le nom est obligatoire.")
            return
        self.accept()

    def data(self) -> dict:
        data = {
            "name": self.name_edit.text(),
            "phone": self.phone_edit.text(),
            "email": self.email_edit.text(),
            "address": self.address_edit.text(),
            "avenue": self.avenue_edit.text(),
            "quartier": self.quartier_edit.text(),
            "commune": self.commune_edit.text(),
            "city": self.city_edit.text(),
            "province": self.province_edit.text(),
        }
        if self.kind == "client":
            data["credit_limit"] = self.credit_spin.value()
        return data


# ------------------------------------------------------------------
# Dépense
# ------------------------------------------------------------------
class ExpenseDialog(FormDialog):
    """Formulaire de dépense."""

    def __init__(self, parent=None, expense: dict | None = None):
        super().__init__("Modifier la dépense" if expense else "Nouvelle dépense", parent)
        self.label_edit = QLineEdit(expense.get("label", "") if expense else "")
        self.label_edit.setMinimumHeight(36)
        self.label_edit.setPlaceholderText("Ex. : Achat fournitures")
        self.category_combo = QComboBox()
        self.category_combo.setEditable(True)
        self.category_combo.setMinimumHeight(36)
        self.category_combo.addItems(EXPENSE_CATEGORIES)
        if expense:
            self.category_combo.setCurrentText(expense.get("category", "Divers"))
        self.amount_spin = _double_spin()
        if expense:
            self.amount_spin.setValue(expense.get("amount", 0))
        self.date_edit = QDateTimeEdit(QDateTime.currentDateTime())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd/MM/yyyy HH:mm")
        self.date_edit.setMinimumHeight(36)
        if expense and expense.get("spent_at"):
            self.date_edit.setDateTime(QDateTime(expense["spent_at"]))
        self.note_edit = QPlainTextEdit(expense.get("note", "") if expense else "")
        self.note_edit.setMinimumHeight(80)
        self.note_edit.setMaximumHeight(110)
        self.note_edit.setPlaceholderText("Remarques supplémentaires (facultatif)")

        self.form.addRow("Libellé *", self.label_edit)
        self.form.addRow("Catégorie", self.category_combo)
        self.form.addRow("Montant *", self.amount_spin)
        self.form.addRow("Date", self.date_edit)
        self.form.addRow("Note", self.note_edit)

    def _on_accept(self) -> None:
        if not self.label_edit.text().strip():
            self.warn("Le libellé est obligatoire.")
            return
        if self.amount_spin.value() <= 0:
            self.warn("Le montant doit être supérieur à zéro.")
            return
        self.accept()

    def data(self) -> dict:
        return {
            "label": self.label_edit.text(),
            "category": self.category_combo.currentText(),
            "amount": self.amount_spin.value(),
            "spent_at": self.date_edit.dateTime().toPython(),
            "note": self.note_edit.toPlainText(),
        }


# ------------------------------------------------------------------
# Utilisateur
# ------------------------------------------------------------------
class UserDialog(FormDialog):
    """Formulaire de création / modification d'un utilisateur."""

    def __init__(self, parent=None, user: dict | None = None):
        super().__init__("Modifier l'utilisateur" if user else "Nouvel utilisateur", parent)
        self._user = user
        self.username_edit = QLineEdit(user.get("username", "") if user else "")
        self.username_edit.setEnabled(user is None)  # identifiant immuable
        self.username_edit.setMinimumHeight(36)
        self.full_name_edit = QLineEdit(user.get("full_name", "") if user else "")
        self.full_name_edit.setMinimumHeight(36)
        self.role_combo = QComboBox()
        self.role_combo.setMinimumHeight(36)
        self.role_combo.addItem("Caissier", "caissier")
        self.role_combo.addItem("Administrateur", "admin")
        if user:
            index = self.role_combo.findData(user.get("role", "caissier"))
            if index >= 0:
                self.role_combo.setCurrentIndex(index)
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setMinimumHeight(36)
        self.password_edit.setPlaceholderText(
            "Mot de passe (min. 4 caractères)" if user is None
            else "Laisser vide pour ne pas changer")

        self.form.addRow("Nom d'utilisateur *", self.username_edit)
        self.form.addRow("Nom complet", self.full_name_edit)
        self.form.addRow("Rôle", self.role_combo)
        self.form.addRow("Mot de passe" + ("" if user else " *"), self.password_edit)

    def _on_accept(self) -> None:
        if self._user is None:
            if not self.username_edit.text().strip():
                self.warn("Le nom d'utilisateur est obligatoire.")
                return
            if len(self.password_edit.text()) < 4:
                self.warn("Le mot de passe doit contenir au moins 4 caractères.")
                return
        self.accept()

    def data(self) -> dict:
        return {
            "username": self.username_edit.text(),
            "full_name": self.full_name_edit.text(),
            "role": self.role_combo.currentData(),
            "password": self.password_edit.text(),
        }


class ChangePasswordDialog(FormDialog):
    """Changement de son propre mot de passe."""

    def __init__(self, parent=None):
        super().__init__("Changer mon mot de passe", parent)
        self.old_edit = QLineEdit()
        self.old_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_edit = QLineEdit()
        self.new_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_edit = QLineEdit()
        self.confirm_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.form.addRow("Ancien mot de passe", self.old_edit)
        self.form.addRow("Nouveau mot de passe", self.new_edit)
        self.form.addRow("Confirmation", self.confirm_edit)

    def _on_accept(self) -> None:
        if len(self.new_edit.text()) < 4:
            self.warn("Le nouveau mot de passe doit contenir au moins 4 caractères.")
            return
        if self.new_edit.text() != self.confirm_edit.text():
            self.warn("La confirmation ne correspond pas.")
            return
        self.accept()

    def data(self) -> dict:
        return {"old": self.old_edit.text(), "new": self.new_edit.text()}


# ------------------------------------------------------------------
# Aperçu de facture après validation
# ------------------------------------------------------------------
class InvoicePreviewDialog(QDialog):
    """Résumé d'une facture validée : aperçu, impression, ouverture du PDF."""

    def __init__(self, sale: dict, company: dict, parent=None):
        super().__init__(parent)
        self.sale = sale
        self.company = company
        self.setWindowTitle(f"Facture {sale['number']} enregistrée")
        self.setModal(True)
        self.setMinimumWidth(460)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        title = QLabel(f"✅ Facture {sale['number']} enregistrée")
        title.setObjectName("title")
        layout.addWidget(title)

        currency = company.get("currency", "FCFA")
        details = QLabel(
            f"Client : {sale.get('customer_name') or 'Client comptant'}    "
            f"Tél. : {sale.get('customer_phone') or '—'}\n"
            f"Articles : {len(sale['items'])}    "
            f"Total : {format_money(sale['total'], currency)}\n"
            f"Payé : {format_money(sale['amount_paid'], currency)}    "
            f"Reste : {format_money(sale['remaining'], currency)}"
        )
        details.setObjectName("muted")
        layout.addWidget(details)

        pdf_label = QLabel(f"PDF : {sale.get('pdf_path', '')}")
        pdf_label.setObjectName("muted")
        pdf_label.setWordWrap(True)
        layout.addWidget(pdf_label)

        buttons = QHBoxLayout()
        print_button = QPushButton("Aperçu / Imprimer")
        print_button.setObjectName("PrimaryButton")
        print_button.clicked.connect(self._print)
        open_button = QPushButton("Ouvrir le PDF")
        open_button.clicked.connect(self._open_pdf)
        close_button = QPushButton("Fermer")
        close_button.clicked.connect(self.accept)
        buttons.addWidget(print_button)
        buttons.addWidget(open_button)
        buttons.addStretch()
        buttons.addWidget(close_button)
        layout.addLayout(buttons)

    def _print(self) -> None:
        """Ouvre l'aperçu avant impression natif."""
        from app.views.printing import print_invoice

        print_invoice(self.sale, self.company, self)

    def _open_pdf(self) -> None:
        """Ouvre le PDF avec l'application par défaut du système."""
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        path = self.sale.get("pdf_path", "")
        if path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
