"""
Web Dashboard — interface web temps réel via FastAPI + WebSocket.
Accès depuis n'importe quel appareil, pas besoin de PyQt.
"""
import asyncio
import json
from datetime import datetime
from typing import Dict, Optional, Set
from dataclasses import asdict

try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
    from fastapi.responses import HTMLResponse
    from fastapi.middleware.cors import CORSMiddleware
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    FastAPI = None
    WebSocket = None
    WebSocketDisconnect = None
    HTMLResponse = None
    CORSMiddleware = None


HTML_DASHBOARD = """
<!DOCTYPE html>
<html>
<head>
    <title>SafeTrendBot V5 — Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #0f0f1a; color: #e0e0ff; margin: 0; padding: 20px; }
        h1 { color: #cba6f7; margin: 0 0 10px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; margin: 20px 0; }
        .card { background: #1a1a2e; border-radius: 12px; padding: 20px; border: 1px solid #313244; }
        .card h3 { margin: 0 0 10px; color: #89b4fa; font-size: 14px; text-transform: uppercase; }
        .value { font-size: 28px; font-weight: bold; color: #cdd6f4; }
        .positive { color: #a6e3a1; }
        .negative { color: #f38ba8; }
        .neutral { color: #f9e2af; }
        .status-dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 8px; }
        .running { background: #a6e3a1; }
        .stopped { background: #f38ba8; }
        #logs { max-height: 300px; overflow-y: auto; font-family: monospace; font-size: 12px; }
        .log-line { padding: 3px 0; border-bottom: 1px solid #1e1e2e; }
    </style>
</head>
<body>
    <h1>🤖 SafeTrendBot V5 — Dashboard</h1>
    <div id="status"><span class="status-dot stopped"></span>Connecté...</div>
    <div class="grid">
        <div class="card"><h3>État</h3><div class="value" id="state">—</div></div>
        <div class="card"><h3>Régime</h3><div class="value" id="regime">—</div></div>
        <div class="card"><h3>P&L Jour</h3><div class="value" id="pnl">—</div></div>
        <div class="card"><h3>Positions</h3><div class="value" id="positions">—</div></div>
        <div class="card"><h3>Sharpe</h3><div class="value" id="sharpe">—</div></div>
        <div class="card"><h3>Max DD</h3><div class="value" id="maxdd">—</div></div>
        <div class="card"><h3>Balance</h3><div class="value" id="balance">—</div></div>
        <div class="card"><h3>Win Rate</h3><div class="value" id="winrate">—</div></div>
    </div>
    <div class="card"><h3>Logs temps réel</h3><div id="logs"></div></div>
    <script>
        const ws = new WebSocket(`ws://${location.host}/ws`);
        const logs = document.getElementById('logs');
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'status') {
                document.getElementById('state').textContent = data.state || '—';
                document.getElementById('regime').textContent = data.regime || '—';
                document.getElementById('pnl').textContent = (data.today_pnl ? data.today_pnl.toFixed(2) : '—') + ' %';
                document.getElementById('pnl').className = 'value ' + (data.today_pnl > 0 ? 'positive' : data.today_pnl < 0 ? 'negative' : '');
                document.getElementById('positions').textContent = data.open_positions ?? '—';
                document.getElementById('sharpe').textContent = data.sharpe ?? '—';
                document.getElementById('maxdd').textContent = (data.max_drawdown ? data.max_drawdown.toFixed(1) : '—') + ' %';
                document.getElementById('balance').textContent = (data.balance ? data.balance.toFixed(2) : '—');
                document.getElementById('winrate').textContent = (data.win_rate ? data.win_rate.toFixed(0) : '—') + ' %';
                const dot = document.querySelector('.status-dot');
                dot.className = 'status-dot ' + (data.state === 'running' ? 'running' : 'stopped');
                document.getElementById('status').innerHTML = `<span class="status-dot ${data.state === 'running' ? 'running' : 'stopped'}"></span>${data.state ? data.state.toUpperCase() : '?'}`;
            } else if (data.type === 'log') {
                const line = document.createElement('div');
                line.className = 'log-line';
                line.textContent = `[${data.level}] ${data.message}`;
                logs.insertBefore(line, logs.firstChild);
                if (logs.children.length > 100) logs.removeChild(logs.lastChild);
            }
        };
    </script>
</body>
</html>
"""


class WebDashboard:
    """
    Dashboard web temps réel. Lance comme thread séparé.
    """

    def __init__(self, engine, host="0.0.0.0", port=8080):
        self.engine = engine
        self.host = host
        self.port = port
        self.app: Optional[FastAPI] = None
        self._clients: Set[WebSocket] = set()
        self._running = False

        if not FASTAPI_AVAILABLE:
            print("[WEB] FastAPI non installé — dashboard web désactivé")
            print("[WEB] pip install fastapi uvicorn")
            return

        self.app = FastAPI(title="SafeTrendBot V5 API")
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"], allow_credentials=True,
            allow_methods=["*"], allow_headers=["*"],
        )
        self._setup_routes()
        self._setup_engine_hooks()

    def _setup_routes(self):
        @self.app.get("/")
        async def root():
            return HTMLResponse(content=HTML_DASHBOARD)

        @self.app.get("/api/status")
        async def api_status():
            return self._get_status_dict()

        @self.app.get("/api/positions")
        async def api_positions():
            return {"positions": []}  # À enrichir

        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            self._clients.add(websocket)
            try:
                while True:
                    await websocket.receive_text()
            except WebSocketDisconnect:
                self._clients.discard(websocket)

    def _setup_engine_hooks(self):
        self.engine.status_changed.connect(self._broadcast_status)
        self.engine.log_message.connect(self._broadcast_log)
        if hasattr(self.engine, 'regime_changed'):
            self.engine.regime_changed.connect(self._broadcast_regime)
        if hasattr(self.engine, 'performance_updated'):
            self.engine.performance_updated.connect(self._broadcast_perf)

    def _get_status_dict(self) -> Dict:
        status = self.engine.get_status()
        return {
            'type': 'status',
            'state': status.state.value,
            'regime': getattr(status, 'current_regime', 'unknown'),
            'today_pnl': status.today_pnl,
            'open_positions': status.open_positions,
            'sharpe': getattr(status, 'sharpe', 0),
            'max_drawdown': getattr(status, 'max_drawdown', 0),
            'balance': getattr(status, 'today_start_balance', 0),
            'win_rate': getattr(status, 'win_rate', 0),
        }

    def _broadcast_status(self, status):
        data = self._get_status_dict()
        asyncio.create_task(self._send_to_all(data))

    def _broadcast_log(self, level, message):
        data = {'type': 'log', 'level': level, 'message': message,
                'time': datetime.now().isoformat()}
        asyncio.create_task(self._send_to_all(data))

    def _broadcast_regime(self, regime, confidence, reasons):
        data = {'type': 'regime', 'regime': regime, 'confidence': confidence,
                'reason': reasons[0] if reasons else ''}
        asyncio.create_task(self._send_to_all(data))

    def _broadcast_perf(self, perf):
        data = {'type': 'performance', 'win_rate': perf.win_rate, 'sharpe': perf.sharpe,
                'profit_factor': perf.profit_factor, 'expectancy': perf.expectancy}
        asyncio.create_task(self._send_to_all(data))

    async def _send_to_all(self, data):
        disconnected = set()
        for ws in self._clients:
            try:
                await ws.send_json(data)
            except Exception:
                disconnected.add(ws)
        self._clients -= disconnected

    def start(self):
        if not FASTAPI_AVAILABLE or self.app is None:
            return False
        import uvicorn
        self._running = True
        # Lancer dans un thread séparé
        import threading
        def run_server():
            uvicorn.run(self.app, host=self.host, port=self.port, log_level="warning")
        self._thread = threading.Thread(target=run_server, daemon=True)
        self._thread.start()
        print(f"[WEB] Dashboard lancé sur http://{self.host}:{self.port}")
        return True
