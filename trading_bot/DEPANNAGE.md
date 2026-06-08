# Dépannage install.bat

## Le script ne se lance pas du tout

### Cas 1 : Windows dit "Ce fichier est bloqué" ou SmartScreen bloque

**Solution :**
1. Clic droit sur `install.bat` → **Propriétés**
2. Tout en bas, cocher **"Débloquer"** (si la case existe)
3. Cliquer **OK**
4. Relancer `install.bat`

### Cas 2 : Rien ne se passe quand je double-clique

**Cause probable :** Windows Defender / antivirus bloque silencieusement le `.bat`.

**Solutions à essayer dans l'ordre :**

1. **Clic droit sur install.bat → "Exécuter en tant qu'administrateur"**
2. **Désactiver temporairement l'antivirus** le temps de l'installation
3. **Déplacer le projet** dans un dossier simple : `C:\SafeTrendBot\` (éviter les espaces/accents dans le chemin)

### Cas 3 : La fenêtre s'ouvre puis se ferme immédiatement

**Causes possibles :**

- Caractère invalide dans le chemin du dossier (accents, espaces multiples, caractères spéciaux)
- Le fichier `.bat` a été modifié et est corrompu
- Encoding incorrect (si vous l'avez édité dans un éditeur)

**Solution :**

1. Lancer `DIAGNOSTIC.bat` à la place — ce script reste ouvert et montre tous les problèmes
2. Ou ouvrir `cmd.exe` (touches Windows + R → taper `cmd` → Entrée)
3. Naviguer dans le dossier :
   ```
   cd /d C:\chemin\vers\trading_bot
   ```
4. Taper :
   ```
   install.bat
   ```
5. Vous verrez alors le message d'erreur exact.

### Cas 4 : "Python n'est pas reconnu comme commande"

**Cause :** Python n'est pas dans le PATH, ou pas installé.

**Solution :**
1. Télécharger Python 3.12 : https://www.python.org/downloads/
2. Lancer l'installateur
3. **IMPORTANT** : cocher ✅ **"Add Python to PATH"** sur le premier écran
4. Installer
5. Fermer et rouvrir toutes les fenêtres cmd
6. Relancer `install.bat`

---

## Ouvrir une console cmd dans le dossier

**Méthode la plus simple :**
1. Ouvrir l'Explorateur Windows dans le dossier `trading_bot`
2. Cliquer dans la barre d'adresse
3. Taper `cmd` → Entrée
4. Une console cmd s'ouvre déjà positionnée au bon endroit
5. Taper `install.bat` pour voir les erreurs

---

## L'installation se passe bien mais l'app ne démarre pas

Utiliser `launch_debug.bat` à la place de `launch.bat`.

Ce script lance l'app avec la console visible et affiche toutes les erreurs Python, s'il y en a.

---

## Rien ne marche : installation manuelle

Si `install.bat` refuse de fonctionner même avec le diagnostic :

1. Installer Python 3.12 depuis https://www.python.org (cocher "Add to PATH")
2. Ouvrir cmd dans le dossier `trading_bot`
3. Taper ligne par ligne :

```cmd
python -m venv venv
venv\Scripts\activate.bat
pip install PyQt6 numpy pandas yfinance matplotlib requests reportlab ib_insync
pip install MetaTrader5
python main.py
```

Si une étape échoue, notez le message d'erreur exact.

---

## Envoyer les infos pour support

Si rien ne fonctionne, lancez `DIAGNOSTIC.bat` et :
1. Clic droit dans la fenêtre → Sélectionner tout
2. Clic droit à nouveau → Copier
3. Collez-moi le résultat complet
