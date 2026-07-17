"""Génération des documents PDF avec ReportLab (format A4).

- ``generate_invoice_pdf`` : facture professionnelle complète
  (logo, coordonnées, client, lignes, totaux, paiement, signature).
- ``generate_report_pdf``  : rapport d'activité sur une période.

Les fonctions reçoivent des dictionnaires simples (pas d'objets ORM)
afin de rester testables et indépendantes de la base.
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    HRFlowable,
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.utils.helpers import format_money, format_qty

# ------------------------------------------------------------------
# Charte graphique des documents
# ------------------------------------------------------------------
ACCENT = colors.HexColor("#0A84FF")       # bleu principal
DARK = colors.HexColor("#1C1C1E")         # texte foncé
GREY = colors.HexColor("#8E8E93")         # texte secondaire
LIGHT_BG = colors.HexColor("#F2F2F7")     # fond des en-têtes de tableau
BORDER = colors.HexColor("#D1D1D6")

_BASE = ParagraphStyle("base", fontName="Helvetica", fontSize=9, textColor=DARK, leading=13)
_BOLD = ParagraphStyle("bold", parent=_BASE, fontName="Helvetica-Bold")
_TITLE = ParagraphStyle("title", parent=_BASE, fontName="Helvetica-Bold", fontSize=22,
                        textColor=ACCENT, leading=26)
_SMALL_GREY = ParagraphStyle("grey", parent=_BASE, fontSize=8, textColor=GREY)
_SMALL_GREY_RIGHT = ParagraphStyle("greyr", parent=_SMALL_GREY, alignment=2)
_RIGHT = ParagraphStyle("right", parent=_BASE, alignment=2)
_RIGHT_BOLD = ParagraphStyle("rightbold", parent=_BOLD, alignment=2)


def _logo_flowable(logo_path: str, max_h: float = 22 * mm, max_w: float = 45 * mm):
    """Retourne un flowable Image proportionné, ou None si absent."""
    if not logo_path or not Path(logo_path).exists():
        return None
    try:
        reader = ImageReader(logo_path)
        width, height = reader.getSize()
        ratio = min(max_w / width, max_h / height)
        return Image(logo_path, width=width * ratio, height=height * ratio)
    except Exception:
        return None


# ------------------------------------------------------------------
# Facture
# ------------------------------------------------------------------
def generate_invoice_pdf(sale: dict, company: dict, dest: str | Path) -> str:
    """Génère la facture PDF d'une vente.

    :param sale:    dict « number, created_at, customer_name,
                    customer_phone, items[{product_name, quantity,
                    unit_price, line_total}], subtotal, total,
                    amount_paid, remaining ».
    :param company: dict « name, address, phone, email, currency,
                    logo_path, thanks_message ».
    :param dest:    chemin du fichier PDF de sortie.
    :return:        le chemin du fichier généré.
    """
    dest = str(dest)
    currency = company.get("currency", "FCFA")

    doc = SimpleDocTemplate(
        dest, pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=14 * mm, bottomMargin=14 * mm,
        title=f"Facture {sale['number']}", author=company.get("name", ""),
    )
    elements: list = []

    # ---- En-tête : logo + coordonnées de l'entreprise -------------
    company_rows = [[Paragraph(
        f"<b>{company.get('name', '')}</b>",
        ParagraphStyle("cname", parent=_BOLD, fontSize=13, alignment=2))]]
    for line in (company.get("address"), company.get("phone"), company.get("email")):
        if line:
            company_rows.append([Paragraph(line, _SMALL_GREY_RIGHT)])
    # Tableau imbriqué : garantit l'alignement à droite du bloc.
    company_block = Table(company_rows, colWidths=[112 * mm])
    company_block.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    logo = _logo_flowable(company.get("logo_path", ""))
    header = Table(
        [[logo if logo else "", company_block]],
        colWidths=[60 * mm, 120 * mm],
    )
    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(header)
    elements.append(Spacer(1, 6))
    elements.append(HRFlowable(width="100%", thickness=1.4, color=ACCENT))
    elements.append(Spacer(1, 8))

    # ---- Titre + bloc client --------------------------------------
    created = sale["created_at"]
    date_text = created.strftime("%d/%m/%Y %H:%M") if hasattr(created, "strftime") else str(created)
    title_block = [
        Paragraph("FACTURE", _TITLE),
        Spacer(1, 3),
        Paragraph(f"N° <b>{sale['number']}</b>", _BASE),
        Paragraph(f"Date : {date_text}", _SMALL_GREY),
    ]
    client_lines = [Paragraph("Facturé à", _SMALL_GREY), Spacer(1, 2)]
    client_lines.append(Paragraph(f"<b>{sale.get('customer_name') or 'Client comptant'}</b>", _BOLD))
    if sale.get("customer_phone"):
        client_lines.append(Paragraph(f"Tél. : {sale['customer_phone']}", _BASE))
    info = Table([[title_block, client_lines]], colWidths=[95 * mm, 85 * mm])
    info.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (1, 0), (1, 0), LIGHT_BG),
        ("BOX", (1, 0), (1, 0), 0.6, BORDER),
        ("TOPPADDING", (1, 0), (1, 0), 8),
        ("BOTTOMPADDING", (1, 0), (1, 0), 8),
        ("LEFTPADDING", (1, 0), (1, 0), 10),
        ("RIGHTPADDING", (1, 0), (1, 0), 10),
        ("LEFTPADDING", (0, 0), (0, 0), 0),
    ]))
    elements.append(info)
    elements.append(Spacer(1, 12))

    # ---- Tableau des produits -------------------------------------
    header_row = [
        Paragraph("<b>#</b>", _BOLD),
        Paragraph("<b>Désignation</b>", _BOLD),
        Paragraph("<b>Qté</b>", _RIGHT_BOLD),
        Paragraph("<b>Prix unitaire</b>", _RIGHT_BOLD),
        Paragraph("<b>Total</b>", _RIGHT_BOLD),
    ]
    rows = [header_row]
    for idx, item in enumerate(sale["items"], start=1):
        rows.append([
            Paragraph(str(idx), _BASE),
            Paragraph(item["product_name"], _BASE),
            Paragraph(format_qty(item["quantity"]), _RIGHT),
            Paragraph(format_money(item["unit_price"], currency), _RIGHT),
            Paragraph(format_money(item["line_total"], currency), _RIGHT),
        ])
    table = Table(rows, colWidths=[10 * mm, 84 * mm, 20 * mm, 33 * mm, 33 * mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT_BG),
        ("LINEBELOW", (0, 0), (-1, 0), 1, ACCENT),
        ("GRID", (0, 1), (-1, -1), 0.4, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FAFAFC")]),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 10))

    # ---- Totaux et paiement ---------------------------------------
    totals_rows = [
        ["", Paragraph("Sous-total", _RIGHT), Paragraph(format_money(sale["subtotal"], currency), _RIGHT)],
        ["", Paragraph("<b>Total</b>", _RIGHT_BOLD),
         Paragraph(f"<b>{format_money(sale['total'], currency)}</b>",
                   ParagraphStyle("tot", parent=_RIGHT_BOLD, fontSize=11, textColor=ACCENT))],
        ["", Paragraph("Montant payé", _RIGHT), Paragraph(format_money(sale["amount_paid"], currency), _RIGHT)],
        ["", Paragraph("<b>Reste à payer</b>", _RIGHT_BOLD),
         Paragraph(f"<b>{format_money(sale['remaining'], currency)}</b>", _RIGHT_BOLD)],
    ]
    totals = Table(totals_rows, colWidths=[95 * mm, 45 * mm, 40 * mm])
    totals.setStyle(TableStyle([
        ("LINEABOVE", (1, 1), (2, 1), 1, ACCENT),
        ("BACKGROUND", (1, 3), (2, 3), LIGHT_BG),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(totals)
    elements.append(Spacer(1, 26))

    # ---- Signature et remerciement --------------------------------
    footer = Table(
        [[
            Paragraph(company.get("thanks_message") or "Merci de votre confiance !",
                      ParagraphStyle("thanks", parent=_BASE, textColor=GREY)),
            Paragraph("Signature<br/><br/><br/>_____________________________", _RIGHT),
        ]],
        colWidths=[100 * mm, 80 * mm],
    )
    footer.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "BOTTOM")]))
    elements.append(footer)

    doc.build(elements)
    return dest


# ------------------------------------------------------------------
# Rapport d'activité
# ------------------------------------------------------------------
def generate_report_pdf(report: dict, company: dict, dest: str | Path) -> str:
    """Génère un rapport d'activité PDF.

    :param report: dict « title, period_label, summary[[libellé, valeur]],
                    sales[[n°, date, client, total, payé, reste]],
                    top_products[[produit, qté, montant]] ».
    :param company: dict entreprise (nom, devise…).
    :param dest: chemin du PDF de sortie.
    """
    dest = str(dest)
    doc = SimpleDocTemplate(
        dest, pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm,
        title=report["title"], author=company.get("name", ""),
    )
    elements: list = []

    elements.append(Paragraph(company.get("name", ""), ParagraphStyle("co", parent=_BOLD, fontSize=12)))
    elements.append(Paragraph(report["title"], ParagraphStyle("rt", parent=_TITLE, fontSize=18)))
    elements.append(Paragraph(f"Période : {report['period_label']}", _SMALL_GREY))
    elements.append(Spacer(1, 8))
    elements.append(HRFlowable(width="100%", thickness=1.2, color=ACCENT))
    elements.append(Spacer(1, 10))

    # ---- Résumé chiffré -------------------------------------------
    elements.append(Paragraph("<b>Synthèse</b>", _BOLD))
    elements.append(Spacer(1, 4))
    summary_rows = [[Paragraph(label, _BASE), Paragraph(value, _RIGHT_BOLD)]
                    for label, value in report["summary"]]
    summary = Table(summary_rows, colWidths=[110 * mm, 70 * mm])
    summary.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, LIGHT_BG]),
        ("LINEBELOW", (0, 0), (-1, -2), 0.3, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(summary)
    elements.append(Spacer(1, 14))

    # ---- Détail des ventes ----------------------------------------
    if report.get("sales"):
        elements.append(Paragraph("<b>Détail des ventes</b>", _BOLD))
        elements.append(Spacer(1, 4))
        header = [Paragraph(f"<b>{h}</b>", _BOLD)
                  for h in ("N°", "Date", "Client", "Total", "Payé", "Reste")]
        rows = [header] + [
            [Paragraph(str(cell), _RIGHT if i >= 3 else _BASE) for i, cell in enumerate(row)]
            for row in report["sales"]
        ]
        sales_table = Table(rows, colWidths=[28 * mm, 28 * mm, 58 * mm, 24 * mm, 24 * mm, 24 * mm],
                            repeatRows=1)
        sales_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), LIGHT_BG),
            ("LINEBELOW", (0, 0), (-1, 0), 1, ACCENT),
            ("GRID", (0, 1), (-1, -1), 0.4, BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(sales_table)
        elements.append(Spacer(1, 14))

    # ---- Meilleurs produits ---------------------------------------
    if report.get("top_products"):
        elements.append(Paragraph("<b>Meilleurs produits</b>", _BOLD))
        elements.append(Spacer(1, 4))
        header = [Paragraph("<b>Produit</b>", _BOLD), Paragraph("<b>Quantité</b>", _RIGHT_BOLD),
                  Paragraph("<b>Montant</b>", _RIGHT_BOLD)]
        rows = [header] + [
            [Paragraph(str(row[0]), _BASE), Paragraph(str(row[1]), _RIGHT),
             Paragraph(str(row[2]), _RIGHT)]
            for row in report["top_products"]
        ]
        top_table = Table(rows, colWidths=[110 * mm, 30 * mm, 40 * mm], repeatRows=1)
        top_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), LIGHT_BG),
            ("LINEBELOW", (0, 0), (-1, 0), 1, ACCENT),
            ("GRID", (0, 1), (-1, -1), 0.4, BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(top_table)

    doc.build(elements)
    return dest
