"""
Guide de compilation SafeTrendBot V5 en .exe commercial
=======================================================

OBJECTIF : transformer le projet Python en .exe standalone
           avec le code critique compilé en binaire (illisible).

PRÉREQUIS
---------
1. Python 3.11 (la version la plus stable pour PyInstaller)
2. pip install pyinstaller cython pyarmor
3. Windows: Visual C++ Build Tools (pour Cython)
   Linux: sudo apt-get install build-essential python3-dev

ÉTAPES
------

### 1. Compiler les fichiers critiques (optionnel mais RECOMMANDÉ)

Cela transforme license_manager.py, anti_tamper.py, trading_engine_v4.py
en fichiers binaires .pyd (Windows) ou .so (Linux).
Le code source devient illisible.

    python compile_critical.py

Résultat: des fichiers comme license_manager.cpython-311-x86_64-linux-gnu.so

### 2. Supprimer les sources Python critiques (AVANT distribution!)

⚠️  NE PAS supprimer les .py du dossier source de développement!
    Copiez d'abord le projet dans un dossier "dist_source" propre.

Dans le dossier de distribution:

    del app/core/license_manager.py
    del app/core/anti_tamper.py
    del app/core/trading_engine_v4.py
    del app/core/adaptive_strategies.py
    del app/core/regime_detector.py
    del app/core/strategies.py

Gardez SEULEMENT les .pyd / .so générés à l'étape 1.

### 3. Compiler l'application complète en .exe

    python build.py

Ou manuellement:

    pyinstaller main.py \
        --name SafeTrendBot \
        --onefile \  # OU --onedir pour plus rapide
        --windowed \  # Pas de console noire
        --icon=icon.ico \
        --add-data "app;app" \
        --add-data "bot;bot" \
        --hidden-import app.core.license_manager \
        --hidden-import app.core.anti_tamper \
        --hidden-import app.core.trading_engine_v4

### 4. Résultat

Le .exe est dans: dist/SafeTrendBot.exe (ou dist/SafeTrendBot/SafeTrendBot.exe)

Testez-le sur une machine SANS Python installé pour vérifier
qu'il est vraiment standalone.

SÉCURITÉ
--------
- Changez la SECRET_KEY dans license_manager.py AVANT compilation
- Changez-la aussi dans server/activation_server.py
- N'incluez JAMAIS vos vraies clés API dans le .exe
- Utilisez des variables d'environnement pour les credentials

ANTI-DÉCOMPILATION
------------------
Même en .exe, le code Python peut être extrait. Contre-mesures:

1. Cython (compile_critical.py) → code machine
2. PyArmor (pip install pyarmor) → obfuscation supplémentaire
3. UPX compression (inclus dans build.py) → rend l'analyse plus difficile
4. Code signing (optionnel) → certificat Windows pour authenticité

LIMITATIONS
-----------
Aucun système n'est inviolable. Un hacker motivé peut:
- Dumper la mémoire du processus
- Hooker les fonctions de vérification
- Désassembler le .pyd compilé

Mais le coût technique augmente énormément, dissuadant 99% des attaquants.

SUPPORT
-------
Pour des questions: README.md ou contact@safetrendbot.com
"""
