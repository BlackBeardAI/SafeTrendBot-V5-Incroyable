# SafeTrendBot V5 — GUIDE DE COMPILATION
# ========================================
# Ce guide explique comment créer un .exe PROTÉGÉ que le client ne peut pas lire.

## OPTION 1: Utiliser le BUILDER (Recommandé)

```bash
cd /root/SafeTrendBot-V5-Incroyable/trading_bot

# Lancer le Builder GUI
python builder/builder_gui.py

# Ou en ligne de commande:
python builder/license_builder.py build \
    --email client@example.com \
    --platform windows
```

Le Builder va :
1. ✅ Générer une clé de licence unique
2. ✅ Injecter la clé dans le code
3. ✅ Compiler avec PyInstaller → .exe
4. ✅ Créer un ZIP prêt à分发

---

## OPTION 2: Compilation Manuelle

```bash
cd /root/SafeTrendBot-V5-Incroyable/trading_bot

# Installer PyInstaller
pip install pyinstaller pyarmor

# Compiler avec PyInstaller
pyinstaller --onefile --windowed --name SafeTrendBotV5 main.py

# Le .exe est dans: dist/SafeTrendBotV5.exe
```

---

## OPTION 3: Compilation + Obfuscation (MEILLEURE)

```bash
# 1. Obfusquer avec PyArmor
pyarmor gen --output dist/app app/

# 2. Compiler le résultat avec PyInstaller
pyinstaller --onefile --add-data "dist/app;app" main.py
```

---

## COMMENT ÇA MARCHE

```
CODE SOURCE (.py)          EXÉCUTABLE (.exe)
─────────────────          ───────────────────
                           
app/
├── core/          pyarmor    ┌─────────────────┐
│   ├── license_   ──────────▶ │                 │
│   │   manager.py            │   SafeTrendBot  │
│   ├── trading_              │      .exe        │
│   │   engine.py            │                 │
│   └── ...                   │   Client ne peut │
└── main.py                   │   PAS voir le   │
      │                       │   code source!  │
      └────── pyinstaller ───▶ │                 │
                              └─────────────────┘

CLIENT VOIT:
├── SafeTrendBot.exe     ← CODE CACHÉ À L'INTÉRIEUR
├── AUTO_INSTALL.bat      ← Instructions
└── FICHE_VENTE.txt      ← Prix et wallets
```

---

## DIFFÉRENCE VISUELLE

### ❌ SANS COMPILATION (code lisible)
```
Le client reçoit un dossier .py:

trading_bot/
├── app/
│   ├── core/
│   │   ├── license_manager.py   ← LISIBLE
│   │   └── trading_engine.py   ← LISIBLE
│   └── ...
├── main.py                     ← LISIBLE
└── ...
```

### ✅ AVEC COMPILATION (code caché)
```
Le client reçoit:

SafeTrendBot-V5/
├── SafeTrendBot.exe            ← COMPILÉ, IN LISIBLE
├── AUTO_INSTALL.bat
├── LANCER_SafeTrendBot.bat
└── FICHE_VENTE.txt
```

---

## RÉSUMÉ

| Pour protéger le code | Utilise |
|----------------------|---------|
| Cacher le code Python | PyInstaller (`pyinstaller --onefile`) |
| Rendre le bytecode illisible | PyArmor (`pyarmor gen`) |
| Les deux | PyArmor + PyInstaller |

---

## IMPORTANT

Même avec PyInstaller, le code tourne sur la machine du client.
QLQN peut théoriquement désassembler, mais c'est :
1. **Technique** complexe
2. **Illégal** (contredit les CGU)
3. **Inutile** car le HW-lock empêche quand même la copie

**PyInstaller suffit** pour 99% des cas.

---

*Pour des besoins极高, vois: Nuitka, Cython, ou obfuscateurs commerciaux*