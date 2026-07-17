# Gestion Commerciale & Facturation

Logiciel **desktop** professionnel de gestion commerciale et de facturation,
destiné à une maison de vente multi-catégories. 100 % hors ligne : aucun
navigateur, aucune connexion Internet requise.

| | |
|---|---|
| **Langage** | Python 3.11+ |
| **Interface** | PySide6 (Qt6) — thème clair & sombre, design inspiré de macOS |
| **Base de données** | SQLite (créée automatiquement au premier lancement) |
| **ORM** | SQLAlchemy 2 + gestionnaire de migrations maison |
| **PDF** | ReportLab (factures A4 et rapports) |
| **Excel** | OpenPyXL (rapports et inventaire) |
| **Graphiques** | matplotlib intégré à Qt |
| **Architecture** | MVC stricte, code entièrement commenté en français |
| **Packaging** | py2app → `.app`, puis `.dmg` (script fourni) |

---

## Fonctionnalités

- **Tableau de bord** : factures du jour, chiffre d'affaires (jour et mois),
  produits en stock, ruptures, graphiques (14 jours, mensuel, par catégorie),
  dernières factures.
- **Produits** : ajout, modification, suppression (archivage si le produit a
  déjà été vendu), recherche, catégories, prix d'achat / de vente, stock,
  seuil d'alerte, photo facultative.
- **Stock** : entrées, sorties, ajustements d'inventaire, historique complet
  des mouvements, valorisation du stock, export Excel.
- **Facturation** *(processus volontairement très simple)* :
  - nom et téléphone du client saisis directement sur la facture, **sans
    enregistrement obligatoire** ;
  - produits **enregistrés** (liste déroulante, prix pré-rempli) ou
    **manuels** (nom, quantité, prix unitaire) ;
  - bouton **« Ajouter ce produit à la base »** pour enregistrer un produit
    manuel dans le catalogue ;
  - sous-total et total automatiques, montant payé, **reste à payer**
    calculé en direct ;
  - à la validation : vente enregistrée, **stock mis à jour**, **numéro de
    facture unique** (`FAC-ANNÉE-NNNNN`), **PDF A4 généré**, **aperçu avant
    impression**, impression et **réimpression** depuis l'historique ;
  - annulation d'une facture (administrateur) avec réintégration du stock.
- **Clients** *(module facultatif)* : enregistrement possible mais jamais
  obligatoire ; pré-remplissage des factures.
- **Fournisseurs** : ajout, modification, suppression.
- **Dépenses** : gestion complète des dépenses de l'entreprise.
- **Rapports** : quotidiens, hebdomadaires, mensuels, annuels ou
  personnalisés — ventes, encaissements, marge brute, dépenses, résultat
  net, meilleurs produits — export **PDF** et **Excel**.
- **Paramètres** : nom, adresse, téléphone, email, **devise**, logo,
  message de remerciement, **sauvegarde** et **restauration** de la base.
- **Utilisateurs** : connexion sécurisée (PBKDF2-SHA256, 200 000
  itérations), rôles **Administrateur** / **Caissier** (accès restreint),
  activation/désactivation, garde-fou « dernier administrateur ».
- **Journal d'audit** : toutes les actions sensibles sont tracées
  (utilisateur, action, date, détails).

---

## Démarrage rapide (développement)

```bash
# 1. Cloner / copier le projet puis :
cd gestion-commerciale

# 2. Créer un environnement virtuel
python3 -m venv .venv
source .venv/bin/activate          # Windows : .venv\Scripts\activate

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Lancer l'application
python main.py
```

Au premier lancement :

- la base SQLite est créée automatiquement (migrations incluses) ;
- un compte administrateur est créé : **`admin` / `admin123`**
  *(à changer immédiatement dans Utilisateurs)*.

### Lancer les tests

```bash
python -m pytest tests/ -q        # 17 tests : métier, PDF, Excel, sécurité
python tests/smoke_gui.py          # test de fumée de l'interface (hors écran)
```

---

## Construire l'application macOS (.app / .dmg)

Sur macOS 11+ avec Python 3.11+ :

```bash
chmod +x scripts/build_mac.sh
./scripts/build_mac.sh
```

Le script :

1. crée un environnement virtuel et installe les dépendances + py2app ;
2. génère l'icône `AppIcon.icns` (via `scripts/make_icon.py` + `iconutil`) ;
3. construit **`dist/Gestion Commerciale.app`** (py2app) ;
4. emballe l'installeur **`dist/GestionCommerciale-1.0.0.dmg`** (hdiutil).

> Les données (base, factures, sauvegardes) sont stockées hors du bundle
> dans `~/Library/Application Support/GestionCommerciale/` : elles
> survivent aux mises à jour de l'application.

---

## Structure du projet

```
gestion-commerciale/
├── main.py                     # Point d'entrée (login → fenêtre principale)
├── requirements.txt
├── setup.py                    # Configuration py2app (.app)
├── scripts/
│   ├── build_mac.sh            # Build complet : .app + .dmg
│   └── make_icon.py            # Génération de l'icône (iconset)
├── app/
│   ├── config.py               # Chemins, constantes, rôles
│   ├── models/                 # — MODÈLES —
│   │   ├── database.py         # Moteur SQLite, sessions SQLAlchemy
│   │   ├── entities.py         # 12 tables (produits, ventes, stock, users…)
│   │   └── migrations.py       # Migrations versionnées (schema_version)
│   ├── controllers/            # — CONTRÔLEURS (logique métier, sans Qt) —
│   │   ├── product_controller.py
│   │   ├── stock_controller.py
│   │   ├── sale_controller.py  # Validation vente + stock + numérotation
│   │   ├── report_controller.py
│   │   ├── customer_controller.py / supplier_controller.py
│   │   ├── expense_controller.py
│   │   ├── settings_controller.py
│   │   └── user_controller.py
│   ├── services/               # Services techniques
│   │   ├── auth_service.py     # PBKDF2, compte admin par défaut
│   │   ├── audit_service.py    # Journal des actions
│   │   ├── pdf_service.py      # Factures et rapports A4 (ReportLab)
│   │   ├── excel_service.py    # Exports .xlsx (OpenPyXL)
│   │   └── backup_service.py   # Sauvegarde / restauration
│   ├── utils/
│   │   ├── theme.py            # QSS clair & sombre (style macOS)
│   │   ├── icons.py            # Pictogrammes SVG générés à la volée
│   │   └── helpers.py          # Devises, arrondis, périodes
│   └── views/                  # — VUES (PySide6, sans logique métier) —
│       ├── login_dialog.py     # Connexion sécurisée
│       ├── main_window.py      # Barre latérale + barre supérieure + pages
│       ├── widgets.py          # Sidebar, TopBar, StatCard
│       ├── dialogs.py          # Tous les formulaires (popups)
│       ├── printing.py         # Aperçu avant impression A4
│       └── pages/              # dashboard, produits, stock, facturation,
│                               # clients, fournisseurs, dépenses, rapports,
│                               # paramètres, utilisateurs, journal
└── tests/
    ├── test_core.py            # 17 tests unitaires (pytest)
    └── smoke_gui.py            # Test de fumée de toute l'interface
```

### Architecture MVC

- **Modèles** : uniquement SQLAlchemy — aucune référence à Qt ;
- **Contrôleurs** : logique métier pure, sessions transactionnelles,
  journalisation automatique — retournent des dictionnaires simples ;
- **Vues** : uniquement PySide6 — appellent les contrôleurs, jamais la base.

### Évolution du schéma (migrations)

1. Modifier `app/models/entities.py` ;
2. Ajouter dans `app/models/migrations.py` une entrée
   `(2, "Description", _migration_002)` appliquant les `ALTER TABLE` ;
3. La migration s'applique automatiquement au prochain lancement.

---

## Emplacements des données

| Donnée | macOS | Windows | Linux |
|---|---|---|---|
| Base SQLite | `~/Library/Application Support/GestionCommerciale/gestion.db` | `%APPDATA%\GestionCommerciale\` | `~/.local/share/gestion-commerciale/` |
| Factures PDF | `…/factures/` | `…\factures\` | `…/factures/` |
| Sauvegardes | `…/sauvegardes/` | `…\sauvegardes\` | `…/sauvegardes/` |
| Rapports exportés | `…/rapports/` | `…\rapports\` | `…/rapports/` |

La variable d'environnement `GESTION_DATA_DIR` permet de forcer un autre
dossier (utilisée par les tests).

## Sécurité

- Mots de passe hachés en **PBKDF2-SHA256** (200 000 itérations, sel
  aléatoire), vérification en temps constant ;
- aucun mot de passe en clair n'est jamais stocké ni journalisé ;
- le rôle **Caissier** masque Fournisseurs, Dépenses, Utilisateurs,
  Journal et Paramètres ;
- il est impossible de supprimer ou désactiver le dernier administrateur
  actif, ou son propre compte.
