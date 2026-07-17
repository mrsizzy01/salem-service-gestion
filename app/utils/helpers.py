"""Fonctions utilitaires pures (sans dépendance Qt).

Formatage des montants, arrondis et bornes de périodes pour les rapports.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

# Devises traditionnellement affichées sans décimales.
_ZERO_DECIMAL_CURRENCIES = {"CDF", "FCFA", "XOF", "XAF", "GNF", "MGA", "KMF"}


def round2(value: float) -> float:
    """Arrondit un montant à 2 décimales (évite les erreurs flottantes)."""
    return round(float(value) + 1e-9, 2)


def format_money(amount: float, currency: str = "CDF") -> str:
    """Formate un montant avec séparateur de milliers et devise."""
    amount = round2(amount)
    if currency.upper() in _ZERO_DECIMAL_CURRENCIES:
        text = f"{amount:,.0f}"
    else:
        text = f"{amount:,.2f}"
    return f"{text} {currency}".strip()


def format_qty(quantity: float) -> str:
    """Formate une quantité (supprime les décimales inutiles)."""
    if float(quantity) == int(quantity):
        return str(int(quantity))
    return f"{quantity:g}"


def format_address(parts: dict) -> str:
    """Formate une adresse RDC complète à partir des champs."""
    lines = []
    if parts.get("avenue"):
        lines.append(parts["avenue"])
    if parts.get("quartier"):
        lines.append(parts["quartier"])
    if parts.get("commune"):
        lines.append(parts["commune"])
    if parts.get("city"):
        lines.append(parts["city"])
    if parts.get("province"):
        lines.append(parts["province"])
    return ", ".join(lines)


def format_address_multiline(parts: dict) -> str:
    """Formate une adresse RDC sur plusieurs lignes."""
    lines = []
    if parts.get("avenue"):
        lines.append(parts["avenue"])
    parts_list = []
    if parts.get("quartier"):
        parts_list.append(parts["quartier"])
    if parts.get("commune"):
        parts_list.append(parts["commune"])
    if parts_list:
        lines.append(" / ".join(parts_list))
    city_parts = []
    if parts.get("city"):
        city_parts.append(parts["city"])
    if parts.get("province"):
        city_parts.append(parts["province"])
    if city_parts:
        lines.append(" / ".join(city_parts))
    return "\n".join(lines)


# ------------------------------------------------------------------
# Bornes de périodes (rapports)
# ------------------------------------------------------------------
def day_range(day: date) -> tuple[datetime, datetime]:
    """Retourne [début, fin] d'une journée."""
    start = datetime.combine(day, time.min)
    end = datetime.combine(day, time.max)
    return start, end


def week_range(day: date) -> tuple[datetime, datetime]:
    """Retourne [lundi, dimanche] de la semaine contenant ``day``."""
    monday = day - timedelta(days=day.weekday())
    sunday = monday + timedelta(days=6)
    return datetime.combine(monday, time.min), datetime.combine(sunday, time.max)


def month_range(year: int, month: int) -> tuple[datetime, datetime]:
    """Retourne [premier jour, dernier jour] du mois."""
    start = date(year, month, 1)
    if month == 12:
        end = date(year, 12, 31)
    else:
        end = date(year, month + 1, 1) - timedelta(days=1)
    return datetime.combine(start, time.min), datetime.combine(end, time.max)


def year_range(year: int) -> tuple[datetime, datetime]:
    """Retourne [1er janvier, 31 décembre] de l'année."""
    return (
        datetime.combine(date(year, 1, 1), time.min),
        datetime.combine(date(year, 12, 31), time.max),
    )
