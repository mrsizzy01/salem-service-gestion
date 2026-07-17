"""Thèmes clair et sombre — Salem Service.

Palette : jaune‑or (#F5A200) + bleu royal (#1A3C6E) + blanc.
"""

from __future__ import annotations

THEME_LIGHT = "light"
THEME_DARK = "dark"

# ------------------------------------------------------------------
# Palettes
# ------------------------------------------------------------------
LIGHT = {
    "window":          "#F4F6FA",      # fond général légèrement bleuté
    "surface":         "#FFFFFF",      # cartes, tables, dialogues
    "sidebar":         "#1A3C6E",      # bleu foncé professionnel
    "sidebar_active":  "#F5A200",      # jaune‑or pour l'élément actif
    "sidebar_hover":   "#254F8F",      # bleu légèrement plus clair au survol
    "text":            "#1A1A2E",      # texte principal quasi‑noir bleuté
    "text_secondary":  "#6B7280",      # texte secondaire gris
    "text_sidebar":    "#CBD5E1",      # texte dans la barre latérale
    "border":          "#DDE3ED",
    "accent":          "#F5A200",      # jaune‑or (boutons primaires)
    "accent_hover":    "#E09000",
    "accent_text":     "#FFFFFF",
    "danger":          "#E53E3E",
    "success":         "#2F855A",
    "warning":         "#D97706",
    "input_bg":        "#FFFFFF",
    "header_bg":       "#F0F4FB",
    "selection":       "#FEF3C7",      # sélection couleur dorée claire
}

DARK = {
    "window":          "#0F172A",
    "surface":         "#1E293B",
    "sidebar":         "#0D1F3C",
    "sidebar_active":  "#F5A200",
    "sidebar_hover":   "#1A3C6E",
    "text":            "#F1F5F9",
    "text_secondary":  "#94A3B8",
    "text_sidebar":    "#CBD5E1",
    "border":          "#334155",
    "accent":          "#F5A200",
    "accent_hover":    "#FBBF24",
    "accent_text":     "#FFFFFF",
    "danger":          "#FC8181",
    "success":         "#68D391",
    "warning":         "#FBBF24",
    "input_bg":        "#293548",
    "header_bg":       "#243044",
    "selection":       "#78350F",
}


def get_stylesheet(theme: str) -> str:
    """Retourne la feuille de style QSS complète du thème demandé."""
    c = DARK if theme == THEME_DARK else LIGHT
    is_dark = theme == THEME_DARK
    sidebar_text = c["text_sidebar"]
    return f"""
/* ================== Base ================== */
QWidget {{
    font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
    color: {c['text']};
    background-color: {c['window']};
}}
QDialog, QMessageBox {{ background-color: {c['surface']}; }}
QLabel {{ background: transparent; }}
QLabel#muted {{ color: {c['text_secondary']}; }}
QLabel#title {{ font-size: 20px; font-weight: 700; }}
QLabel#subtitle {{ color: {c['text_secondary']}; font-size: 12px; }}

/* ================== Barre latérale ================== */
QFrame#Sidebar {{
    background-color: {c['sidebar']};
    border-right: none;
}}
QLabel#AppName {{
    font-size: 17px;
    font-weight: 800;
    color: #F5A200;
    letter-spacing: 0.5px;
}}
QLabel#AppSubtitle {{
    color: {c['text_sidebar']};
    font-size: 11px;
    opacity: 0.8;
}}
QToolButton#NavButton {{
    border: none;
    border-radius: 8px;
    padding: 9px 12px;
    text-align: left;
    color: {sidebar_text};
    font-size: 13px;
    background: transparent;
}}
QToolButton#NavButton:hover {{
    background-color: {c['sidebar_hover']};
    color: #FFFFFF;
}}
QToolButton#NavButton:checked {{
    background-color: {c['sidebar_active']};
    color: #1A1A2E;
    font-weight: 700;
}}

/* ================== Barre supérieure ================== */
QFrame#TopBar {{
    background-color: {c['surface']};
    border-bottom: 1px solid {c['border']};
}}
QLineEdit#SearchEdit {{
    background-color: {c['input_bg']};
    border: 1px solid {c['border']};
    border-radius: 8px;
    padding: 7px 12px 7px 32px;
    selection-background-color: {c['selection']};
}}
QLineEdit#SearchEdit:focus {{ border: 1px solid {c['accent']}; }}

/* ================== Boutons ================== */
QPushButton {{
    background-color: {c['surface']};
    border: 1px solid {c['border']};
    border-radius: 8px;
    padding: 10px 18px;
    min-width: 100px;
    min-height: 36px;
    font-size: 13px;
    font-weight: 500;
    color: {c['text']};
}}
QPushButton:hover {{ background-color: {c['header_bg']}; border-color: {c['accent']}; color: {c['text']}; }}
QPushButton:pressed {{ background-color: {c['border']}; }}
QPushButton:disabled {{ color: {c['text_secondary']}; background-color: {c['header_bg']}; }}
QPushButton#PrimaryButton {{
    background-color: {c['accent']};
    color: #1A1A2E;
    border: none;
    font-weight: 700;
    min-width: 140px;
    min-height: 40px;
    padding: 10px 20px;
}}
QPushButton#PrimaryButton:hover {{ background-color: {c['accent_hover']}; color: #FFFFFF; }}
QPushButton#DangerButton {{
    background-color: {c['danger']};
    color: #FFFFFF;
    border: none;
    font-weight: 600;
    min-width: 120px;
    min-height: 36px;
    padding: 10px 18px;
}}
QPushButton#GhostButton {{
    border: none;
    background: transparent;
    color: {c['accent']};
    min-width: 80px;
    padding: 8px 12px;
}}
QPushButton#GhostButton:hover {{ text-decoration: underline; background: transparent; }}
QToolButton#IconButton {{
    border: none;
    border-radius: 8px;
    padding: 8px;
    min-width: 36px;
    min-height: 36px;
    background: transparent;
    color: {c['text']};
}}
QToolButton#IconButton:hover {{ background-color: {c['header_bg']}; }}

/* ================== Champs de saisie ================== */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QDateTimeEdit, QPlainTextEdit, QTextEdit {{
    background-color: {c['input_bg']};
    border: 1px solid {c['border']};
    border-radius: 8px;
    padding: 6px 10px;
    selection-background-color: {c['selection']};
    color: {c['text']};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus,
QDateEdit:focus, QDateTimeEdit:focus, QPlainTextEdit:focus, QTextEdit:focus {{
    border: 2px solid {c['accent']};
}}
QComboBox::drop-down {{ border: none; width: 26px; }}
QComboBox QAbstractItemView {{
    background-color: {c['surface']};
    border: 1px solid {c['border']};
    selection-background-color: {c['accent']};
    selection-color: #1A1A2E;
    outline: none;
}}

/* ================== Tableaux ================== */
QTableWidget, QTableView {{
    background-color: {c['surface']};
    alternate-background-color: {c['header_bg']};
    gridline-color: {c['border']};
    border: 1px solid {c['border']};
    border-radius: 10px;
    selection-background-color: {c['selection']};
    selection-color: {c['text']};
}}
QHeaderView::section {{
    background-color: {c['sidebar']};
    color: #FFFFFF;
    border: none;
    border-bottom: 2px solid {c['accent']};
    padding: 8px 6px;
    font-weight: 700;
    font-size: 12px;
}}
QTableWidget::item, QTableView::item {{ padding: 6px; border: none; }}

/* ================== Cartes et conteneurs ================== */
QFrame#Card, QFrame#StatCard {{
    background-color: {c['surface']};
    border: 1px solid {c['border']};
    border-radius: 12px;
}}
QLabel#StatValue {{ font-size: 18px; font-weight: 800; color: {c['accent']}; }}
QLabel#StatTitle {{ color: {c['text_secondary']}; font-size: 12px; }}

/* ================== Onglets ================== */
QTabWidget::pane {{ border: 1px solid {c['border']}; border-radius: 10px; background: {c['surface']}; }}
QTabBar::tab {{
    background: transparent;
    color: {c['text_secondary']};
    padding: 8px 16px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
}}
QTabBar::tab:selected {{ background: {c['surface']}; color: {c['accent']}; font-weight: 700; border-bottom: 2px solid {c['accent']}; }}

/* ================== Divers ================== */
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {c['border']}; border-radius: 5px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {c['text_secondary']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {c['border']}; border-radius: 5px; min-width: 30px; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
QToolTip {{
    background-color: {c['surface']};
    color: {c['text']};
    border: 1px solid {c['border']};
    padding: 6px 8px;
    border-radius: 6px;
}}
QGroupBox {{
    border: 1px solid {c['border']};
    border-radius: 10px;
    margin-top: 12px;
    padding-top: 12px;
    background-color: {c['surface']};
    font-weight: 600;
}}
QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 6px; color: {c['accent']}; }}
QCheckBox, QRadioButton {{ spacing: 8px; background: transparent; }}
QMessageBox QPushButton {{ min-width: 80px; }}
"""
