"""
SafeTrendBot V5 — Core modules extraordinaires
"""
from app.core.regime_detector import RegimeDetector, MarketRegime, RegimeResult
from app.core.adaptive_strategies import AdaptiveStrategyVoter, create_adaptive_voter, AdaptiveVoteResult
from app.core.portfolio_manager import PortfolioRiskManager, PortfolioMetrics
from app.core.performance_metrics import PerformanceTracker, PerformanceSnapshot
from app.core.trading_engine_v4 import TradingEngineV4, BotStatus, BotState
from app.core.system_tray_manager import SystemTrayManager

# V5 Extraordinaire
from app.core.walk_forward import WalkForwardAnalysis, WFAParams, WFAResult
from app.core.smart_order_routing import SmartOrderRouter, ExecutionType, ExecutionResult
from app.core.ml_regime_detector import MLRegimeDetector, MLRegimeResult
from app.core.triple_screen import TripleScreen, TripleScreenResult, TimeframeAlignment
from app.core.symbol_circuit_breaker import SymbolCircuitBreaker, SymbolCircuitState
from app.core.news_nlp import NewsNLPAnalyzer, SentimentResult
from app.core.broker_failover import BrokerFailover, BrokerConfig
from app.core.web_dashboard import WebDashboard
from app.core.parallel_backtest import ParallelBacktest, BacktestResult
from app.core.decision_journal import DecisionJournal, DecisionRecord

__all__ = [
    'RegimeDetector', 'MarketRegime', 'RegimeResult',
    'AdaptiveStrategyVoter', 'create_adaptive_voter', 'AdaptiveVoteResult',
    'PortfolioRiskManager', 'PortfolioMetrics',
    'PerformanceTracker', 'PerformanceSnapshot',
    'TradingEngineV4', 'BotStatus', 'BotState',
    'SystemTrayManager',
    # V5
    'WalkForwardAnalysis', 'WFAParams', 'WFAResult',
    'SmartOrderRouter', 'ExecutionType', 'ExecutionResult',
    'MLRegimeDetector', 'MLRegimeResult',
    'TripleScreen', 'TripleScreenResult', 'TimeframeAlignment',
    'SymbolCircuitBreaker', 'SymbolCircuitState',
    'NewsNLPAnalyzer', 'SentimentResult',
    'BrokerFailover', 'BrokerConfig',
    'WebDashboard',
    'ParallelBacktest', 'BacktestResult',
    'DecisionJournal', 'DecisionRecord',
]
