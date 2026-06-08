# Publier SafeTrendBot sur GitHub (privé)

Trois méthodes, de la plus simple à la plus manuelle. Choisissez celle qui vous convient.

---

## ⚠️ Avant tout : vérifier qu'aucun secret ne fuite

Le `.gitignore` exclut déjà les fichiers sensibles (`.env`, credentials, logs, etc.), mais **vérifiez toujours** avant de pousser :

```bash
# Depuis le dossier trading_bot/
cat .gitignore
```

Si vous avez créé un `.env` avec votre token Telegram ou des credentials MT5, **il ne sera PAS poussé** (c'est voulu).

---

## Méthode 1 : Script automatique (le plus simple)

### Windows
Double-cliquez sur **`publish_to_github.bat`**. Le script fait tout :
1. Vérifie Git et GitHub CLI
2. Initialise le dépôt local
3. Crée le repo privé sur GitHub
4. Pousse le code

### Linux / Mac
```bash
chmod +x publish_to_github.sh
./publish_to_github.sh
```

---

## Méthode 2 : GitHub CLI (rapide, en ligne de commande)

Installation : https://cli.github.com/

```bash
# Se placer dans le dossier du projet
cd trading_bot

# Authentification (une seule fois)
gh auth login

# Initialiser git et tout pousser en une commande
git init -b main
git add .
git commit -m "Initial commit - SafeTrendBot v1.0"
gh repo create safetrendbot --private --source=. --remote=origin --push
```

C'est tout. Le repo privé est créé, le code est poussé, vous pouvez le voir sur github.com.

---

## Méthode 3 : Manuelle (sans outils extra, juste git)

### Étape 1 — Créer le repo sur GitHub

1. Allez sur https://github.com/new
2. Remplissez :
   - **Repository name** : `safetrendbot` (ou autre)
   - **Visibility** : ⚠️ **Private** (important !)
   - ❌ **NE PAS** cocher "Initialize this repository with a README"
   - ❌ **NE PAS** ajouter .gitignore ou license
3. Cliquez **Create repository**
4. Copiez l'URL HTTPS affichée (ex: `https://github.com/votrepseudo/safetrendbot.git`)

### Étape 2 — Pousser le code local

Depuis le dossier `trading_bot/` :

```bash
# Configurer git si c'est la première fois
git config --global user.email "vous@example.com"
git config --global user.name "Votre Nom"

# Initialiser
git init -b main
git add .
git commit -m "Initial commit - SafeTrendBot v1.0"

# Lier au repo GitHub
git remote add origin https://github.com/votrepseudo/safetrendbot.git

# Pousser
git push -u origin main
```

### Étape 3 — Authentification lors du push

GitHub ne permet plus les mots de passe directs depuis 2021. Vous devez utiliser un **Personal Access Token (PAT)** :

1. Allez sur https://github.com/settings/tokens
2. **Generate new token** → **Generate new token (classic)**
3. Cochez la case **repo** (accès complet aux repos privés)
4. **Generate token** → **copiez-le immédiatement** (visible une seule fois)
5. Au moment du `git push`, quand git demande :
   - **Username** : votre pseudo GitHub
   - **Password** : collez le TOKEN (pas votre mot de passe GitHub)

Le token est mémorisé par le credential manager de Windows, vous n'aurez plus à le retaper.

---

## Après la publication

### Vérifier que le repo est bien privé

1. Allez sur `https://github.com/votrepseudo/safetrendbot`
2. Vérifiez la présence du badge **Private** à côté du nom
3. En mode déconnecté, l'URL doit afficher 404

### Workflow quotidien

```bash
# Après modifications
git add .
git commit -m "Description des changements"
git push

# Récupérer les changements (si vous travaillez sur plusieurs PC)
git pull
```

### Inviter un collaborateur (optionnel)

1. Sur votre repo → **Settings** → **Collaborators**
2. **Add people** → entrer son pseudo/email GitHub
3. La personne reçoit une invitation par email

### Si vous avez committé un secret par erreur

**Stop, ne pushez pas davantage.** Deux options :

- **Avant push** : `git reset --soft HEAD~1` (annule le commit, garde les modifs)
- **Après push** : révoquez immédiatement le secret (changez le token, le mot de passe) puis utilisez `git filter-repo` ou `BFG Repo-Cleaner` pour purger l'historique

**Les secrets poussés en clair doivent être considérés comme compromis**, même dans un repo privé.

---

## Structure des branches recommandée

Pour un projet solo, restez simple :

```
main (branche stable, ce qui tourne chez vous)
  └── dev (expérimentations)
```

Pour créer une branche de dev :
```bash
git checkout -b dev
# ... travailler, commiter ...
git push -u origin dev

# Revenir à main
git checkout main

# Fusionner dev dans main quand c'est stable
git merge dev
git push
```

---

## Cloner le repo sur un autre PC

```bash
git clone https://github.com/votrepseudo/safetrendbot.git
cd safetrendbot
# Puis installer comme d'habitude
install.bat  # Windows
# ou
python main.py  # si déjà configuré
```

---

## Aide-mémoire sécurité

| Ne jamais committer | Alternative |
|---------------------|-------------|
| Token Telegram | Variable d'environnement ou `.env` |
| Login/password MT5 | Saisis dans l'UI, stockés en local (pas dans le repo) |
| Clés API brokers | Variables d'environnement |
| Logs de trading | Déjà dans `.gitignore` (`logs/`) |
| Fichiers de cache | Déjà dans `.gitignore` |

Le fichier `.gitignore` fourni couvre déjà tous ces cas. Ne le modifiez qu'en connaissance de cause.
