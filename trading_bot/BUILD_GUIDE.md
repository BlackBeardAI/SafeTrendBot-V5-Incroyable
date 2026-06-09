# Build SafeTrendBot — Binaires Cross-Platform

## 🎯 Objectif

Transformer SafeTrendBot en **binaires standalone** pour Windows, Linux et macOS — **aucun fichier .py visible** pour l'utilisateur final.

---

## 📦 Ce que vous obtenez

Après build, le dossier `releases/` contient :

```
releases/
├── SafeTrendBot-v5.X.X-windows-x64.zip       ← Windows 10/11 (x64)
├── SafeTrendBot-v5.X.X-linux-x64.tar.gz      ← Linux Ubuntu/Debian/Fedora
├── SafeTrendBot-v5.X.X-macos-x64.tar.gz      ← macOS Intel
└── SafeTrendBot-v5.X.X-macos-arm64.tar.gz    ← macOS Apple Silicon (M1/M2/M3)
```

Chaque archive contient :
- `SafeTrendBot` — **Application GUI** (clic pour lancer)
- `SafeTrendBotHeadless` — **Mode serveur** (terminal, VPS)
- `README.md`, `INSTALLATION.md`

**Aucun Python requis. Aucun fichier source visible.**

---

## 🔧 Prérequis

### Option 1: Build Local (une seule plateforme)

```bash
pip install pyinstaller cython pyarmor
```

### Option 2: Build Multi-Plateforme (recommandé)

Utilisez **GitHub Actions** — build automatique pour Windows + Linux + macOS en parallèle.

---

## 🚀 Build Rapide (Local)

```bash
cd trading_bot
python build_release.py
```

Résultat dans `releases/` — une seule archive pour votre OS.

---

## 🚀 Build Multi-Plateforme (GitHub Actions)

### Méthode 1: Push un tag

```bash
git tag -a v5.3.0 -m "Release v5.3.0"
git push origin v5.3.0
```

GitHub Actions compile automatiquement pour **Windows, Linux, macOS x64, macOS ARM64** et crée un Release avec les 4 archives.

### Méthode 2: Déclenchement manuel

1. Allez sur GitHub → Actions → "Build SafeTrendBot Releases"
2. Cliquez "Run workflow"
3. Entrez la version (ex: `5.3.0`)
4. Les binaires sont générés et attachés au workflow

---

## 🛡 Sécurité du Build

### 1. Obfuscation Cython (automatique)

Avant compilation, les fichiers critiques sont transformés en **code machine binaire** (.so / .pyd) :

- `license_manager.py` → illisible
- `anti_tamper.py` → illisible
- `trading_engine_v4.py` → illisible
- `extreme_guard.py` → illisible
- `trading_profiles.py` → illisible

### 2. Compilation PyInstaller

Le binaire final est un **fichier unique** contenant :
- L'interpréteur Python embarqué
- Toutes les dépendances
- Le code obfusqué
- **AUCUN** fichier .py visible

### 3. Anti-Tamper intégré

Le binaire vérifie au démarrage :
- Débogueur présent ? → Arrêt
- Machine virtuelle ? → Arrêt
- Fichiers modifiés ? → Arrêt

---

## 📋 Installation pour l'utilisateur final

### Windows
1. Télécharger `SafeTrendBot-v*-windows-x64.zip`
2. Extraire le ZIP
3. Double-cliquer `SafeTrendBot.exe`
4. Aucune installation requise

### Linux
```bash
# Télécharger
curl -L -o safetrendbot.tar.gz https://github.com/BlackBeardAI/SafeTrendBot-V5-Incroyable/releases/latest/download/SafeTrendBot-v5-linux-x64.tar.gz

# Extraire
tar -xzf safetrendbot.tar.gz
cd SafeTrendBot-v5-linux-x64

# Lancer GUI
chmod +x SafeTrendBot
./SafeTrendBot

# OU mode serveur
chmod +x SafeTrendBotHeadless
./SafeTrendBotHeadless --paper --symbols EURUSD,GBPUSD
```

### macOS (Intel)
```bash
tar -xzf SafeTrendBot-v5-macos-x64.tar.gz
cd SafeTrendBot-v5-macos-x64
chmod +x SafeTrendBot
./SafeTrendBot
```

### macOS (Apple Silicon M1/M2/M3)
```bash
tar -xzf SafeTrendBot-v5-macos-arm64.tar.gz
cd SafeTrendBot-v5-macos-arm64
chmod +x SafeTrendBot
./SafeTrendBot
```

Si Gatekeeper bloque : **Clic droit → Ouvrir** (une fois autorisé, ça fonctionne pour toujours).

---

## 🔒 Protection commerciale

### Licence requise

Chaque binaire nécessite une **licence valide** au premier démarrage :

1. L'utilisateur achète sur votre site
2. Il reçoit une **clé de licence** (format: `XXXX-XXXX-XXXX-XXXX`)
3. Il entre la clé dans le bot → activation automatique
4. La licence est **liée au hardware** (impossible de partager)

### Serveur d'activation

Vous devez héberger le serveur d'activation :

```bash
cd server
pip install -r requirements.txt
export SAFETRENDBOT_SECRET="votre_secret"
python activation_server.py
```

### 7 jours d'essai gratuit

Par défaut, chaque nouveau bot a **7 jours d'essai** sans licence.

---

## 🧪 Tester le binaire

Vérifiez que le binaire est vraiment standalone :

```bash
# Sur une machine VIERGE (sans Python installé)
./SafeTrendBot --version
```

Si ça affiche la version → ✅ Le binaire est standalone.

---

## 📊 Tailles attendues

| Plateforme | GUI | Headless |
|------------|-----|----------|
| Windows | ~180-250 MB | ~150-200 MB |
| Linux | ~160-220 MB | ~130-180 MB |
| macOS | ~170-240 MB | ~140-190 MB |

La taille inclut l'interpréteur Python + PyQt6 + numpy + toutes les dépendances.

---

## 🆘 Dépannage

### "SafeTrendBot.exe ne se lance pas"
→ Windows Defender peut bloquer. Ajoutez une exception.

### "cannot find libpython" sur Linux
→ Installez `libpython3.11` : `sudo apt-get install libpython3.11`

### Gatekeeper macOS
→ `xattr -cr SafeTrendBot` pour supprimer les attributs quarantaine.

---

**Pour toute question: README.md ou contact@safetrendbot.com**
