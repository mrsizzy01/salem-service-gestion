import os
import sys
from pathlib import Path
from datetime import datetime

# Ajouter le chemin du projet au sys.path
project_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_dir))

from app.services.pdf_service import generate_invoice_pdf

# Données factices de l'entreprise Salem Service
company = {
    "name": "Salem Service",
    "address": "123 Avenue Lumumba, Lubumbashi",
    "phone": "+243 999 999 999",
    "email": "contact@salemservice.com",
    "currency": "USD",
    "thanks_message": "Merci pour votre confiance !",
    "logo_path": ""
}

# Données factices d'une vente
sale = {
    "number": "FAC-2026-00042",
    "created_at": datetime.now(),
    "customer_name": "Sizzy Shk",
    "customer_phone": "+243 812 345 678",
    "subtotal": 150.00,
    "total": 150.00,
    "amount_paid": 100.00,
    "remaining": 50.00,
    "items": [
        {
            "product_name": "Clavier Mécanique Sans Fil",
            "quantity": 1,
            "unit_price": 80.00,
            "line_total": 80.00
        },
        {
            "product_name": "Souris Ergonomique rechargeable",
            "quantity": 2,
            "unit_price": 35.00,
            "line_total": 70.00
        }
    ]
}

dest_pdf = project_dir / "facture_salem_service.pdf"
generate_invoice_pdf(sale, company, dest_pdf)

print(f"Facture générée avec succès : {dest_pdf}")

# Ouvrir automatiquement le PDF sous Windows
os.startfile(str(dest_pdf))
