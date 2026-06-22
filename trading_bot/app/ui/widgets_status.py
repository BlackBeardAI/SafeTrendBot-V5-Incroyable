"""
Widget d'indicateur de statut du broker.
Affiche en permanence :
- Connexion broker (vert/rouge)
- Nombre de positions ouvertes
- Pourquoi le bot ne trade pas (si applicable)
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QScrollArea, QToolTip
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QPalette, QColor
from datetime import datetime

from app.ui.theme import COLORS


def c(key, default='#888888'):
    """Couleur sûre"""
    return COLORS.get(key, default)


class BrokerStatusIndicator(QWidget):
    """
    Indicateur de statut broker en temps réel.
    Point vert = connecté, rouge = déconnecté, orange = warning.
    Tooltip avec détails.
    """

    refresh_requested = pyqtSignal()

    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self.engine = engine
        self._build()

        # Refresh automatique toutes les 3 secondes
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(3000)
        # Premier refresh
        QTimer.singleShot(500, self.refresh)

    def _build(self):
        self.setMinimumHeight(40)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(10)

        # Point de statut (cercle coloré)
        self.status_dot = QLabel("●")
        self.status_dot.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        self.status_dot.setStyleSheet(f"color: {c('text_muted', '#64748b')};")
        layout.addWidget(self.status_dot)

        # Texte principal
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(1)

        self.main_label = QLabel("Broker : non vérifié")
        self.main_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        text_layout.addWidget(self.main_label)

        self.sub_label = QLabel("Cliquez sur Vérifier")
        self.sub_label.setFont(QFont("Segoe UI", 8))
        self.sub_label.setStyleSheet(f"color: {c('text_secondary', '#94a3b8')};")
        text_layout.addWidget(self.sub_label)

        layout.addLayout(text_layout, 1)

        # Bouton "Vérifier maintenant"
        self.refresh_btn = QPushButton("🔄")
        self.refresh_btn.setFixedSize(28, 28)
        self.refresh_btn.setToolTip("Vérifier la connexion au broker")
        self.refresh_btn.clicked.connect(self.refresh)
        self.refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 1px solid {c('border', '#1e293b')};
                border-radius: 14px;
                padding: 0;
            }}
            QPushButton:hover {{
                background-color: {c('hover', '#1e293b')};
            }}
        """)
        layout.addWidget(self.refresh_btn)

    def refresh(self):
        """Met à jour l'état en interrogeant le broker"""
        try:
            status = self._get_current_status()
            self._update_display(status)
        except Exception as e:
            self._update_display({
                'connected': False,
                'color': c('error', '#ef4444'),
                'main': 'Erreur',
                'sub': str(e)[:50],
            })

    def _get_current_status(self) -> dict:
        """Interroge le broker et retourne l'état actuel"""
        if self.engine is None:
            return {
                'connected': False,
                'color': c('text_muted', '#64748b'),
                'main': 'Moteur non initialisé',
                'sub': '',
            }

        # Tenter une connexion test (sans démarrer le bot)
        try:
            from app.brokers.factory import create_broker_adapter
            from app.brokers import BrokerType
            from app.core.config_manager import config_manager

            cfg = config_manager.config.broker
            broker_name = cfg.selected or "mt5"

            type_map = {
                "mt5": BrokerType.MT5,
                "xtb": BrokerType.XTB,
                "ib": BrokerType.INTERACTIVE_BROKERS,
            }
            broker_type = type_map.get(broker_name)
            if broker_type is None:
                return {
                    'connected': False,
                    'color': c('error', '#ef4444'),
                    'main': f'Broker inconnu : {broker_name}',
                    'sub': '',
                }

            # Si le bot tourne déjà, utiliser son adapter — NE PAS en créer un nouveau
            if (hasattr(self.engine, 'broker') and self.engine.broker is not None
                    and self.engine.broker.is_connected()):
                info = self.engine.broker.get_account_info()
                if info:
                    return {
                        'connected': True,
                        'color': c('success', '#10b981'),
                        'main': f'✓ {broker_name.upper()} connecté',
                        'sub': f'{info.name} · {info.balance:.2f} {info.currency}',
                    }

            # Test indépendant UNIQUEMENT si le bot n'est pas actif
            # Pour MT5 : on n'appelle JAMAIS disconnect() pour ne pas couper la connexion
            adapter = create_broker_adapter(broker_type)
            if adapter is None:
                return {
                    'connected': False,
                    'color': c('error', '#ef4444'),
                    'main': f'{broker_name.upper()} non installé',
                    'sub': 'Lib Python manquante',
                }

            ok = False
            if broker_name == "mt5":
                ok = adapter.connect(
                    auto_detect=cfg.mt5.auto_detect,
                    terminal_path=cfg.mt5.terminal_path,
                    login=cfg.mt5.login,
                    password=cfg.mt5.password,
                    server=cfg.mt5.server,
                )
            elif broker_name == "xtb":
                ok = adapter.connect(
                    user_id=cfg.xtb.user_id,
                    password=cfg.xtb.password,
                    demo=cfg.xtb.demo,
                )
            elif broker_name == "ib":
                ok = adapter.connect(
                    host=cfg.ib.host, port=cfg.ib.port,
                    client_id=cfg.ib.client_id,
                )

            if ok:
                info = adapter.get_account_info()
                # ⚠️ Pour MT5 : NE PAS appeler disconnect() car mt5.shutdown()
                # est global et couperait la connexion du moteur !
                if broker_name != "mt5":
                    adapter.disconnect()
                if info:
                    return {
                        'connected': True,
                        'color': c('success', '#10b981'),
                        'main': f'✓ {broker_name.upper()} connecté',
                        'sub': f'{info.name} · {info.balance:.2f} {info.currency}',
                    }
                return {
                    'connected': True,
                    'color': c('warning', '#f59e0b'),
                    'main': f'{broker_name.upper()} : compte illisible',
                    'sub': 'Connecté mais pas de compte',
                }
            else:
                err = adapter.get_last_error() or ""
                return {
                    'connected': False,
                    'color': c('error', '#ef4444'),
                    'main': f'✗ {broker_name.upper()} déconnecté',
                    'sub': self._friendly_error(err, broker_name),
                }
        except Exception as e:
            return {
                'connected': False,
                'color': c('error', '#ef4444'),
                'main': 'Erreur',
                'sub': str(e)[:60],
            }

    @staticmethod
    def _friendly_error(err: str, broker: str) -> str:
        """Transforme l'erreur brute en message compréhensible"""
        err_lower = err.lower()
        if broker == "mt5":
            if "not installed" in err_lower or "module" in err_lower:
                return "MT5 Python non installé"
            if "initialize" in err_lower or "not found" in err_lower:
                return "MT5 non lancé ou compte déconnecté"
            if "auto" in err_lower:
                return "Aucun terminal MT5 détecté"
        return err[:60] if err else "Connexion impossible"

    def _update_display(self, status: dict):
        """Met à jour l'affichage avec le statut"""
        self.status_dot.setStyleSheet(f"color: {status['color']};")
        self.main_label.setText(status['main'])
        self.sub_label.setText(status['sub'])

        # Couleur du texte principal
        if status.get('connected'):
            self.main_label.setStyleSheet(f"color: {c('success', '#10b981')};")
        else:
            self.main_label.setStyleSheet(f"color: {c('text_primary', '#f1f5f9')};")


class TradingStatusPanel(QFrame):
    """
    Panneau complet de diagnostic du bot :
    pourquoi il ne trade pas, quelles conditions sont remplies, etc.
    """

    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self.engine = engine
        self._build()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(5000)
        QTimer.singleShot(1000, self.refresh)

    def _build(self):
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(f"""
            TradingStatusPanel {{
                background-color: {c('card_bg', '#1a2028')};
                border: 1px solid {c('border', '#1e293b')};
                border-radius: 8px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        title = QLabel("🔍 Diagnostic du bot")
        title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout.addWidget(title)

        self.conditions_layout = QVBoxLayout()
        self.conditions_layout.setSpacing(4)
        layout.addLayout(self.conditions_layout)

        self._conditions_labels = {}

        # Créer les conditions
        conditions = [
            ('bot_running', 'Bot démarré'),
            ('broker_connected', 'Broker connecté'),
            ('mt5_autotrade', 'Trading automatique autorisé dans MT5'),
            ('symbols_configured', 'Symboles configurés'),
            ('market_hours', 'Dans les heures de trading'),
            ('market_open', 'Marché ouvert (forex fermé le week-end)'),
            ('no_circuit_breaker', 'Circuit breaker désactivé'),
            ('strategies_loaded', 'Stratégies chargées'),
        ]

        for key, label in conditions:
            row = QHBoxLayout()
            row.setSpacing(8)
            status_icon = QLabel("⏳")
            status_icon.setFixedWidth(20)
            text_label = QLabel(label)
            text_label.setStyleSheet(
                f"color: {c('text_secondary', '#94a3b8')};"
            )
            row.addWidget(status_icon)
            row.addWidget(text_label, 1)
            self.conditions_layout.addLayout(row)
            self._conditions_labels[key] = (status_icon, text_label)

        # Message global
        self.global_message = QLabel("")
        self.global_message.setWordWrap(True)
        self.global_message.setStyleSheet(
            f"color: {c('warning', '#f59e0b')}; "
            f"padding: 10px; background: rgba(245, 158, 11, 0.1); "
            f"border-radius: 4px; margin-top: 10px;"
        )
        layout.addWidget(self.global_message)

    def _set_condition(self, key, ok, hint=''):
        if key not in self._conditions_labels:
            return
        icon_label, text_label = self._conditions_labels[key]
        if ok:
            icon_label.setText("✓")
            icon_label.setStyleSheet(f"color: {c('success', '#10b981')};")
            text_label.setStyleSheet(
                f"color: {c('text_primary', '#f1f5f9')};"
            )
        else:
            icon_label.setText("✗")
            icon_label.setStyleSheet(f"color: {c('error', '#ef4444')};")
            text_label.setStyleSheet(
                f"color: {c('text_secondary', '#94a3b8')};"
            )
        if hint:
            text_label.setToolTip(hint)

    def refresh(self):
        """Met à jour tous les indicateurs"""
        try:
            self._check_all()
        except Exception as e:
            self.global_message.setText(f"Erreur diagnostic : {e}")

    def _check_all(self):
        from app.core.config_manager import config_manager
        cfg = config_manager.config

        issues = []

        # 1. Bot démarré
        bot_running = False
        if self.engine and hasattr(self.engine, 'state'):
            from app.core.bot_types import BotState
            bot_running = self.engine.state == BotState.RUNNING
        self._set_condition('bot_running', bot_running,
                            'Cliquez sur Démarrer dans le Dashboard')
        if not bot_running:
            issues.append("Le bot n'est pas démarré")

        # 2. Broker connecté
        broker_connected = False
        if self.engine and hasattr(self.engine, 'broker') and self.engine.broker:
            broker_connected = self.engine.broker.is_connected()
        self._set_condition('broker_connected', broker_connected,
                            'Ouvrez MT5 et connectez-vous à votre compte')
        if bot_running and not broker_connected:
            issues.append("Le bot tourne mais n'est pas connecté au broker")

        # 3. MT5 auto-trade (on ne peut pas vraiment vérifier depuis Python)
        # → on l'affiche comme "à vérifier" toujours si broker connecté
        if broker_connected:
            icon, text = self._conditions_labels['mt5_autotrade']
            icon.setText("?")
            icon.setStyleSheet(f"color: {c('warning', '#f59e0b')};")
            text.setToolTip(
                "À vérifier manuellement dans MT5 :\n"
                "Outils > Options > Expert Advisors\n"
                "Cocher 'Autoriser le trading automatique'"
            )
        else:
            self._set_condition('mt5_autotrade', False)

        # 4. Symboles configurés
        enabled_symbols = [s for s in cfg.symbols if s.enabled]
        self._set_condition('symbols_configured', len(enabled_symbols) > 0,
                            f'{len(enabled_symbols)} symbole(s) actif(s)')
        if not enabled_symbols:
            issues.append("Aucun symbole activé")

        # 5. Heures de trading
        now = datetime.now()
        in_hours = cfg.strategy.start_hour <= now.hour < cfg.strategy.end_hour
        self._set_condition('market_hours', in_hours,
                            f'Trading autorisé entre {cfg.strategy.start_hour}h et {cfg.strategy.end_hour}h')
        if not in_hours and bot_running:
            issues.append(f"Hors heures de trading ({cfg.strategy.start_hour}h-{cfg.strategy.end_hour}h)")

        # 6. Marché ouvert
        weekday = now.weekday()
        market_open = weekday < 5  # Lundi-Vendredi
        if weekday == 4 and not cfg.strategy.trade_on_friday:
            market_open = False
        self._set_condition('market_open', market_open,
                            'Le forex est fermé samedi-dimanche')
        if not market_open and bot_running:
            issues.append("Marché forex fermé (week-end)")

        # 7. Circuit breaker
        cb_ok = True
        if self.engine and hasattr(self.engine, 'circuit_breaker'):
            try:
                from app.core.market_filters import CircuitBreakerLevel
                cb_status = self.engine.circuit_breaker.check()
                cb_ok = cb_status.level != CircuitBreakerLevel.HALT
            except Exception:
                pass
        self._set_condition('no_circuit_breaker', cb_ok,
                            'Circuit breaker activé - reset requis')
        if not cb_ok and bot_running:
            issues.append("Circuit breaker déclenché")

        # 8. Stratégies
        strategies_ok = False
        if self.engine and hasattr(self.engine, 'voter') and self.engine.voter:
            strategies_ok = len(self.engine.voter.strategies) > 0
        self._set_condition('strategies_loaded', strategies_ok,
                            'Stratégies chargées')

        # Message global
        if issues:
            self.global_message.setText(
                "⚠️ Raisons probables pour lesquelles le bot ne trade pas :\n• " +
                "\n• ".join(issues)
            )
            self.global_message.setVisible(True)
        else:
            if bot_running and broker_connected:
                self.global_message.setText(
                    "✅ Toutes les conditions sont remplies. Le bot attend que les "
                    "stratégies détectent un signal valide. Les trades peuvent être "
                    "rares - c'est normal si vous avez configuré des critères stricts."
                )
                self.global_message.setStyleSheet(
                    f"color: {c('success', '#10b981')}; "
                    f"padding: 10px; background: rgba(16, 185, 129, 0.1); "
                    f"border-radius: 4px; margin-top: 10px;"
                )
            else:
                self.global_message.setText(
                    "💡 Pour que le bot trade : démarrez-le, connectez MT5, "
                    "et assurez-vous d'être en heures de marché (lundi-vendredi)."
                )
                self.global_message.setStyleSheet(
                    f"color: {c('text_secondary', '#94a3b8')}; "
                    f"padding: 10px; background: rgba(37, 99, 235, 0.1); "
                    f"border-radius: 4px; margin-top: 10px;"
                )
            self.global_message.setVisible(True)
