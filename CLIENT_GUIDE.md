# SafeTrendBot V5 — Guide d'Installation Client

Bienvenue dans SafeTrendBot V5! Ce guide vous accompagne pas à pas.

---

## 📦 Contenu du ZIP

Après achat, vous recevez un fichier ZIP contenant :

```
SafeTrendBot_[tier]_[date].zip
├── SafeTrendBot_[tier].exe     ← Le bot (double-cliquez ici)
├── README.txt                    ← Instructions rapides
└── _ADMIN_LICENSE.txt            ← Votre licence (gardez-la!)
```

---

## 🚀 Installation (2 minutes)

### 1. Extraire le ZIP

- **Windows** : Clic droit → "Extraire tout..." → Choisissez le Bureau ou Documents
- Le dossier extrait contient `SafeTrendBot_[tier].exe`

### 2. Double-cliquez le fichier .exe

- Windows SmartScreen peut afficher un avertissement (certificat auto-signé)
- Cliquez **"Plus d'infos"** → **"Exécuter quand même"**

### 3. Activation automatique

Au premier lancement :
1. Le bot vérifie votre licence
2. L'enregistre sur CET ordinateur (CPU + disque)
3. Le fichier d'installation se supprime automatiquement
4. Les données sont chiffrées

✅ **Le bot est prêt!**

---

## ⚙️ Première configuration

### Connexion broker

1. Ouvrez l'onglet **"Broker"**
2. Sélectionnez votre broker (MT5, XTB, Interactive Brokers...)
3. Entrez vos credentials
4. Cliquez **"Connecter"**

> 🔒 Vos credentials sont chiffrés localement avec AES-256.

### Choisir le mode de trading

| Votre profil | Mode recommandé |
|--------------|-----------------|
| Débutant / Capital important | 🛡️ Safe (0.5% risque) |
| Standard | ⚖️ Normal (1% risque) |
| Expérimenté | 🔥 Aggressive (2% risque) |
| Recherche rendement max | 🔥🔥 EXTREME (5% risque) |

**Comment changer :** Menu → Profils → Sélectionner

### Paper Trading (recommandé)

Avant de trader en réel, testez en **paper trading** :
1. Onglet **"Paper Trading"**
2. Activez le mode simulation
3. Le bot simule les trades sans risquer de vrai capital
4. Testez 2-4 semaines avant de passer en réel

---

## 📊 Utilisation quotidienne

### Lancer le bot

1. Double-cliquez `SafeTrendBot_[tier].exe`
2. Le bot démarre dans la barre des tâches (system tray)
3. Clic droit sur l'icône pour accéder au menu

### Voir les signaux

- Onglet **"Signaux"** : trades en temps réel
- Onglet **"Positions"** : positions ouvertes
- Onglet **"Dashboard"** : performance globale

### Recevoir des alertes

Le bot peut envoyer des alertes via :
- Telegram (configurez dans Paramètres)
- Notifications vocales (si activé)
- Pop-up Windows

---

## 🔄 Mise à jour

Le bot vérifie automatiquement les mises à jour :
- **Au démarrage** : vérification silencieuse
- **Toutes les 24h** : check automatique
- Si une mise à jour est disponible, une notification s'affiche

**Pour mettre à jour manuellement :**
```
Menu → Aide → Vérifier les mises à jour
```

---

## 🆘 Dépannage

| Problème | Solution |
|----------|----------|
| "Licence invalide" | Ce build a déjà été activé sur un autre PC. Contactez le support. |
| "Connexion broker échouée" | Vérifiez vos credentials, vérifiez que le broker tourne. |
| "Aucun trade" | Vérifiez le mode (paper vs live), vérifiez les filtres. |
| "Bot crash" | Redémarrez, vérifiez la connexion internet. |
| SmartScreen bloque | Clic droit → Propriétés → Débloquer. |

---

## 📞 Support

- **Email :** contact@safetrendbot.com
- **Dashboard admin :** https://217.160.191.107:8443

---

## ⚠️ Avertissements Importants

1. **Le trading comporte des risques.** Vous pouvez perdre votre capital.
2. **Testez en paper trading** avant tout capital réel (minimum 2 semaines).
3. **Le mode EXTREME** peut entraîner des pertes jusqu'à 30%.
4. **Ne tradez pas** avec de l'argent dont vous avez besoin.
5. **Chaque build est lié à un PC.** En cas de changement de machine, nouvelle licence requise.

---

**SafeTrendBot V5 — Trade smart, stay safe.**
