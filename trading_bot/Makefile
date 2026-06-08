# Makefile pour SafeTrendBot V5
# Usage: make install | make run | make headless | make test

.PHONY: install run headless test clean docker-build docker-run logs status

PYTHON := python3
PIP := pip3

install:
	@echo "🚀 Installation SafeTrendBot V5..."
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@echo "✅ Installation terminée"

install-ml:
	@echo "🧠 Installation dépendances ML..."
	$(PIP) install scikit-learn hmmlearn transformers torch

install-web:
	@echo "🌐 Installation dépendances Web Dashboard..."
	$(PIP) install fastapi uvicorn websockets

run:
	@echo "🖥️  Lancement UI..."
	$(PYTHON) main.py

headless:
	@echo "🤖 Lancement mode headless..."
	$(PYTHON) headless.py --paper

headless-live:
	@echo "⚠️  Lancement mode headless LIVE"
	$(PYTHON) headless.py

test:
	@echo "🧪 Tests..."
	$(PYTHON) -c "from app.core.trading_engine_v4 import TradingEngineV4; print('✅ Engine OK')"
	$(PYTHON) -c "from app.core.regime_detector import RegimeDetector; print('✅ Regime OK')"
	$(PYTHON) -c "from app.core.adaptive_strategies import create_adaptive_voter; print('✅ Strategies OK')"
	$(PYTHON) -c "from app.core.triple_screen import TripleScreen; print('✅ Triple Screen OK')"
	$(PYTHON) -c "from app.core.parallel_backtest import ParallelBacktest; print('✅ Backtest OK')"
	@echo "✅ Tous les tests passés"

clean:
	@echo "🧹 Nettoyage..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete
	rm -rf build/ dist/ *.egg-info/

logs:
	@echo "📋 Derniers logs..."
	tail -n 50 ~/.safetrendbot/logs/trading.log 2>/dev/null || echo "Pas encore de logs"

status:
	@systemctl --user status safetrendbot 2>/dev/null || echo "Service non actif (mode UI ou headless manuel)"

docker-build:
	@echo "🐳 Build Docker..."
	docker build -t safetrendbot:v5 .

docker-run:
	@echo "🐳 Run Docker..."
	docker run -p 8080:8080 -v safetrendbot-data:/data safetrendbot:v5
