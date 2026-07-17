"""Page Paramètres : entreprise, logo, devise, sauvegarde / restauration."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.controllers.settings_controller import SettingsController
from app.services.backup_service import create_backup, restore_backup
from app.views.pages.base_page import BasePage


class SettingsPage(BasePage):
    """Configuration de l'entreprise et des données."""

    def __init__(self, user, parent=None):
        super().__init__("Paramètres", user, parent)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        container = QWidget()
        scroll_layout = QVBoxLayout(container)
        scroll_layout.setSpacing(14)
        scroll.setWidget(container)
        self.main_layout.addWidget(scroll, 1)

        # ---- Groupe Entreprise ------------------------------------------
        company_group = QGroupBox("Informations de l'entreprise")
        form = QFormLayout(company_group)
        form.setSpacing(10)
        self.name_edit = QLineEdit()
        self.address_edit = QLineEdit()
        self.phone_edit = QLineEdit()
        self.email_edit = QLineEdit()
        self.currency_edit = QLineEdit()
        self.currency_edit.setMaximumWidth(120)
        self.currency_edit.setPlaceholderText("FCFA, €, $…")
        self.thanks_edit = QLineEdit()
        form.addRow("Nom de l'entreprise", self.name_edit)
        form.addRow("Adresse", self.address_edit)
        form.addRow("Téléphone", self.phone_edit)
        form.addRow("Email", self.email_edit)
        form.addRow("Devise", self.currency_edit)
        form.addRow("Message de remerciement", self.thanks_edit)

        # Logo.
        logo_row = QHBoxLayout()
        self.logo_preview = QLabel("Aucun logo")
        self.logo_preview.setFixedSize(90, 90)
        self.logo_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo_preview.setStyleSheet("border: 1px dashed #B0B0B5; border-radius: 10px;")
        choose_logo = QPushButton("Choisir un logo…")
        choose_logo.clicked.connect(self._choose_logo)
        logo_row.addWidget(self.logo_preview)
        logo_row.addWidget(choose_logo)
        logo_row.addStretch()
        form.addRow("Logo", logo_row)

        save_button = QPushButton("💾 Enregistrer les paramètres")
        save_button.setMinimumHeight(38)
        save_button.setObjectName("PrimaryButton")
        save_button.clicked.connect(self._save)
        form.addRow("", save_button)
        scroll_layout.addWidget(company_group)

        # ---- Groupe Sauvegarde -------------------------------------------
        data_group = QGroupBox("Sauvegarde et restauration de la base de données")
        data_layout = QVBoxLayout(data_group)
        data_layout.setSpacing(8)
        backup_button = QPushButton("💾 Sauvegarder maintenant")
        backup_button.setMinimumHeight(36)
        backup_button.clicked.connect(self._backup)
        restore_button = QPushButton("♻ Restaurer depuis un fichier…")
        restore_button.setMinimumHeight(36)
        restore_button.clicked.connect(self._restore)
        note = QLabel("La restauration remplace les données actuelles "
                      "(une copie de sécurité est créée) puis nécessite un redémarrage.")
        note.setObjectName("muted")
        note.setWordWrap(True)
        data_layout.addWidget(backup_button)
        data_layout.addWidget(restore_button)
        data_layout.addWidget(note)
        scroll_layout.addWidget(data_group)
        scroll_layout.addStretch()

        self._logo_path = ""
        self.refresh()

    # ------------------------------------------------------------------
    # Données
    # ------------------------------------------------------------------
    def refresh(self) -> None:
        """Charge les paramètres actuels dans le formulaire."""
        company = SettingsController.get_company()
        self._logo_path = company.get("logo_path", "")
        self.name_edit.setText(company.get("name", ""))
        self.address_edit.setText(company.get("address", ""))
        self.phone_edit.setText(company.get("phone", ""))
        self.email_edit.setText(company.get("email", ""))
        self.currency_edit.setText(company.get("currency", ""))
        self.thanks_edit.setText(company.get("thanks_message", ""))
        self._update_logo_preview()

    def _update_logo_preview(self) -> None:
        """Affiche la miniature du logo."""
        if self._logo_path and Path(self._logo_path).exists():
            pixmap = QPixmap(self._logo_path)
            if not pixmap.isNull():
                self.logo_preview.setPixmap(pixmap.scaled(
                    84, 84, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation))
                return
        self.logo_preview.setText("Aucun logo")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _choose_logo(self) -> None:
        """Sélectionne et importe un logo."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Choisir un logo", "", "Images (*.png *.jpg *.jpeg *.webp)"
        )
        if path:
            self._logo_path = SettingsController.import_logo(path)
            self._update_logo_preview()

    def _save(self) -> None:
        """Enregistre les paramètres de l'entreprise."""
        data = {
            "name": self.name_edit.text() or "Ma Maison de Vente",
            "address": self.address_edit.text(),
            "phone": self.phone_edit.text(),
            "email": self.email_edit.text(),
            "currency": self.currency_edit.text() or "FCFA",
            "thanks_message": self.thanks_edit.text() or "Merci de votre confiance !",
            "logo_path": self._logo_path,
        }
        SettingsController.update_company(data, self.user)
        QMessageBox.information(self, "Paramètres",
                                "Paramètres enregistrés.\n"
                                "La nouvelle devise s'appliquera aux prochains écrans ouverts.")

    def _backup(self) -> None:
        """Crée une sauvegarde horodatée de la base."""
        try:
            path = create_backup()
        except Exception as exc:
            self.show_error(f"Sauvegarde impossible :\n{exc}")
            return
        QMessageBox.information(self, "Sauvegarde", f"Sauvegarde créée :\n{path}")

    def _restore(self) -> None:
        """Restaure la base depuis un fichier de sauvegarde."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Restaurer une sauvegarde", "", "Base SQLite (*.db *.sqlite *.sqlite3)"
        )
        if not path:
            return
        if not self.confirm("Restaurer cette sauvegarde ?\n"
                            "Les données actuelles seront remplacées et "
                            "l'application devra être redémarrée."):
            return
        try:
            restore_backup(path)
        except Exception as exc:
            self.show_error(f"Restauration impossible :\n{exc}")
            return
        QMessageBox.information(
            self, "Restauration",
            "Restauration terminée.\nVeuillez fermer puis relancer l'application.")
