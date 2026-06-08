"""
Gestionnaire central de configuration et d'état de l'application.
Stocke tous les paramètres dans un JSON, gère les profils, les sauvegardes.
"""

import json
import os
from dataclasses import dataclass, asdict, field
from typing import List, Optional
from datetime import datetime
from pathlib import Path


def get_app_data_dir() -> Path:
    """Retourne le dossier de données de l'application (OS-dependent)"""
    if os.name == 'nt':  # Windows
        base = os.environ.get('APPDATA', os.path.expanduser('~'))
    else:
        base = os.path.expanduser('~/.config')
    path = Path(base) / 'SafeTrendBot'
    path.mkdir(parents=True, exist_ok=True)
    return path


@dataclass
class StrategyParams:
    """Paramètres de la stratégie de trading"""
    risk_percent: float = 1.0
    risk_reward_ratio: float = 2.0
    atr_period: int = 14
    atr_multiplier: float = 2.0
    atr_multiplier_sl: float = 1.5
    max_consecutive_losses: int = 3
    max_daily_loss_percent: float = 3.0
    fast_ema: int = 50
    slow_ema: int = 200
    rsi_period: int = 14
    rsi_overbought: float = 70.0
    rsi_oversold: float = 30.0
    start_hour: int = 0     # Forex tourne 24h/5 - couvrir toute la journée
    end_hour: int = 24
    trade_on_friday: bool = False
    min_bars_between_trades: int = 10
    magic_number: int = 20260416

    # Profil actif et paramètres dérivés
    active_profile: str = "normal"  # safe, normal, aggressive, trend_pure, etc.
    risk_per_trade: float = 1.0
    max_positions: int = 3
    daily_loss_limit_pct: float = 3.0
    max_drawdown_pct: float = 15.0
    min_strategies_agreement: int = 1   # 1 suffit (Normal), était 2
    min_confidence: float = 0.40        # 40 % au lieu de 50 %
    use_volatility_filter: bool = False  # Désactivé par défaut
    use_correlation_filter: bool = False
    use_news_filter: bool = False
    enable_trailing_stop: bool = True
    enable_breakeven: bool = True
    read_only_mode: bool = False  # Si True, le bot analyse mais ne trade pas


@dataclass
class SymbolConfig:
    """Configuration par symbole tradé"""
    symbol: str
    enabled: bool = True
    timeframe: str = "H1"   # H1 : 4x plus de signaux que H4
    custom_params: Optional[StrategyParams] = None


@dataclass
class MT5ConnectionConfig:
    """Paramètres de connexion MT5"""
    auto_detect: bool = True
    terminal_path: str = ""
    login: int = 0
    password: str = ""
    server: str = ""


@dataclass
class XTBConnectionConfig:
    """Paramètres de connexion XTB"""
    user_id: str = ""
    password: str = ""
    demo: bool = True  # True = compte démo, False = live


@dataclass
class IBConnectionConfig:
    """Paramètres de connexion Interactive Brokers"""
    host: str = "127.0.0.1"
    port: int = 7497
    client_id: int = 1


@dataclass
class CTraderConnectionConfig:
    """Paramètres de connexion cTrader"""
    client_id: str = ""
    client_secret: str = ""
    access_token: str = ""
    account_id: int = 0
    demo: bool = True


@dataclass
class CryptoConnectionConfig:
    """Paramètres de connexion pour un exchange crypto (Binance, Bybit, Kraken, Coinbase)"""
    api_key: str = ""
    api_secret: str = ""
    passphrase: str = ""       # Coinbase uniquement
    sandbox: bool = False      # Mode testnet si disponible


@dataclass
class BrokerConfig:
    """Configuration du broker actif"""
    selected: str = "mt5"      # "mt5", "xtb", "ib", "ctrader", "binance", "bybit", "kraken", "coinbase"
    mt5: MT5ConnectionConfig = field(default_factory=MT5ConnectionConfig)
    xtb: XTBConnectionConfig = field(default_factory=XTBConnectionConfig)
    ib: IBConnectionConfig = field(default_factory=IBConnectionConfig)
    ctrader: CTraderConnectionConfig = field(default_factory=CTraderConnectionConfig)
    binance: CryptoConnectionConfig = field(default_factory=CryptoConnectionConfig)
    bybit: CryptoConnectionConfig = field(default_factory=CryptoConnectionConfig)
    kraken: CryptoConnectionConfig = field(default_factory=CryptoConnectionConfig)
    coinbase: CryptoConnectionConfig = field(default_factory=CryptoConnectionConfig)


@dataclass
class TelegramConfig:
    """Configuration des alertes Telegram"""
    enabled: bool = False
    token: str = ""
    chat_id: str = ""
    alert_drawdown: bool = True
    alert_drawdown_threshold: float = 10.0
    alert_consecutive_losses: bool = True
    alert_position_open: bool = True
    alert_position_close: bool = True
    alert_news: bool = True
    alert_daily_report: bool = True
    daily_report_hour: int = 22


@dataclass
class NewsConfig:
    """Configuration du filtrage news"""
    enabled: bool = True
    blackout_minutes_before: int = 30
    blackout_minutes_after: int = 30
    block_high_impact: bool = True
    block_medium_impact: bool = False
    refresh_interval_minutes: int = 60


@dataclass
class UIConfig:
    """Préférences d'interface"""
    theme: str = "dark"  # "dark" ou "light"
    refresh_interval_seconds: int = 5
    chart_bars_displayed: int = 100
    show_notifications: bool = True
    minimize_to_tray: bool = True
    start_minimized: bool = False
    auto_start_bot: bool = False


from app.core.pin_lock import PinConfig


@dataclass
class AppConfig:
    """Configuration complète de l'application"""
    version: str = "2.1.0"
    profile_name: str = "default"
    strategy: StrategyParams = field(default_factory=StrategyParams)
    symbols: List[SymbolConfig] = field(default_factory=lambda: [
        SymbolConfig(symbol="EURUSD", timeframe="H1"),
        SymbolConfig(symbol="GBPUSD", timeframe="H1"),
        SymbolConfig(symbol="USDJPY", timeframe="H1"),
        SymbolConfig(symbol="XAUUSD", timeframe="H1"),
        SymbolConfig(symbol="AUDUSD", timeframe="H1"),
    ])
    broker: BrokerConfig = field(default_factory=BrokerConfig)
    # mt5 est conservé pour rétrocompatibilité v1 (lecture seule)
    mt5: MT5ConnectionConfig = field(default_factory=MT5ConnectionConfig)
    telegram: TelegramConfig = field(default_factory=TelegramConfig)
    news: NewsConfig = field(default_factory=NewsConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    security: PinConfig = field(default_factory=PinConfig)
    initial_capital: float = 10000.0
    broker_name: str = ""


class ConfigManager:
    """Gestionnaire singleton de la configuration"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self.app_data_dir = get_app_data_dir()
        self.config_file = self.app_data_dir / 'config.json'
        self.profiles_dir = self.app_data_dir / 'profiles'
        self.profiles_dir.mkdir(exist_ok=True)
        self.logs_dir = self.app_data_dir / 'logs'
        self.logs_dir.mkdir(exist_ok=True)

        self.config = self.load()

    def load(self) -> AppConfig:
        """Charge la configuration depuis le disque"""
        if not self.config_file.exists():
            config = AppConfig()
            self.save(config)
            return config

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return self._dict_to_config(data)
        except (IOError, json.JSONDecodeError, KeyError) as e:
            print(f"Erreur chargement config, utilisation par défaut : {e}")
            return AppConfig()

    def save(self, config: Optional[AppConfig] = None):
        """Sauvegarde la configuration"""
        if config is None:
            config = self.config
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(config), f, indent=2, default=str)
        except IOError as e:
            print(f"Erreur sauvegarde config : {e}")

    def _dict_to_config(self, data: dict) -> AppConfig:
        """Reconstruit AppConfig depuis un dict (gestion des champs manquants)"""
        default = AppConfig()

        strategy_data = data.get('strategy', {})
        strategy = StrategyParams(**{**asdict(default.strategy), **strategy_data})

        symbols_data = data.get('symbols', [])
        symbols = [
            SymbolConfig(
                symbol=s.get('symbol', 'EURUSD'),
                enabled=s.get('enabled', True),
                timeframe=s.get('timeframe', 'H1'),
            ) for s in symbols_data
        ] or default.symbols

        # Migration v1 → v2 : si pas de config broker mais mt5 existant, migrer
        mt5_data = data.get('mt5', {})
        mt5 = MT5ConnectionConfig(**{**asdict(default.mt5), **mt5_data})

        broker_data = data.get('broker', {})
        if broker_data:
            # Config v2 existante
            broker_mt5 = MT5ConnectionConfig(**{
                **asdict(default.broker.mt5),
                **broker_data.get('mt5', {})
            })
            broker_xtb = XTBConnectionConfig(**{
                **asdict(default.broker.xtb),
                **broker_data.get('xtb', {})
            })
            broker_ib = IBConnectionConfig(**{
                **asdict(default.broker.ib),
                **broker_data.get('ib', {})
            })
            broker_ctrader = CTraderConnectionConfig(**{
                **asdict(default.broker.ctrader),
                **broker_data.get('ctrader', {})
            })
            broker_binance = CryptoConnectionConfig(**{
                **asdict(default.broker.binance),
                **broker_data.get('binance', {})
            })
            broker_bybit = CryptoConnectionConfig(**{
                **asdict(default.broker.bybit),
                **broker_data.get('bybit', {})
            })
            broker_kraken = CryptoConnectionConfig(**{
                **asdict(default.broker.kraken),
                **broker_data.get('kraken', {})
            })
            broker_coinbase = CryptoConnectionConfig(**{
                **asdict(default.broker.coinbase),
                **broker_data.get('coinbase', {})
            })
            broker = BrokerConfig(
                selected=broker_data.get('selected', 'mt5'),
                mt5=broker_mt5, xtb=broker_xtb, ib=broker_ib,
                ctrader=broker_ctrader,
                binance=broker_binance, bybit=broker_bybit,
                kraken=broker_kraken, coinbase=broker_coinbase,
            )
        else:
            # Migration depuis v1
            broker = BrokerConfig(selected='mt5', mt5=mt5)

        telegram_data = data.get('telegram', {})
        telegram = TelegramConfig(**{**asdict(default.telegram), **telegram_data})

        news_data = data.get('news', {})
        news = NewsConfig(**{**asdict(default.news), **news_data})

        ui_data = data.get('ui', {})
        ui = UIConfig(**{**asdict(default.ui), **ui_data})

        security_data = data.get('security', {})
        security = PinConfig(**{**asdict(default.security), **security_data})

        return AppConfig(
            version=data.get('version', default.version),
            profile_name=data.get('profile_name', default.profile_name),
            strategy=strategy,
            symbols=symbols,
            broker=broker,
            mt5=mt5,
            telegram=telegram,
            news=news,
            ui=ui,
            security=security,
            initial_capital=data.get('initial_capital', default.initial_capital),
            broker_name=data.get('broker_name', default.broker_name),
        )

    def save_profile(self, name: str):
        """Sauvegarde la config actuelle comme profil nommé"""
        path = self.profiles_dir / f'{name}.json'
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(asdict(self.config), f, indent=2, default=str)

    def load_profile(self, name: str) -> bool:
        """Charge un profil existant"""
        path = self.profiles_dir / f'{name}.json'
        if not path.exists():
            return False
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.config = self._dict_to_config(data)
            self.save()
            return True
        except (IOError, json.JSONDecodeError):
            return False

    def list_profiles(self) -> List[str]:
        """Liste les profils disponibles"""
        return [p.stem for p in self.profiles_dir.glob('*.json')]

    def get_log_file(self, name: str = 'app') -> Path:
        """Retourne le chemin d'un fichier de log"""
        date_str = datetime.now().strftime('%Y-%m-%d')
        return self.logs_dir / f'{name}_{date_str}.log'


# Singleton accessible partout
config_manager = ConfigManager()
