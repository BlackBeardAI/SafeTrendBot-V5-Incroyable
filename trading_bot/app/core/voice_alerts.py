"""
Voice Alerts — notifications vocales pour les événements critiques.
"""
from dataclasses import dataclass
from typing import Dict, List
from datetime import datetime, timedelta
import os


class VoiceAlertManager:
    """
    Gère les alertes vocales pour les événements critiques du bot.
    """

    def __init__(self, enabled: bool = True, cooldown_seconds: int = 30):
        self.enabled = enabled
        self.cooldown = cooldown_seconds
        self._last_alert: Dict[str, datetime] = {}

    def _can_alert(self, alert_type: str) -> bool:
        now = datetime.now()
        last = self._last_alert.get(alert_type)
        if last and (now - last).seconds < self.cooldown:
            return False
        self._last_alert[alert_type] = now
        return True

    def alert_position_opened(self, symbol: str, direction: str, price: float):
        if not self.enabled or not self._can_alert('open'):
            return
        text = f"Position {direction} ouverte sur {symbol} à {price:.5f}"
        self._speak(text)

    def alert_position_closed(self, symbol: str, profit: float, reason: str):
        if not self.enabled or not self._can_alert('close'):
            return
        if profit > 0:
            text = f"Trade gagnant sur {symbol}, profit {profit:+.2f} dollars"
        else:
            text = f"Trade perdant sur {symbol}, perte {profit:.2f} dollars"
        self._speak(text)

    def alert_circuit_breaker(self, reasons: List[str]):
        if not self.enabled or not self._can_alert('cb'):
            return
        text = f"Alerte! Circuit breaker activé. {reasons[0]}"
        self._speak(text)

    def alert_daily_target(self, pnl: float, target: float):
        if not self.enabled or not self._can_alert('target'):
            return
        pct = pnl / target * 100
        text = f"Objectif journalier à {pct:.0f} pour cent. PNL {pnl:+.2f}"
        self._speak(text)

    def alert_failover(self, old_broker: str, new_broker: str):
        if not self.enabled or not self._can_alert('failover'):
            return
        text = f"Basculement broker de {old_broker} vers {new_broker}"
        self._speak(text)

    def _speak(self, text: str):
        """Joue le texte via TTS"""
        try:
            # Utilise l'outil TTS du bot si disponible
            from hermes_tools import text_to_speech
            # En local, on utilise espeak ou say
            if os.system("which espeak > /dev/null 2>&1") == 0:
                os.system(f'espeak "{text}" 2>/dev/null')
            elif os.system("which say > /dev/null 2>&1") == 0:
                os.system(f'say "{text}"')
            else:
                print(f"[VOICE] {text}")
        except Exception:
            print(f"[VOICE] {text}")
