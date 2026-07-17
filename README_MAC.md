# 🍎 Salem Service — Installation sur macOS

## Prérequis

| Outil | Version minimale | Lien |
|-------|-----------------|------|
| macOS | Big Sur 11.0+ | — |
| Python | 3.11 ou 3.12 | https://www.python.org/downloads/ |
| Xcode CLI | Dernière version | `xcode-select --install` |

---

## ✅ Étape 1 — Copier le projet sur le Mac

Transfère le dossier `gestion-commerciale` sur le Mac (clé USB, AirDrop, etc.)  
ou clone depuis Git :

```bash
git clone https://github.com/ton-repo/gestion-commerciale.git
cd gestion-commerciale
```

---

## ✅ Étape 2 — Lancer le script de build

Ouvre le **Terminal** (Applications → Utilitaires → Terminal) :

```bash
cd /chemin/vers/gestion-commerciale
chmod +x build_mac.sh
./build_mac.sh
```

Le script fait automatiquement :
- Crée un environnement virtuel Python isolé
- Installe toutes les dépendances (PySide6, SQLAlchemy, ReportLab…)
- Compile un `.app` autonome avec PyInstaller
- Génère un fichier `.dmg` installable

---

## ✅ Étape 3 — Installer l'application

Deux options :

### Option A — Depuis le .dmg (recommandé)
```
dist/SalemService.dmg
```
Double-clic → glisse `SalemService.app` dans **Applications**.

### Option B — Copie directe
```bash
cp -r dist/SalemService.app /Applications/
```

---

## ▶️ Lancer l'application

- Double-clic sur **SalemService** dans Applications
- Ou depuis le Terminal :
```bash
open /Applications/SalemService.app
```

---

## ⚠️ Problème : "Impossible d'ouvrir car le développeur n'est pas identifié"

C'est une protection macOS Gatekeeper. Pour contourner :

1. **Clic droit** sur `SalemService.app` → **Ouvrir**
2. Cliquer **Ouvrir** dans la boîte de dialogue
3. L'app se lancera normalement à chaque fois ensuite

Ou depuis le Terminal :
```bash
xattr -rd com.apple.quarantine /Applications/SalemService.app
```

---

## 📂 Données de l'application

Les données (base de données, factures PDF, rapports) sont stockées dans :
```
~/Library/Application Support/GestionCommerciale/
```

Ce dossier survit aux mises à jour de l'application.

---

## 🔄 Mise à jour

Pour mettre à jour :
1. Remplacer les fichiers sources
2. Relancer `./build_mac.sh`
3. Copier la nouvelle version dans `/Applications`

Les données existantes ne sont **jamais effacées** lors d'une mise à jour.

---

## 🛠️ Tester sans builder (mode développement)

Si Python est installé sur le Mac, tu peux lancer directement :

```bash
cd gestion-commerciale
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

---

## 🔧 Support Apple Silicon (M1/M2/M3)

Le build détecte automatiquement l'architecture (`arm64` ou `x86_64`).  
Pour un build universel (compatible les deux) :

```bash
pip install pyinstaller
pyinstaller SalemService.spec --target-architecture universal2
```

> ⚠️ Le build universel nécessite que toutes les dépendances soient disponibles pour les deux architectures.

---

## 📞 Contact

**Salem Service** — Logiciel de gestion commerciale  
Version 1.0.0
