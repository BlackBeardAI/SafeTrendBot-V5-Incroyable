"""
SafeTrendBot V5 — Core modules
"""
from app.core.regime_detector import RegimeDetector, MarketRegime, RegimeResult
from app.core.adaptive_strategies import AdaptiveStrategyVoter, create_adaptive_voter, AdaptiveVoteResult
from app.core.portfolio_manager import PortfolioRiskManager, PortfolioMetrics
from app.core.performance_metrics import PerformanceTracker, PerformanceSnapshot
from app.core.trading_engine_v4 import TradingEngineV4, BotStatus, BotState
from app.core.system_tray_manager import SystemTrayManager

__all__ = [
    'RegimeDetector', 'MarketRegime', 'RegimeResult',
    'AdaptiveStrategyVoter', 'create_adaptive_voter', 'AdaptiveVoteResult',
    'PortfolioRiskManager', 'PortfolioMetrics',
    'PerformanceTracker', 'PerformanceSnapshot',
    'TradingEngineV4', 'BotStatus', 'BotState',
    'SystemTrayManager',
]
