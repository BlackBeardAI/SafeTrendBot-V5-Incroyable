"""
Système d'alertes Telegram pour le bot de trading.
Envoie des notifications push pour les événements importants :
- Drawdown excessif
- Pertes consécutives
- Positions importantes ouvertes/fermées
- News à haut impact à venir
- Problèmes de connexion

PRÉREQUIS - Créer un bot Telegram :
1. Sur Telegram, chercher @BotFather
2. Envoyer /newbot et suivre les instructions
3. Récupérer le TOKEN fourni (format: 123456:ABC-DEF1234...)
4. Démarrer une conversation avec votre nouveau bot
5. Obtenir votre CHAT_ID en envoyant /start à @userinfobot

Puis créer un fichier .env à la racine du projet :
    TELEGRAM_TOKEN=votre_token_ici
    TELEGRAM_CHAT_ID=votre_chat_id_ici

Usage :
    from telegram_alerts import AlertSystem
    alerts = AlertSystem()
    alerts.send("Test message")
    alerts.alert_drawdown(12.5)
"""

import os
import requests
from datetime import datetime
from typing import Optional
from enum import Enum


class AlertLevel(Enum):
    INFO = "ℹ️"
    SUCCESS = "✅"
    WARNING = "⚠️"
    ERROR = "🚨"
    CRITICAL = "⛔"


class AlertSystem:
    """Système d'alertes via Telegram"""

    TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"

    def __init__(self, token: Optional[str] = None, chat_id: Optional[str] = None):
        # Lecture depuis variables d'environnement ou paramètres
        self.token = token or os.getenv('TELEGRAM_TOKEN')
        self.chat_id = chat_id or os.getenv('TELEGRAM_CHAT_ID')

        # Essayer de charger un fichier .env si présent
        if not self.token or not self.chat_id:
            self._load_env_file()

        self.enabled = bool(self.token and self.chat_id)
        if not self.enabled:
            print("[AlertSystem] Désactivé - TELEGRAM_TOKEN et TELEGRAM_CHAT_ID manquants")

    def _load_env_file(self):
        """Charge les variables depuis un fichier .env à la racine"""
        env_paths = ['.env', '../.env', '../../.env']
        for path in env_paths:
            if os.path.exists(path):
                try:
                    with open(path, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if not line or line.startswith('#'):
                                continue
                            if '=' in line:
                                key, value = line.split('=', 1)
                                key = key.strip()
                                value = value.strip().strip('"').strip("'")
                                if key == 'TELEGRAM_TOKEN' and not self.token:
                                    self.token = value
                                elif key == 'TELEGRAM_CHAT_ID' and not self.chat_id:
                                    self.chat_id = value
                    break
                except IOError:
                    continue

    def send(self, message: str, level: AlertLevel = AlertLevel.INFO,
             silent: bool = False) -> bool:
        """
        Envoie un message Telegram.
        Retourne True si succès, False sinon.
        """
        if not self.enabled:
            print(f"[Alert non envoyée] {level.value} {message}")
            return False

        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        formatted = f"{level.value} *SafeTrendBot*\n\n{message}\n\n`{timestamp}`"

        url = self.TELEGRAM_API.format(token=self.token)
        payload = {
            'chat_id': self.chat_id,
            'text': formatted,
            'parse_mode': 'Markdown',
            'disable_notification': silent,
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            print(f"[AlertSystem] Erreur envoi : {e}")
            return False

    # ========================================================================
    # ALERTES PRÉDÉFINIES
    # ========================================================================

    def alert_drawdown(self, drawdown_pct: float, threshold: float = 10.0):
        """Alerte drawdown"""
        if abs(drawdown_pct) < threshold:
            return

        level = AlertLevel.WARNING if abs(drawdown_pct) < 15 else AlertLevel.CRITICAL
        msg = (
            f"*Drawdown détecté : {drawdown_pct:.2f} %*\n\n"
            f"Seuil d'alerte : {threshold}%\n"
            f"Vérifiez les conditions de marché et considérez "
            f"une pause du bot si le drawdown s'aggrave."
        )
        self.send(msg, level=level)

    def alert_consecutive_losses(self, count: int, max_allowed: int):
        """Alerte pertes consécutives"""
        if count < max_allowed - 1:
            return

        if count >= max_allowed:
            level = AlertLevel.CRITICAL
            msg = (
                f"*Bot arrêté : {count} pertes consécutives*\n\n"
                f"Limite atteinte ({max_allowed}). "
                f"Intervention manuelle requise pour redémarrer.\n\n"
                f"Recommandations :\n"
                f"• Vérifier les conditions de marché\n"
                f"• Re-backtester avec données récentes\n"
                f"• Envisager une pause de 1-2 semaines"
            )
        else:
            level = AlertLevel.WARNING
            msg = (
                f"*Attention : {count} pertes consécutives*\n\n"
                f"Une perte supplémentaire déclenchera l'arrêt du bot."
            )
        self.send(msg, level=level)

    def alert_position_opened(self, symbol: str, direction: str,
                              volume: float, entry: float, sl: float, tp: float,
                              strategy: str = "", confidence: float = 0,
                              atr: float = 0, session: str = ""):
        """Notification d'ouverture de position — enrichie"""
        risk_pips = abs(entry - sl) / 0.0001 if 'JPY' not in symbol else abs(entry - sl) / 0.01
        reward_pips = abs(tp - entry) / 0.0001 if 'JPY' not in symbol else abs(tp - entry) / 0.01
        rr = reward_pips / risk_pips if risk_pips > 0 else 0

        dir_emoji = "🟢 ACHAT" if direction.upper() in ("BUY", "ACHAT") else "🔴 VENTE"

        # Barre de confiance visuelle
        conf_bars = int(confidence * 10)
        conf_visual = "█" * conf_bars + "░" * (10 - conf_bars)

        lines = [
            f"*{dir_emoji} — {symbol}*",
            "",
            f"🔢 Volume : `{volume:.2f}` lots",
            f"💵 Entrée : `{entry:.5f}`",
            f"🛑 Stop Loss : `{sl:.5f}` ({risk_pips:.0f} pips)",
            f"🎯 Take Profit : `{tp:.5f}` ({reward_pips:.0f} pips)",
            f"⚖️ Ratio R:R : `1:{rr:.1f}`",
        ]
        if confidence > 0:
            lines.append(f"💡 Confiance : `{conf_visual}` {confidence:.0%}")
        if strategy:
            lines.append(f"📐 Stratégie : {strategy}")
        if session:
            lines.append(f"🕐 Session : {session}")

        self.send("\n".join(lines), level=AlertLevel.INFO, silent=True)

    def alert_position_closed(self, symbol: str, profit: float, reason: str,
                              pips: float = 0, duration_min: int = 0,
                              win_rate_today: float = 0):
        """Notification de clôture — enrichie avec contexte"""
        level = AlertLevel.SUCCESS if profit >= 0 else AlertLevel.WARNING
        result_emoji = "✅ GAIN" if profit >= 0 else "❌ PERTE"
        profit_emoji = "💰" if profit >= 0 else "💸"

        lines = [
            f"*{result_emoji} — {symbol}* {profit_emoji}",
            "",
            f"💵 P&L : `{profit:+.2f}`",
            f"📍 Raison : {reason}",
        ]
        if pips != 0:
            lines.append(f"📏 Pips : `{pips:+.1f}`")
        if duration_min > 0:
            if duration_min < 60:
                dur_str = f"{duration_min}min"
            else:
                dur_str = f"{duration_min//60}h{duration_min%60:02d}min"
            lines.append(f"⏱️ Durée : {dur_str}")
        if win_rate_today > 0:
            lines.append(f"📊 Win rate aujourd'hui : `{win_rate_today:.0%}`")

        self.send("\n".join(lines), level=level, silent=(profit >= 0))

    def alert_high_impact_news(self, event_title: str, country: str, time_until: str):
        """Alerte news à haut impact imminente"""
        msg = (
            f"*News à haut impact dans {time_until}*\n\n"
            f"🌍 {country}\n"
            f"📰 {event_title}\n\n"
            f"Le bot ne tradera pas durant la fenêtre de sécurité (±30 min)."
        )
        self.send(msg, level=AlertLevel.INFO, silent=True)

    def alert_low_margin(self, margin_level: float):
        """Alerte niveau de marge faible"""
        if margin_level > 300:
            return
        level = AlertLevel.CRITICAL if margin_level < 150 else AlertLevel.WARNING
        msg = (
            f"*Niveau de marge faible : {margin_level:.0f}%*\n\n"
            f"Risque de margin call en approche.\n"
            f"Fermeture automatique de positions possible par le broker."
        )
        self.send(msg, level=level)

    def alert_daily_report(self, trades: int, pnl: float, win_rate: float,
                          balance: float):
        """Rapport journalier"""
        pnl_emoji = "📈" if pnl >= 0 else "📉"
        msg = (
            f"*Rapport journalier* {pnl_emoji}\n\n"
            f"Trades : {trades}\n"
            f"P&L : {pnl:+.2f}\n"
            f"Win rate : {win_rate:.1f}%\n"
            f"Balance : {balance:,.2f}"
        )
        self.send(msg, level=AlertLevel.INFO, silent=True)

    def alert_connection_lost(self):
        """Alerte perte de connexion"""
        msg = (
            "*Connexion MT5 perdue*\n\n"
            "Le bot ne peut plus surveiller les positions.\n"
            "Vérifiez :\n"
            "• MT5 est lancé\n"
            "• Connexion internet OK\n"
            "• Serveur broker accessible"
        )
        self.send(msg, level=AlertLevel.ERROR)

    def test(self):
        """Test d'envoi"""
        return self.send(
            "Test de connexion Telegram réussi. Le système d'alertes est opérationnel.",
            level=AlertLevel.SUCCESS
        )


if __name__ == '__main__':
    import sys

    alerts = AlertSystem()
    
    if not alerts.enabled:
        print("\n⚠️  Configuration manquante. Créez un fichier .env avec :")
        print("    TELEGRAM_TOKEN=votre_token")
        print("    TELEGRAM_CHAT_ID=votre_chat_id")
        print("\nVoir les instructions en haut du fichier telegram_alerts.py")
        sys.exit(1)

    print("Envoi d'un message de test...")
    if alerts.test():
        print("✅ Message envoyé avec succès")
    else:
        print("❌ Échec de l'envoi")
