"""Écran de connexion professionnel — Salem Service."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QLinearGradient, QColor, QPainter, QBrush
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.services.auth_service import authenticate


# ---------------------------------------------------------------------------
# Widget de fond dégradé
# ---------------------------------------------------------------------------
class _GradientBg(QWidget):
    """Fond bleu dégradé diagonal."""

    def paintEvent(self, event):  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        grad = QLinearGradient(0, 0, self.width(), self.height())
        grad.setColorAt(0.0, QColor("#0D2149"))
        grad.setColorAt(0.5, QColor("#1A3C6E"))
        grad.setColorAt(1.0, QColor("#254F8F"))
        painter.fillRect(self.rect(), QBrush(grad))


# ---------------------------------------------------------------------------
# Dialogue principal
# ---------------------------------------------------------------------------
class LoginDialog(QDialog):
    """Écran de connexion sécurisée — Salem Service.

    En cas de succès, ``self.user`` contient l'utilisateur authentifié.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.user = None
        self.setWindowTitle("Salem Service — Connexion")
        self.setModal(True)
        self.setFixedSize(480, 580)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.CustomizeWindowHint
            | Qt.WindowType.WindowTitleHint
        )

        # ---- Fond dégradé -----------------------------------------------
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        bg = _GradientBg(self)
        bg_layout = QVBoxLayout(bg)
        bg_layout.setContentsMargins(0, 0, 0, 0)
        bg_layout.setSpacing(0)
        root_layout.addWidget(bg)

        # ---- Zone supérieure : logo + titre --------------------------------
        top_area = QWidget()
        top_area.setStyleSheet("background: transparent;")
        top_layout = QVBoxLayout(top_area)
        top_layout.setContentsMargins(40, 40, 40, 24)
        top_layout.setSpacing(6)
        top_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Pastille icône dorée
        badge = QLabel("S")
        badge.setFixedSize(72, 72)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet("""
            QLabel {
                background-color: #F5A200;
                color: #1A1A2E;
                border-radius: 36px;
                font-size: 36px;
                font-weight: 900;
            }
        """)
        badge_shadow = QGraphicsDropShadowEffect()
        badge_shadow.setBlurRadius(20)
        badge_shadow.setOffset(0, 4)
        badge_shadow.setColor(QColor(0, 0, 0, 120))
        badge.setGraphicsEffect(badge_shadow)

        company_label = QLabel("SALEM SERVICE")
        company_label.setStyleSheet(
            "color: #F5A200; font-size: 26px; font-weight: 900; "
            "letter-spacing: 2px; background: transparent;"
        )
        company_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        tagline = QLabel("Système de Gestion Commerciale")
        tagline.setStyleSheet(
            "color: #CBD5E1; font-size: 12px; background: transparent; letter-spacing: 0.5px;"
        )
        tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)

        separator = QFrame()
        separator.setFixedHeight(1)
        separator.setStyleSheet("background-color: rgba(245,162,0,0.35);")

        top_layout.addWidget(badge, alignment=Qt.AlignmentFlag.AlignCenter)
        top_layout.addSpacing(12)
        top_layout.addWidget(company_label)
        top_layout.addWidget(tagline)
        top_layout.addSpacing(16)
        top_layout.addWidget(separator)

        # ---- Carte formulaire blanche --------------------------------------
        card = QFrame()
        card.setObjectName("LoginCard")
        card.setStyleSheet("""
            QFrame#LoginCard {
                background-color: #FFFFFF;
                border-radius: 16px;
                border: none;
            }
        """)
        card_shadow = QGraphicsDropShadowEffect()
        card_shadow.setBlurRadius(32)
        card_shadow.setOffset(0, 8)
        card_shadow.setColor(QColor(0, 0, 0, 100))
        card.setGraphicsEffect(card_shadow)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(36, 32, 36, 32)
        card_layout.setSpacing(16)

        # Titre de la carte
        form_title = QLabel("Authentification")
        form_title.setStyleSheet(
            "color: #1A3C6E; font-size: 15px; font-weight: 700; background: transparent;"
        )

        # Champ utilisateur
        user_lbl = QLabel("Nom d'utilisateur")
        user_lbl.setStyleSheet("color: #374151; font-size: 12px; font-weight: 600; background: transparent;")
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Entrez votre identifiant…")
        self.username_edit.setMinimumHeight(44)
        self.username_edit.setStyleSheet("""
            QLineEdit {
                background: #F8FAFF;
                border: 1.5px solid #DDE3ED;
                border-radius: 10px;
                padding: 0 14px;
                font-size: 13px;
                color: #1A1A2E;
            }
            QLineEdit:focus {
                border: 2px solid #F5A200;
                background: #FFFDF5;
            }
        """)

        # Champ mot de passe
        pwd_lbl = QLabel("Mot de passe")
        pwd_lbl.setStyleSheet("color: #374151; font-size: 12px; font-weight: 600; background: transparent;")
        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("Entrez votre mot de passe…")
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setMinimumHeight(44)
        self.password_edit.setStyleSheet("""
            QLineEdit {
                background: #F8FAFF;
                border: 1.5px solid #DDE3ED;
                border-radius: 10px;
                padding: 0 14px;
                font-size: 13px;
                color: #1A1A2E;
            }
            QLineEdit:focus {
                border: 2px solid #F5A200;
                background: #FFFDF5;
            }
        """)
        self.password_edit.returnPressed.connect(self._try_login)

        # Œil pour afficher/masquer le mot de passe
        from app.utils.icons import icon as _icon
        self.toggle_pwd_action = self.password_edit.addAction(
            _icon("eye", color="#94A3B8"), QLineEdit.ActionPosition.TrailingPosition
        )
        self.toggle_pwd_action.triggered.connect(self._toggle_password_visibility)

        # Message d'erreur (caché par défaut)
        self.error_label = QLabel("")
        self.error_label.setStyleSheet(
            "color: #E53E3E; font-size: 12px; background: #FFF5F5; "
            "border-radius: 8px; padding: 8px 12px; border: 1px solid #FEB2B2;"
        )
        self.error_label.setVisible(False)
        self.error_label.setWordWrap(True)

        # Bouton connexion
        self.login_button = QPushButton("  Se connecter")
        self.login_button.setMinimumHeight(48)
        self.login_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_button.setStyleSheet("""
            QPushButton {
                background-color: #F5A200;
                color: #1A1A2E;
                border: none;
                border-radius: 10px;
                font-size: 14px;
                font-weight: 700;
                letter-spacing: 0.5px;
                min-width: 0;
                padding: 0 20px;
            }
            QPushButton:hover {
                background-color: #E09000;
                color: #FFFFFF;
            }
            QPushButton:pressed {
                background-color: #CC8000;
            }
        """)
        self.login_button.clicked.connect(self._try_login)

        card_layout.addWidget(form_title)
        card_layout.addSpacing(4)
        card_layout.addWidget(user_lbl)
        card_layout.addWidget(self.username_edit)
        card_layout.addWidget(pwd_lbl)
        card_layout.addWidget(self.password_edit)
        card_layout.addWidget(self.error_label)
        card_layout.addSpacing(4)
        card_layout.addWidget(self.login_button)

        # ---- Zone inférieure : copyright ----------------------------------
        footer = QLabel("© 2025 Salem Service — Tous droits réservés")
        footer.setStyleSheet(
            "color: rgba(203,213,225,0.7); font-size: 10px; background: transparent;"
        )
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # ---- Assemblage ---------------------------------------------------
        bg_layout.addWidget(top_area)
        bg_layout.addWidget(card, 0, Qt.AlignmentFlag.AlignHCenter)
        bg_layout.setAlignment(card, Qt.AlignmentFlag.AlignHCenter)
        card.setFixedWidth(400)
        bg_layout.addStretch()
        bg_layout.addWidget(footer)
        bg_layout.addSpacing(16)

    # -----------------------------------------------------------------------

    def _toggle_password_visibility(self) -> None:
        """Affiche/masque le mot de passe."""
        from app.utils.icons import icon as _icon
        if self.password_edit.echoMode() == QLineEdit.EchoMode.Password:
            self.password_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_pwd_action.setIcon(_icon("eye", color="#F5A200"))
        else:
            self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_pwd_action.setIcon(_icon("eye", color="#94A3B8"))

    def _try_login(self) -> None:
        """Vérifie les identifiants saisis."""
        username = self.username_edit.text().strip()
        password = self.password_edit.text()

        if not username or not password:
            self._show_error("Veuillez saisir vos identifiants.")
            return

        user = authenticate(username, password)
        if user is None:
            self._show_error("Nom d'utilisateur ou mot de passe incorrect.")
            self.password_edit.clear()
            self.password_edit.setFocus()
            return

        self.user = user
        self.accept()

    def _show_error(self, msg: str) -> None:
        """Affiche un message d'erreur inline sous les champs."""
        self.error_label.setText(f"⚠  {msg}")
        self.error_label.setVisible(True)
        # Fait trembler légèrement le bouton pour retour haptique visuel
        orig = self.login_button.styleSheet()
        self.login_button.setStyleSheet(orig + "border: 2px solid #E53E3E;")
        QTimer.singleShot(600, lambda: self.login_button.setStyleSheet(orig))
