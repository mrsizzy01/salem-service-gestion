"""Fabrique d'icônes vectorielles (SVG dessinés à la volée).

Les icônes sont des pictogrammes minimalistes de style « trait »
(inspirés de Feather Icons), rendus en ``QIcon`` via ``QSvgRenderer`` :
aucune ressource externe n'est nécessaire, la couleur s'adapte au thème.
"""

from __future__ import annotations

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

# Corps des pictogrammes (viewBox 24x24, style trait).
_SHAPES: dict[str, str] = {
    "dashboard": '<rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/>',
    "box": '<path d="M21 8l-9-5-9 5v8l9 5 9-5z"/><path d="M3.3 8.3L12 13l8.7-4.7"/><path d="M12 13v9"/>',
    "stock": '<path d="M3 21V10l9-6 9 6v11"/><path d="M3 21h18"/><rect x="8" y="13" width="8" height="8"/><path d="M8 17h8"/>',
    "invoice": '<path d="M6 2h12v20l-3-2-3 2-3-2-3 2z"/><path d="M9 7h6M9 11h6M9 15h4"/>',
    "customers": '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c0-3.6 2.9-6 6.5-6s6.5 2.4 6.5 6"/><path d="M16 4.7a3.5 3.5 0 0 1 0 6.6"/><path d="M17.5 14.4c2.3.8 4 2.9 4 5.6"/>',
    "suppliers": '<rect x="1.5" y="5" width="13" height="11" rx="1"/><path d="M14.5 9h4l3 4v3h-7z"/><circle cx="6" cy="18.5" r="2"/><circle cx="17.5" cy="18.5" r="2"/>',
    "expenses": '<rect x="2" y="6" width="20" height="14" rx="2.5"/><path d="M2 10.5h20"/><path d="M6 15.5h4"/>',
    "reports": '<path d="M3 3v18h18"/><path d="M7 15l4-6 4 3 5-8"/>',
    "settings": '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1L7 17M17 7l2.1-2.1"/>',
    "users": '<path d="M12 2l8 4v6c0 5-3.5 8.5-8 10-4.5-1.5-8-5-8-10V6z"/><path d="M9 11.5l2 2 4-4"/>',
    "logout": '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="M16 17l5-5-5-5"/><path d="M21 12H9"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "edit": '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/>',
    "trash": '<path d="M3 6h18"/><path d="M8 6V4h8v2"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6M14 11v6"/>',
    "print": '<path d="M6 9V2h12v7"/><rect x="3" y="9" width="18" height="8" rx="1.5"/><path d="M6 14h12v8H6z"/>',
    "file": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/>',
    "excel": '<rect x="3" y="3" width="18" height="18" rx="2.5"/><path d="M3 9h18M3 15h18M9 3v18M15 3v18"/>',
    "sun": '<circle cx="12" cy="12" r="4.5"/><path d="M12 2v2.5M12 19.5V22M2 12h2.5M19.5 12H22M4.9 4.9l1.8 1.8M17.3 17.3l1.8 1.8M4.9 19.1l1.8-1.8M17.3 6.7l1.8-1.8"/>',
    "moon": '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/>',
    "database": '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 1.7 4 3 9 3s9-1.3 9-3V5"/><path d="M3 12c0 1.7 4 3 9 3s9-1.3 9-3"/>',
    "history": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "money": '<circle cx="12" cy="12" r="9"/><path d="M12 6v12M15 9.2c-.5-1-1.7-1.5-3-1.5-1.8 0-3 .9-3 2.1 0 2.9 6 1.5 6 4.4 0 1.2-1.2 2.1-3 2.1-1.3 0-2.5-.5-3-1.5"/>',
    "warning": '<path d="M12 3L1.5 21h21z"/><path d="M12 10v5"/><circle cx="12" cy="17.8" r="0.4"/>',
    "check": '<circle cx="12" cy="12" r="9"/><path d="M8 12.5l2.7 2.7L16 9.5"/>',
    "refresh": '<path d="M21 12a9 9 0 1 1-2.6-6.4"/><path d="M21 3v6h-6"/>',
    "eye": '<path d="M1.5 12S5.5 4.5 12 4.5 22.5 12 22.5 12 18.5 19.5 12 19.5 1.5 12 1.5 12z"/><circle cx="12" cy="12" r="3"/>',
    "cancel": '<circle cx="12" cy="12" r="9"/><path d="M8.5 8.5l7 7M15.5 8.5l-7 7"/>',
}


def _build_svg(name: str, color: str, stroke_width: float = 1.8) -> bytes:
    """Assemble le document SVG complet d'un pictogramme."""
    body = _SHAPES.get(name, _SHAPES["box"])
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
        f'fill="none" stroke="{color}" stroke-width="{stroke_width}" '
        f'stroke-linecap="round" stroke-linejoin="round">{body}</svg>'
    ).encode("utf-8")


def icon(name: str, color: str = "#6E6E73", size: int = 18) -> QIcon:
    """Rend un pictogramme en ``QIcon`` de la couleur demandée."""
    renderer = QSvgRenderer(QByteArray(_build_svg(name, color)))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()
    return QIcon(pixmap)


def icon_names() -> list[str]:
    """Liste les pictogrammes disponibles."""
    return sorted(_SHAPES.keys())
