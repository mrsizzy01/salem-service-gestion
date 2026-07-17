"""Page Facturation : création de factures et historique.

Processus de vente volontairement simple :
1. saisir le nom et le téléphone du client (sans enregistrement obligé) ;
2. ajouter des produits enregistrés OU manuels ;
3. vérifier totaux et paiement (reste calculé automatiquement) ;
4. Valider → vente enregistrée, stock mis à jour, numéro unique généré,
   facture PDF créée, aperçu avant impression proposé.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.config import ROLE_ADMIN, invoices_dir
from app.controllers.customer_controller import CustomerController
from app.controllers.product_controller import ProductController
from app.controllers.sale_controller import SaleController
from app.controllers.settings_controller import SettingsController
from app.services.pdf_service import generate_invoice_pdf
from app.utils.helpers import format_money, format_qty
from app.views.dialogs import InvoicePreviewDialog, ProductDialog
from app.views.pages.base_page import BasePage
from app.views.printing import print_invoice


class InvoicingPage(BasePage):
    """Module de facturation complet."""

    def __init__(self, user, parent=None):
        super().__init__("Facturation", user, parent)
        self.items: list[dict] = []  # lignes de la facture en cours
        self.company = SettingsController.get_company()
        self.currency = self.company.get("currency", "FCFA")

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_layout.addWidget(splitter, 1)

        # ==================================================================
        # Panneau gauche : nouvelle facture avec défilement sécurisé
        # ==================================================================
        left = QFrame()
        left.setObjectName("Card")
        left_outer_layout = QVBoxLayout(left)
        left_outer_layout.setContentsMargins(0, 0, 0, 0)
        left_outer_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        scroll_content = QWidget()
        scroll_content.setObjectName("LeftScrollContent")
        scroll_content.setStyleSheet("QWidget#LeftScrollContent { background: transparent; }")
        
        left_layout = QVBoxLayout(scroll_content)
        left_layout.setContentsMargins(18, 16, 18, 16)
        left_layout.setSpacing(12)

        new_label = QLabel("Nouvelle facture")
        new_label.setStyleSheet("font-weight: 700; font-size: 15px;")
        left_layout.addWidget(new_label)

        # ---- Scanneur de code-barres & Type de document ----
        scanner_layout = QHBoxLayout()
        self.barcode_input = QLineEdit()
        self.barcode_input.setPlaceholderText("Scanner code-barres ou SKU + Entrée...")
        self.barcode_input.setMinimumHeight(36)
        self.barcode_input.returnPressed.connect(self._on_barcode_scanned)
        
        self.doc_type_combo = QComboBox()
        self.doc_type_combo.addItems(["Facture", "Devis / Pro-forma"])
        self.doc_type_combo.setMinimumHeight(36)
        self.doc_type_combo.currentIndexChanged.connect(self._on_doc_type_changed)
        
        scanner_layout.addWidget(self.barcode_input, 3)
        scanner_layout.addWidget(self.doc_type_combo, 2)
        left_layout.addLayout(scanner_layout)

        # ---- Informations client (agencées de manière compacte) ------
        client_form = QFormLayout()
        client_form.setSpacing(8)

        # Choix rapide d'un client enregistré + sauvegarde facultative.
        customer_row = QHBoxLayout()
        self.customer_combo = QComboBox()
        self.customer_combo.setMinimumWidth(150)
        self.customer_combo.currentIndexChanged.connect(self._on_customer_chosen)
        save_customer_button = QPushButton("💾 Enregistrer ce client")
        save_customer_button.setToolTip("Enregistrer nom + téléphone dans la base (facultatif)")
        save_customer_button.clicked.connect(self._save_customer)
        customer_row.addWidget(self.customer_combo, 1)
        customer_row.addWidget(save_customer_button)
        customer_widget = QWidget()
        customer_widget.setLayout(customer_row)
        customer_row.setContentsMargins(0, 0, 0, 0)
        client_form.addRow("Client enregistré", customer_widget)

        # Saisie Nom et Téléphone sur une seule ligne horizontale
        row_fields = QHBoxLayout()
        self.customer_name = QLineEdit()
        self.customer_name.setPlaceholderText("Nom du client (facultatif)")
        self.customer_name.setMinimumHeight(36)
        self.customer_phone = QLineEdit()
        self.customer_phone.setPlaceholderText("Téléphone (facultatif)")
        self.customer_phone.setMinimumHeight(36)
        row_fields.addWidget(self.customer_name, 3)
        row_fields.addWidget(self.customer_phone, 2)
        client_form.addRow("Client / Tél.", row_fields)
        left_layout.addLayout(client_form)

        # ---- Ajout de produits ----------------------------------------
        self.add_tabs = QTabWidget()
        left_layout.addWidget(self.add_tabs)

        # Onglet 1 : produit enregistré.
        registered_tab = QWidget()
        registered_layout = QVBoxLayout(registered_tab)
        reg_form = QFormLayout()
        reg_form.setSpacing(8)
        self.product_combo = QComboBox()
        self.product_combo.setMinimumHeight(36)
        self.product_combo.currentIndexChanged.connect(self._on_product_chosen)
        
        self.reg_qty = QDoubleSpinBox()
        self.reg_qty.setRange(0.01, 999_999)
        self.reg_qty.setValue(1)
        self.reg_qty.setDecimals(2)
        self.reg_qty.setMinimumHeight(36)
        
        self.reg_price = QDoubleSpinBox()
        self.reg_price.setRange(0, 999_999_999)
        self.reg_price.setDecimals(2)
        self.reg_price.setGroupSeparatorShown(True)
        self.reg_price.setMinimumHeight(36)
        
        reg_form.addRow("Produit", self.product_combo)
        
        # Qté et PU côte à côte
        reg_qty_price_layout = QHBoxLayout()
        reg_qty_price_layout.addWidget(self.reg_qty, 1)
        reg_qty_price_layout.addWidget(self.reg_price, 1)
        reg_form.addRow("Qté / P.U.", reg_qty_price_layout)
        
        registered_layout.addLayout(reg_form)
        self.add_tabs.addTab(registered_tab, "Produit enregistré")

        # Onglet 2 : produit manuel.
        manual_tab = QWidget()
        manual_layout = QVBoxLayout(manual_tab)
        man_form = QFormLayout()
        man_form.setSpacing(8)
        self.man_name = QLineEdit()
        self.man_name.setPlaceholderText("Nom du produit")
        self.man_name.setMinimumHeight(36)
        
        self.man_qty = QDoubleSpinBox()
        self.man_qty.setRange(0.01, 999_999)
        self.man_qty.setValue(1)
        self.man_qty.setDecimals(2)
        self.man_qty.setMinimumHeight(36)
        
        self.man_price = QDoubleSpinBox()
        self.man_price.setRange(0, 999_999_999)
        self.man_price.setDecimals(2)
        self.man_price.setGroupSeparatorShown(True)
        self.man_price.setMinimumHeight(36)
        
        man_form.addRow("Produit", self.man_name)
        
        # Qté et PU côte à côte
        man_qty_price_layout = QHBoxLayout()
        man_qty_price_layout.addWidget(self.man_qty, 1)
        man_qty_price_layout.addWidget(self.man_price, 1)
        man_form.addRow("Qté / P.U.", man_qty_price_layout)
        
        manual_layout.addLayout(man_form)
        add_to_base = QPushButton("⬇ Ajouter ce produit à la base")
        add_to_base.setToolTip("Enregistre ce produit dans le catalogue (stock, prix…)")
        add_to_base.clicked.connect(self._add_manual_to_base)
        manual_layout.addWidget(add_to_base)
        self.add_tabs.addTab(manual_tab, "Produit manuel")

        add_line_button = QPushButton("＋ Ajouter à la facture")
        add_line_button.setObjectName("PrimaryButton")
        add_line_button.setCursor(Qt.CursorShape.PointingHandCursor)
        add_line_button.clicked.connect(self._add_line)
        left_layout.addWidget(add_line_button)

        # ---- Lignes de la facture ------------------------------------
        self.items_table = self.make_table(["Produit", "Qté", "P.U.", "Total"])
        self.items_table.setMinimumHeight(180)
        left_layout.addWidget(self.items_table, 1)
        remove_button = QPushButton("Retirer la ligne sélectionnée")
        remove_button.clicked.connect(self._remove_line)
        left_layout.addWidget(remove_button)

        # ---- Résumé des totaux et paiement (Section Horizontale Premium) -----
        totals_panel = QFrame()
        totals_panel.setFrameShape(QFrame.Shape.StyledPanel)
        totals_panel.setStyleSheet("""
            QFrame {
                background-color: rgba(128, 128, 128, 0.05);
                border: 1px solid rgba(128, 128, 128, 0.15);
                border-radius: 8px;
            }
        """)
        totals_layout = QHBoxLayout(totals_panel)
        totals_layout.setContentsMargins(12, 10, 12, 10)
        totals_layout.setSpacing(14)
        
        subtotal_widget = QVBoxLayout()
        subtotal_title = QLabel("SOUS-TOTAL")
        subtotal_title.setStyleSheet("font-size: 10px; font-weight: 600; color: #98989D;")
        self.subtotal_label = QLabel("—")
        self.subtotal_label.setStyleSheet("font-size: 14px; font-weight: 700;")
        subtotal_widget.addWidget(subtotal_title)
        subtotal_widget.addWidget(self.subtotal_label)
        
        total_widget = QVBoxLayout()
        total_title = QLabel("TOTAL À PAYER")
        total_title.setStyleSheet("font-size: 10px; font-weight: 600; color: #98989D;")
        self.total_label = QLabel("—")
        self.total_label.setStyleSheet("font-size: 16px; font-weight: 800; color: #0A84FF;")
        total_widget.addWidget(total_title)
        total_widget.addWidget(self.total_label)

        paid_widget = QVBoxLayout()
        paid_title = QLabel("MONTANT PAYÉ")
        paid_title.setStyleSheet("font-size: 10px; font-weight: 600; color: #98989D;")
        self.paid_spin = QDoubleSpinBox()
        self.paid_spin.setRange(0, 999_999_999)
        self.paid_spin.setDecimals(2)
        self.paid_spin.setGroupSeparatorShown(True)
        self.paid_spin.setMinimumHeight(36)
        self.paid_spin.setMinimumWidth(110)
        self.paid_spin.valueChanged.connect(self._update_totals)
        paid_widget.addWidget(paid_title)
        paid_widget.addWidget(self.paid_spin)

        remaining_widget = QVBoxLayout()
        remaining_title = QLabel("RESTE À PAYER")
        remaining_title.setStyleSheet("font-size: 10px; font-weight: 600; color: #98989D;")
        self.remaining_label = QLabel("—")
        self.remaining_label.setStyleSheet("font-size: 16px; font-weight: 800; color: #FF3B30;")
        remaining_widget.addWidget(remaining_title)
        remaining_widget.addWidget(self.remaining_label)
        
        totals_layout.addLayout(subtotal_widget, 1)
        totals_layout.addLayout(total_widget, 1)
        totals_layout.addLayout(paid_widget, 1)
        totals_layout.addLayout(remaining_widget, 1)
        
        left_layout.addWidget(totals_panel)

        # ---- Options de Paiement et d'Impression ----
        options_row = QHBoxLayout()
        
        pay_layout = QVBoxLayout()
        pay_label = QLabel("MODE DE PAIEMENT")
        pay_label.setStyleSheet("font-size: 10px; font-weight: 600; color: #98989D;")
        self.payment_combo = QComboBox()
        self.payment_combo.addItems(["Cash", "Mobile Money", "Chèque"])
        self.payment_combo.setMinimumHeight(36)
        pay_layout.addWidget(pay_label)
        pay_layout.addWidget(self.payment_combo)
        
        print_layout = QVBoxLayout()
        print_label = QLabel("FORMAT D'IMPRESSION")
        print_label.setStyleSheet("font-size: 10px; font-weight: 600; color: #98989D;")
        self.print_format_combo = QComboBox()
        self.print_format_combo.addItems(["A4", "Ticket (80mm)"])
        self.print_format_combo.setMinimumHeight(36)
        print_layout.addWidget(print_label)
        print_layout.addWidget(self.print_format_combo)
        
        options_row.addLayout(pay_layout, 1)
        options_row.addLayout(print_layout, 1)
        left_layout.addLayout(options_row)

        # ---- Validation -----------------------------------------------
        buttons_row = QHBoxLayout()
        self.validate_button = QPushButton("✔ Valider la facture")
        self.validate_button.setObjectName("PrimaryButton")
        self.validate_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.validate_button.clicked.connect(self._validate)
        reset_button = QPushButton("Réinitialiser")
        reset_button.clicked.connect(self._reset_form)
        buttons_row.addWidget(self.validate_button, 1)
        buttons_row.addWidget(reset_button)
        left_layout.addLayout(buttons_row)

        scroll.setWidget(scroll_content)
        left_outer_layout.addWidget(scroll)
        splitter.addWidget(left)

        # ==================================================================
        # Panneau droit : historique des factures
        # ==================================================================
        right = QFrame()
        right.setObjectName("Card")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(18, 16, 18, 16)
        right_layout.setSpacing(10)

        history_header = QHBoxLayout()
        history_label = QLabel("Historique des factures")
        history_label.setStyleSheet("font-weight: 700; font-size: 15px;")
        history_header.addWidget(history_label)
        history_header.addStretch()
        refresh_button = QPushButton("Actualiser")
        refresh_button.clicked.connect(self.refresh)
        history_header.addWidget(refresh_button)
        right_layout.addLayout(history_header)

        self.history_table = self.make_table(
            ["N°", "Date", "Client", "Total", "Payé", "Reste", "Statut"]
        )
        # Largeurs adaptées au contenu ; le nom du client occupe le reste.
        from PySide6.QtWidgets import QHeaderView

        header = self.history_table.horizontalHeader()
        for col in (0, 1, 3, 4, 5, 6):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        right_layout.addWidget(self.history_table, 1)

        history_buttons = QHBoxLayout()
        preview_button = QPushButton("👁 Aperçu / Imprimer")
        preview_button.clicked.connect(self._preview_selected)
        pdf_button = QPushButton("Ouvrir le PDF")
        pdf_button.clicked.connect(self._open_pdf_selected)
        self.cancel_button = QPushButton("Annuler la facture")
        self.cancel_button.setObjectName("DangerButton")
        self.cancel_button.clicked.connect(self._cancel_selected)
        self.cancel_button.setVisible(user.role == ROLE_ADMIN)
        
        self.convert_button = QPushButton("🔄 Convertir en Facture")
        self.convert_button.clicked.connect(self._convert_selected)
        self.convert_button.setVisible(False)
        
        history_buttons.addWidget(preview_button)
        history_buttons.addWidget(pdf_button)
        history_buttons.addWidget(self.convert_button)
        history_buttons.addWidget(self.cancel_button)
        history_buttons.addStretch()
        right_layout.addLayout(history_buttons)

        splitter.addWidget(right)
        splitter.setSizes([620, 680])

        self.history_table.itemSelectionChanged.connect(self._on_history_selection_changed)

        self._reload_products()
        self._reload_customers()
        self.refresh()

    # ==================================================================
    # Chargements
    # ==================================================================
    def _reload_products(self) -> None:
        """Recharge la liste des produits disponibles."""
        self._products = ProductController.list_products()
        self.product_combo.blockSignals(True)
        self.product_combo.clear()
        for p in self._products:
            self.product_combo.addItem(
                f"{p['name']}  —  stock : {format_qty(p['stock_qty'])}", p["id"])
        self.product_combo.blockSignals(False)
        self._on_product_chosen(0)

    def _reload_customers(self) -> None:
        """Recharge la liste des clients enregistrés (choix facultatif)."""
        self.customer_combo.blockSignals(True)
        self.customer_combo.clear()
        self.customer_combo.addItem("— Choisir un client enregistré (facultatif) —", None)
        for c in CustomerController.list_customers():
            self.customer_combo.addItem(f"{c['name']}  {c['phone']}", c["id"])
        self.customer_combo.blockSignals(False)

    # ==================================================================
    # Interactions du formulaire
    # ==================================================================
    def _on_customer_chosen(self, index: int) -> None:
        """Pré-remplit nom et téléphone depuis le client choisi."""
        customer_id = self.customer_combo.itemData(index)
        if not customer_id:
            return
        for c in CustomerController.list_customers():
            if c["id"] == customer_id:
                self.customer_name.setText(c["name"])
                self.customer_phone.setText(c["phone"])
                break

    def _save_customer(self) -> None:
        """Enregistre (facultativement) le client saisi sur la facture."""
        name = self.customer_name.text().strip()
        if not name:
            self.show_error("Saisissez d'abord le nom du client.")
            return
        try:
            CustomerController.save_customer(
                {"name": name, "phone": self.customer_phone.text()}, self.user)
        except ValueError as exc:
            self.show_error(str(exc))
            return
        self._reload_customers()
        QMessageBox.information(self, "Client", f"« {name} » enregistré dans la base.")

    def _on_product_chosen(self, index: int) -> None:
        """Pré-remplit le prix unitaire avec le prix de vente du produit."""
        product_id = self.product_combo.itemData(index)
        product = next((p for p in self._products if p["id"] == product_id), None)
        if product:
            self.reg_price.setValue(product["sale_price"])

    def _add_manual_to_base(self) -> None:
        """Enregistre le produit manuel dans le catalogue."""
        name = self.man_name.text().strip()
        if not name:
            self.show_error("Saisissez le nom du produit à enregistrer.")
            return
        dialog = ProductDialog(self, {
            "name": name, "sku": "", "category_id": None,
            "purchase_price": 0.0, "sale_price": self.man_price.value(),
            "stock_qty": 0.0, "alert_threshold": 5.0, "image_path": "",
        })
        if dialog.exec():
            try:
                product = ProductController.create_product(dialog.data(), self.user)
            except ValueError as exc:
                self.show_error(str(exc))
                return
            self._reload_products()
            # Sélectionne le produit fraîchement créé.
            index = self.product_combo.findData(product["id"])
            if index >= 0:
                self.product_combo.setCurrentIndex(index)
            QMessageBox.information(
                self, "Produit", f"« {product['name']} » ajouté à la base.\n"
                "Il est désormais sélectionné dans l'onglet « Produit enregistré ».")

    def _add_line(self) -> None:
        """Ajoute une ligne à la facture selon l'onglet actif."""
        if self.add_tabs.currentIndex() == 0:
            product_id = self.product_combo.currentData()
            product = next((p for p in self._products if p["id"] == product_id), None)
            if product is None:
                self.show_error("Aucun produit sélectionné. Créez d'abord un produit.")
                return
            item = {
                "product_id": product["id"],
                "name": product["name"],
                "quantity": self.reg_qty.value(),
                "unit_price": self.reg_price.value(),
                "is_manual": False,
            }
        else:
            if not self.man_name.text().strip():
                self.show_error("Saisissez le nom du produit manuel.")
                return
            item = {
                "product_id": None,
                "name": self.man_name.text().strip(),
                "quantity": self.man_qty.value(),
                "unit_price": self.man_price.value(),
                "is_manual": True,
            }

        # Fusionne avec une ligne identique existante.
        for existing in self.items:
            if (existing["product_id"] == item["product_id"]
                    and existing["name"] == item["name"]
                    and abs(existing["unit_price"] - item["unit_price"]) < 1e-9):
                existing["quantity"] += item["quantity"]
                break
        else:
            self.items.append(item)

        self._refresh_items_table()
        self.man_name.clear()

    def _remove_line(self) -> None:
        """Retire la ligne sélectionnée de la facture en cours."""
        row = self.items_table.currentRow()
        if 0 <= row < len(self.items):
            del self.items[row]
            self._refresh_items_table()

    def _refresh_items_table(self) -> None:
        """Réaffiche les lignes et recalcule les totaux."""
        self.items_table.setRowCount(len(self.items))
        for row, item in enumerate(self.items):
            total = item["quantity"] * item["unit_price"]
            values = [
                item["name"] + ("  (manuel)" if item["is_manual"] else ""),
                format_qty(item["quantity"]),
                format_money(item["unit_price"], self.currency),
                format_money(total, self.currency),
            ]
            for col, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if col > 0:
                    cell.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.items_table.setItem(row, col, cell)
        self._update_totals()

    def _update_totals(self) -> None:
        """Recalcule sous-total, total et reste à payer."""
        subtotal = sum(i["quantity"] * i["unit_price"] for i in self.items)
        subtotal = round(subtotal, 2)
        paid = self.paid_spin.value()
        remaining = max(0.0, round(subtotal - paid, 2))
        self.subtotal_label.setText(format_money(subtotal, self.currency))
        self.total_label.setText(format_money(subtotal, self.currency))
        self.remaining_label.setText(format_money(remaining, self.currency))
        self.remaining_label.setStyleSheet(
            "font-weight: 700; color: " + ("#FF3B30" if remaining > 0 else "#28A745"))

    def _reset_form(self) -> None:
        """Vide le formulaire pour une nouvelle facture."""
        self.items.clear()
        self.customer_name.clear()
        self.customer_phone.clear()
        self.customer_combo.setCurrentIndex(0)
        self.paid_spin.setValue(0)
        self._refresh_items_table()
        self._reload_products()

    # ==================================================================
    # Nouveaux modules : Code-barres, Devis et Caisse
    # ==================================================================
    def _on_barcode_scanned(self) -> None:
        """Recherche et ajoute automatiquement un produit par code-barres ou SKU."""
        text = self.barcode_input.text().strip()
        if not text:
            return
        
        product = None
        for p in self._products:
            p_barcode = str(p.get("barcode") or "").strip()
            p_sku = str(p.get("sku") or "").strip()
            if text.lower() in (p_barcode.lower(), p_sku.lower()):
                product = p
                break
        
        if product:
            item = {
                "product_id": product["id"],
                "name": product["name"],
                "quantity": 1.0,
                "unit_price": product["sale_price"],
                "is_manual": False,
            }
            for existing in self.items:
                if existing["product_id"] == item["product_id"]:
                    existing["quantity"] += 1.0
                    break
            else:
                self.items.append(item)
            
            self._refresh_items_table()
            self.barcode_input.clear()
            if hasattr(self.window(), "statusBar") and self.window().statusBar():
                self.window().statusBar().showMessage(f"Produit ajouté : {product['name']}", 2000)
        else:
            self.show_error(f"Aucun produit trouvé avec le code-barres/SKU : « {text} »")

    def _on_doc_type_changed(self, index: int) -> None:
        """Bascule le bouton de validation selon le type de document."""
        if index == 1:  # Devis
            self.validate_button.setText("✔ Générer le devis")
            self.paid_spin.setEnabled(False)
            self.paid_spin.setValue(0.0)
        else:
            self.validate_button.setText("✔ Valider la facture")
            self.paid_spin.setEnabled(True)

    def _on_history_selection_changed(self) -> None:
        """Affiche ou masque le bouton de conversion selon le document sélectionné."""
        row = self.history_table.currentRow()
        if row < 0:
            self.convert_button.setVisible(False)
            return
        statut_item = self.history_table.item(row, 6)
        if statut_item:
            status = statut_item.text().lower()
            self.convert_button.setVisible(status == "devis")

    def _convert_selected(self) -> None:
        """Convertit le devis sélectionné en facture validée."""
        sale_id = self.selected_row_id(self.history_table)
        if sale_id is None:
            self.show_error("Sélectionnez un devis à convertir.")
            return
        if not self.confirm("Convertir ce devis en facture ?\n"
                            "Cette action va diminuer les stocks et valider la vente."):
            return
        try:
            sale = SaleController.convert_devis_to_invoice(sale_id, self.user)
            QMessageBox.information(self, "Conversion", f"Le devis {sale['number']} a été converti en facture avec succès.")
        except Exception as exc:
            self.show_error(str(exc))
        self.refresh()

    # ==================================================================
    # Validation
    # ==================================================================
    def _validate(self) -> None:
        """Valide la facture : vente, stock, numéro, PDF, aperçu."""
        if not self.items:
            self.show_error("Ajoutez au moins un produit à la facture.")
            return
            
        doc_type = self.doc_type_combo.currentText()
        is_devis = doc_type == "Devis / Pro-forma"
        
        msg = ("Générer ce devis / pro-forma ?" if is_devis 
               else "Valider cette facture ?\nLa vente sera enregistrée et le stock mis à jour.")
        if not self.confirm(msg):
            return

        data = {
            "customer_name": self.customer_name.text(),
            "customer_phone": self.customer_phone.text(),
            "customer_id": self.customer_combo.currentData(),
            "amount_paid": 0.0 if is_devis else self.paid_spin.value(),
            "items": list(self.items),
            "status": "devis" if is_devis else "validée",
            "payment_method": self.payment_combo.currentText(),
        }
        try:
            sale = SaleController.create_sale(data, self.user)
        except ValueError as exc:
            self.show_error(str(exc))
            return

        # Génération du PDF A4.
        self.company = SettingsController.get_company()
        pdf_path = invoices_dir() / f"{sale['number']}.pdf"
        try:
            generate_invoice_pdf(sale, self.company, pdf_path)
            SaleController.set_pdf_path(sale["id"], str(pdf_path))
            sale["pdf_path"] = str(pdf_path)
        except Exception as exc:  # la vente reste valide même si le PDF échoue
            QMessageBox.warning(self, "PDF", f"Facture enregistrée mais le PDF a échoué :\n{exc}")

        # Impression / Aperçu automatique direct
        try:
            print_invoice(sale, self.company, self, self.print_format_combo.currentText())
        except Exception:
            pass

        # Boîte de dialogue de confirmation, puis remise à zéro.
        preview = InvoicePreviewDialog(sale, self.company, self)
        preview.exec()
        self._reset_form()
        self.refresh()

    # ==================================================================
    # Historique
    # ==================================================================
    def set_search(self, text: str) -> None:
        """Filtre l'historique par numéro ou client."""
        self._search = text
        self.refresh()

    def refresh(self) -> None:
        """Recharge l'historique des factures."""
        sales = SaleController.list_sales(search=self._search)
        self.history_table.setRowCount(len(sales))
        for row, sale in enumerate(sales):
            values = [
                sale["number"],
                sale["created_at"].strftime("%d/%m/%Y %H:%M"),
                sale["customer_name"] or "Client comptant",
                format_money(sale["total"], self.currency),
                format_money(sale["amount_paid"], self.currency),
                format_money(sale["remaining"], self.currency),
                sale["status"].capitalize(),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col in (3, 4, 5):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, sale["id"])
                if sale["status"] == "annulée":
                    item.setForeground(QColor("#8E8E93"))
                elif col == 5 and sale["remaining"] > 0:
                    item.setForeground(QColor("#FF3B30"))
                self.history_table.setItem(row, col, item)

    def _selected_sale(self) -> dict | None:
        """Retourne la facture complète de la ligne sélectionnée."""
        sale_id = self.selected_row_id(self.history_table)
        if sale_id is None:
            self.show_error("Sélectionnez une facture dans l'historique.")
            return None
        return SaleController.get_sale(sale_id)

    def _ensure_pdf(self, sale: dict) -> str:
        """Garantit l'existence du PDF d'une facture (le régénère si besoin)."""
        path = sale.get("pdf_path", "")
        if path and Path(path).exists():
            return path
        company = SettingsController.get_company()
        new_path = invoices_dir() / f"{sale['number']}.pdf"
        generate_invoice_pdf(sale, company, new_path)
        SaleController.set_pdf_path(sale["id"], str(new_path))
        return str(new_path)

    def _preview_selected(self) -> None:
        """Aperçu avant impression / réimpression d'une ancienne facture."""
        sale = self._selected_sale()
        if sale:
            try:
                sale["pdf_path"] = self._ensure_pdf(sale)
            except Exception:
                pass
            print_invoice(sale, SettingsController.get_company(), self, self.print_format_combo.currentText())

    def _open_pdf_selected(self) -> None:
        """Ouvre le PDF de la facture sélectionnée."""
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        sale = self._selected_sale()
        if not sale:
            return
        try:
            path = self._ensure_pdf(sale)
        except Exception as exc:
            self.show_error(f"Impossible de générer le PDF :\n{exc}")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def _cancel_selected(self) -> None:
        """Annule une facture (administrateur) et réapprovisionne le stock."""
        sale_id = self.selected_row_id(self.history_table)
        if sale_id is None:
            self.show_error("Sélectionnez une facture à annuler.")
            return
        if not self.confirm("Annuler cette facture ?\n"
                            "Les produits seront réintégrés dans le stock."):
            return
        try:
            SaleController.cancel_sale(sale_id, self.user)
        except ValueError as exc:
            self.show_error(str(exc))
        self.refresh()
