"""Aperçu avant impression et impression des factures.

L'aperçu natif ``QPrintPreviewDialog`` rend un ``QTextDocument`` HTML
reprend le contenu de la facture (identique au PDF généré par ReportLab,
qui reste la version archivée).
"""

from __future__ import annotations

from PySide6.QtGui import QPageSize, QTextDocument
from PySide6.QtPrintSupport import QPrinter, QPrintPreviewDialog
from PySide6.QtWidgets import QWidget

from app.utils.helpers import format_money, format_qty


def invoice_html(sale: dict, company: dict) -> str:
    """Construit le HTML d'une facture pour l'aperçu et l'impression."""
    currency = company.get("currency", "FCFA")
    created = sale["created_at"]
    date_text = created.strftime("%d/%m/%Y %H:%M") if hasattr(created, "strftime") else str(created)
    doc_title = "DEVIS / PRO-FORMA" if sale.get("status") == "devis" else "FACTURE"

    rows = "".join(
        "<tr>"
        f"<td>{i}</td>"
        f"<td>{item['product_name']}</td>"
        f"<td align='right'>{format_qty(item['quantity'])}</td>"
        f"<td align='right'>{format_money(item['unit_price'], currency)}</td>"
        f"<td align='right'>{format_money(item['line_total'], currency)}</td>"
        "</tr>"
        for i, item in enumerate(sale["items"], start=1)
    )

    return f"""
<html><body style="font-family: Helvetica, Arial; font-size: 11px; color: #1C1C1E;">
  <table width="100%"><tr>
    <td><h2 style="color:#0A84FF; margin:0;">{doc_title}</h2>
        <div>N° <b>{sale['number']}</b></div>
        <div style="color:#8E8E93;">{date_text}</div></td>
    <td align="right"><b>{company.get('name','')}</b><br/>
        <span style="color:#8E8E93;">{company.get('address','')}<br/>
        {company.get('phone','')} {company.get('email','')}</span></td>
  </tr></table>
  <hr/>
  <p><b>Client :</b> {sale.get('customer_name') or 'Client comptant'}
     &nbsp;&nbsp; <b>Tél. :</b> {sale.get('customer_phone','')}</p>
  <table width="100%" border="1" cellspacing="0" cellpadding="5"
         style="border-collapse:collapse; border-color:#D1D1D6;">
    <tr style="background-color:#F2F2F7;">
      <th>#</th><th align="left">Désignation</th><th>Qté</th>
      <th>Prix unitaire</th><th>Total</th>
    </tr>
    {rows}
  </table>
  <table width="100%" cellpadding="4"><tr>
    <td></td><td width="260">
      <table width="100%" cellpadding="3">
        <tr><td>Sous-total</td><td align="right">{format_money(sale['subtotal'], currency)}</td></tr>
        <tr><td><b>Total</b></td>
            <td align="right"><b style="color:#0A84FF;">{format_money(sale['total'], currency)}</b></td></tr>
        <tr><td>Montant payé</td><td align="right">{format_money(sale['amount_paid'], currency)}</td></tr>
        <tr style="background-color:#F2F2F7;"><td><b>Reste à payer</b></td>
            <td align="right"><b>{format_money(sale['remaining'], currency)}</b></td></tr>
      </table>
    </td>
  </tr></table>
  <br/><br/>
  <table width="100%"><tr>
    <td style="color:#8E8E93;">{company.get('thanks_message','Merci de votre confiance !')}</td>
    <td align="right">Signature<br/><br/><br/>______________________</td>
  </tr></table>
</body></html>
"""


def ticket_html(sale: dict, company: dict) -> str:
    """Construit le HTML d'un ticket de caisse thermique (80mm) pour l'aperçu et l'impression."""
    currency = company.get("currency", "FCFA")
    created = sale["created_at"]
    date_text = created.strftime("%d/%m/%Y %H:%M") if hasattr(created, "strftime") else str(created)
    doc_title = "DEVIS / PRO-FORMA" if sale.get("status") == "devis" else "TICKET DE CAISSE"

    rows = "".join(
        "<tr>"
        f"<td colspan='2' style='padding-top: 4px;'><b>{item['product_name']}</b></td>"
        "</tr>"
        "<tr>"
        f"<td style='color: #333;'>{format_qty(item['quantity'])} x {format_money(item['unit_price'], currency)}</td>"
        f"<td align='right'>{format_money(item['line_total'], currency)}</td>"
        "</tr>"
        for item in sale["items"]
    )

    return f"""
<html><body style="font-family: 'Courier New', monospace; font-size: 10px; color: #000; margin: 0; padding: 5px; width: 260px;">
  <div align="center">
    <strong style="font-size: 13px;">{company.get('name','')}</strong><br/>
    {company.get('address','')}<br/>
    Tél: {company.get('phone','')}<br/>
    {company.get('email','')}<br/>
    <br/>
    <strong>--- {doc_title} ---</strong><br/>
    N°: {sale['number']}<br/>
    Date: {date_text}<br/>
    ----------------------------------
  </div>
  
  <p style="margin: 4px 0;"><b>Client :</b> {sale.get('customer_name') or 'Client comptant'}</p>
  
  <table width="100%" cellspacing="0" cellpadding="0" style="font-size: 10px;">
    {rows}
  </table>
  
  <div style="border-top: 1px dashed #000; margin-top: 6px; padding-top: 4px;">
    <table width="100%" cellspacing="0" cellpadding="1" style="font-size: 10px;">
      <tr><td>Sous-total</td><td align="right">{format_money(sale['subtotal'], currency)}</td></tr>
      <tr><td><b>TOTAL</b></td><td align="right"><b>{format_money(sale['total'], currency)}</b></td></tr>
      <tr><td>Payé</td><td align="right">{format_money(sale['amount_paid'], currency)}</td></tr>
      <tr><td><b>Reste à payer</b></td><td align="right"><b>{format_money(sale['remaining'], currency)}</b></td></tr>
    </table>
  </div>
  
  <div align="center" style="margin-top: 15px; font-size: 8px;">
    {company.get('thanks_message','Merci de votre confiance !')}<br/>
    ----------------------------------<br/>
    Salem Service
  </div>
</body></html>
"""


def print_invoice(sale: dict, company: dict, parent: QWidget | None = None, format_type: str = "A4") -> None:
    """Affiche l'aperçu avant impression natif d'une facture. En cas d'erreur de pilote, propose le PDF."""
    from PySide6.QtWidgets import QMessageBox
    from PySide6.QtCore import QUrl, QSizeF
    from PySide6.QtGui import QDesktopServices
    from pathlib import Path

    try:
        document = QTextDocument()
        if format_type == "Ticket (80mm)":
            document.setHtml(ticket_html(sale, company))
        else:
            document.setHtml(invoice_html(sale, company))

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        
        if format_type == "Ticket (80mm)":
            printer.setPageSize(QPageSize(QSizeF(80, 200), QPageSize.Unit.Millimeter))
        else:
            printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))

        preview = QPrintPreviewDialog(printer, parent)
        doc_name = "Devis" if sale.get("status") == "devis" else "Facture"
        preview.setWindowTitle(f"Aperçu — {doc_name} {sale['number']}")
        preview.paintRequested.connect(document.print_)
        preview.exec()
    except Exception as exc:
        # Fallback si le sous-système d'impression Qt échoue (ex. pilote manquant, pas d'imprimante installée)
        pdf_path = sale.get("pdf_path", "")
        if pdf_path and Path(pdf_path).exists():
            reply = QMessageBox.question(
                parent,
                "Impression impossible",
                f"L'aperçu avant impression a échoué ({exc}).\n"
                "Voulez-vous ouvrir directement la facture au format PDF pour l'imprimer ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                QDesktopServices.openUrl(QUrl.fromLocalFile(pdf_path))
        else:
            QMessageBox.critical(
                parent,
                "Impression impossible",
                f"L'initialisation de l'impression a échoué : {exc}\n"
                "De plus, aucun fichier PDF n'a été trouvé à l'emplacement indiqué."
            )
