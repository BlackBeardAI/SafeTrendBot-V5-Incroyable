# SafeTrendBot V5 — Installation Windows en 1 Clic

## 🚀 Installation Instantannée

### Étape 1 : Télécharger le Projet

**Option A : Téléchargement Direct**
1. Allez sur: https://github.com/BlackBeardAI/SafeTrendBot-V5-Incroyable
2. Cliquez绿色的 "Code" → "Download ZIP"
3. Extrayez le ZIP sur votre Bureau

**Option B : Git Clone**
```powershell
cd Desktop
git clone https://github.com/BlackBeardAI/SafeTrendBot-V5-Incroyable.git
```

### Étape 2 : Lancer l'Installation

1. Ouvrez le dossier `SafeTrendBot-V5-Incroyable`
2. **Double-cliquez sur `INSTALLER_WINDOWS.bat`**
3. Attendez que l'installation se termine (1-2 minutes)

### Étape 3 : Utiliser le Bot

Après installation, **double-cliquez sur `DEMARRER_SafeTrendBot.bat`**

---

## 📋 Fichiers Inclus

| Fichier | Description |
|---------|-------------|
| `INSTALLER_WINDOWS.bat` | Script d'installation 1 clic (à lancer 1 fois) |
| `DEMARRER_SafeTrendBot.bat` | Lance le bot (à utiliser à chaque fois) |
| `main.py` | Interface graphique |
| `headless.py` | Mode serveur (sans GUI) |
| `venv/` | Environnement Python (créé automatiquement) |

---

## ⚙️ Prérequis

- **Windows 10 ou 11** (64-bit)
- **Python 3.9+** (installé automatiquement si manquant)

Si Python n'est pas installé, le script vous guidera vers le téléchargement.

---

## 🔧 Dépannage

### "Python non trouvé"
1. Téléchargez Python: https://www.python.org/downloads/windows/
2. Pendant l'installation, **cochez "Add Python to PATH"**
3. Relancez `INSTALLER_WINDOWS.bat`

### "Module not found"
Relancez l'installation :
```powershell
cd %USERPROFILE%\SafeTrendBot-V5-Incroyable\trading_bot
INSTALLER_WINDOWS.bat
```

### Le bot ne se connecte pas à MT5
1. Ouvrez MetaTrader 5 manuellement
2. Connectez-vous à votre compte
3. Attendez 10 secondes
4. Relancez le bot

---

## 📁 Emplacement des Fichiers

```
C:\Users\TON_USER\Desktop\SafeTrendBot-V5-Incroyable\
├── trading_bot\
│   ├── DEMARRER_SafeTrendBot.bat    ← DOUBLE-CLIQUEZ ICI
│   ├── main.py                       
│   ├── headless.py                  
│   ├── app\                          
│   │   ├── core\                    
│   │   │   ├── license_manager.py   
│   │   │   └── trading_engine.py    
│   │   └── brokers\                 
│   └── venv\                        
└── INSTALLER_WINDOWS.bat            
```

---

## 🔐 Votre Licence

Après installation:
1. Lancez le bot (`DEMARRER_SafeTrendBot.bat`)
2. Entrez votre clé de licence quand demandé
3. Le bot est lié à votre PC

**Votre licence se trouve dans:**
`C:\Users\TON_USER\.safetrendbot\license.json`

---

## 🔄 Mettre à Jour

```powershell
cd %USERPROFILE%\SafeTrendBot-V5-Incroyable
git pull origin main
```

---

## 🆘 Support

- **Logs**: `C:\Users\TON_USER\.safetrendbot\bot.log`
- **Erreurs**: Regardez le fichier log pour diagnostics

---

*SafeTrendBot V5.3.0 — Trading Bot*