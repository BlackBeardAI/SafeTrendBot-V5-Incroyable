"""
Dashboard de surveillance du SafeTrendBot
Fonctionne sur Windows et Linux (Debian, Ubuntu, etc.)

Lancement :
    streamlit run dashboard.py

Puis ouvrir http://localhost:8501 dans un navigateur.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import time
import sys
import os

# Ajout du chemin parent pour importer mt5_bridge
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bot'))

try:
    from mt5_bridge import MT5Bridge, FileBridge, MT5_AVAILABLE
except ImportError:
    MT5_AVAILABLE = False
    st.error("Module mt5_bridge introuvable. Vérifiez la structure du projet.")


# ============================================================================
# CONFIGURATION DE LA PAGE
# ============================================================================

st.set_page_config(
    page_title="SafeTrendBot Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Style CSS personnalisé
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1f4e79;
        margin-bottom: 0.5rem;
    }
    .subheader {
        color: #6c757d;
        font-size: 0.9rem;
        margin-bottom: 2rem;
    }
    .metric-box {
        background-color: #f8f9fa;
        border-left: 4px solid #1f4e79;
        padding: 1rem;
        border-radius: 4px;
    }
    .stAlert {
        padding: 0.75rem 1rem;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================================
# ÉTAT DE LA SESSION
# ============================================================================

if 'bridge' not in st.session_state:
    st.session_state.bridge = None
if 'connected' not in st.session_state:
    st.session_state.connected = False
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = None
if 'connection_mode' not in st.session_state:
    st.session_state.connection_mode = 'direct'


# ============================================================================
# SIDEBAR - CONFIGURATION
# ============================================================================

with st.sidebar:
    st.markdown("### ⚙️ Configuration")

    connection_mode = st.radio(
        "Mode de connexion",
        ['Direct MT5 (Windows)', 'Fichier JSON (Linux/VPS)'],
        help="Direct : MT5 est sur la même machine. Fichier : l'EA écrit un JSON partagé."
    )

    if connection_mode == 'Direct MT5 (Windows)':
        st.session_state.connection_mode = 'direct'
        magic = st.number_input("Numéro magique du bot", value=20260416)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔌 Connecter", use_container_width=True):
                if MT5_AVAILABLE:
                    bridge = MT5Bridge(magic_number=int(magic))
                    if bridge.connect():
                        st.session_state.bridge = bridge
                        st.session_state.connected = True
                        st.success("Connecté !")
                    else:
                        st.error("Échec connexion. MT5 est-il lancé ?")
                else:
                    st.error("Package MetaTrader5 non installé")
        with col2:
            if st.button("⏹️ Déconnecter", use_container_width=True):
                if st.session_state.bridge:
                    st.session_state.bridge.disconnect()
                st.session_state.connected = False
                st.info("Déconnecté")
    else:
        st.session_state.connection_mode = 'file'
        json_path = st.text_input(
            "Chemin du fichier JSON",
            value="/tmp/mt5_snapshot.json",
            help="Fichier écrit par l'EA MT5 à intervalle régulier"
        )
        st.session_state.json_path = json_path

    st.markdown("---")
    st.markdown("### 🔄 Actualisation")
    auto_refresh = st.checkbox("Actualisation auto", value=False)
    refresh_interval = st.slider("Intervalle (s)", 5, 60, 10)

    if st.button("🔄 Actualiser maintenant", use_container_width=True):
        st.rerun()

    st.markdown("---")
    st.markdown("### 📖 À propos")
    st.caption("SafeTrendBot Dashboard v1.0")
    st.caption("Outil de surveillance. Ne génère pas les trades.")


# ============================================================================
# HEADER
# ============================================================================

st.markdown('<div class="main-header">📊 SafeTrendBot Dashboard</div>', unsafe_allow_html=True)
st.markdown('<div class="subheader">Surveillance du bot de trading — Mise à jour en temps réel</div>',
            unsafe_allow_html=True)


# ============================================================================
# RÉCUPÉRATION DES DONNÉES
# ============================================================================

def get_snapshot():
    """Récupère un snapshot depuis la source active"""
    if st.session_state.connection_mode == 'direct':
        if st.session_state.bridge and st.session_state.connected:
            return st.session_state.bridge.to_dict()
        return None
    else:
        bridge = FileBridge(st.session_state.get('json_path', '/tmp/mt5_snapshot.json'))
        return bridge.read_snapshot()


snapshot = get_snapshot()

if snapshot is None:
    st.warning("⚠️ Aucune donnée disponible. Connectez-vous à MT5 depuis la sidebar, "
               "ou vérifiez le chemin du fichier JSON.")
    
    st.markdown("### 🔧 Démarrage rapide")
    tab1, tab2 = st.tabs(["Windows (direct)", "Linux / VPS"])
    
    with tab1:
        st.code("""
# 1. Installer les dépendances
pip install MetaTrader5 streamlit plotly pandas

# 2. Lancer MetaTrader 5 et s'y connecter manuellement
# 3. Activer "Allow algorithmic trading" dans MT5
# 4. Lancer le dashboard
streamlit run dashboard.py

# 5. Cliquer sur "Connecter" dans la sidebar
        """, language="bash")

    with tab2:
        st.code("""
# Option A : MT5 via Wine sur Linux
sudo apt install wine
# Télécharger MT5 depuis metatrader5.com, l'installer via wine
# Puis utiliser un JSON de synchronisation

# Option B : MT5 sur VPS Windows, dashboard sur Linux
# L'EA écrit un fichier JSON, partagé via Dropbox/rsync/NFS
# Le dashboard lit ce fichier depuis n'importe où

# Pour le dashboard seul :
pip install streamlit plotly pandas
streamlit run dashboard.py --server.address 0.0.0.0
        """, language="bash")
    
    st.stop()


# ============================================================================
# AFFICHAGE DES MÉTRIQUES PRINCIPALES
# ============================================================================

account = snapshot.get('account')
stats = snapshot.get('stats', {})
positions = snapshot.get('positions', [])
history = snapshot.get('history', [])

if account:
    st.markdown("### 💰 Compte")
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            "Balance",
            f"{account['balance']:,.2f} {account['currency']}",
        )
    with col2:
        equity_delta = account['equity'] - account['balance']
        st.metric(
            "Équité",
            f"{account['equity']:,.2f}",
            delta=f"{equity_delta:+,.2f}" if equity_delta != 0 else None
        )
    with col3:
        st.metric("Profit ouvert", f"{account['profit']:,.2f}")
    with col4:
        st.metric("Marge libre", f"{account['free_margin']:,.2f}")
    with col5:
        st.metric("Effet de levier", f"1:{account['leverage']}")

    st.caption(f"Compte : {account['name']} — Serveur : {account['server']}")


# ============================================================================
# STATISTIQUES DE PERFORMANCE
# ============================================================================

st.markdown("### 📈 Performance (30 derniers jours)")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Trades", stats.get('total_trades', 0))
with col2:
    win_rate = stats.get('win_rate', 0)
    st.metric("Win rate", f"{win_rate:.1f} %")
with col3:
    pf = stats.get('profit_factor', 0)
    pf_display = f"{pf:.2f}" if pf != float('inf') else "∞"
    st.metric("Profit factor", pf_display)
with col4:
    total = stats.get('total_profit', 0)
    st.metric("P&L total", f"{total:+,.2f}")

# Indicateurs de santé
st.markdown("#### 🎯 Indicateurs de santé")
health_cols = st.columns(4)

checks = [
    ("Win rate > 40%", win_rate > 40),
    ("Profit factor > 1.3", pf > 1.3 if pf != float('inf') else True),
    ("P&L positif", total > 0),
    ("Trades > 10", stats.get('total_trades', 0) > 10),
]

for col, (label, ok) in zip(health_cols, checks):
    with col:
        icon = "✅" if ok else "⚠️"
        st.markdown(f"{icon} {label}")


# ============================================================================
# POSITIONS OUVERTES
# ============================================================================

st.markdown("### 🔓 Positions ouvertes")
if positions:
    df_pos = pd.DataFrame(positions)
    df_pos = df_pos[['ticket', 'symbol', 'type', 'volume', 'price_open',
                     'price_current', 'sl', 'tp', 'profit', 'time']]
    df_pos.columns = ['Ticket', 'Symbole', 'Type', 'Volume', 'Prix entrée',
                      'Prix actuel', 'SL', 'TP', 'Profit', 'Heure']
    
    # Coloration selon profit/perte
    def color_profit(val):
        if isinstance(val, (int, float)):
            color = 'green' if val >= 0 else 'red'
            return f'color: {color}; font-weight: bold'
        return ''

    styled = df_pos.style.map(color_profit, subset=['Profit'])
    st.dataframe(styled, use_container_width=True, hide_index=True)
else:
    st.info("Aucune position ouverte actuellement.")


# ============================================================================
# HISTORIQUE ET COURBE D'ÉQUITÉ
# ============================================================================

if history:
    st.markdown("### 📉 Historique des trades")
    df_hist = pd.DataFrame(history)
    df_hist['time'] = pd.to_datetime(df_hist['time'])
    df_hist = df_hist.sort_values('time')

    # Courbe d'équité cumulative
    df_hist['cumulative_profit'] = df_hist['profit'].cumsum()
    if account:
        df_hist['equity'] = account['balance'] - df_hist['profit'].sum() + df_hist['cumulative_profit']
    else:
        df_hist['equity'] = df_hist['cumulative_profit']

    fig = make_subplots(
        rows=2, cols=1,
        row_heights=[0.6, 0.4],
        subplot_titles=("Courbe d'équité", "Profit par trade"),
        vertical_spacing=0.12
    )

    fig.add_trace(
        go.Scatter(
            x=df_hist['time'],
            y=df_hist['equity'],
            mode='lines',
            name='Équité',
            line=dict(color='#1f4e79', width=2),
            fill='tozeroy',
            fillcolor='rgba(31, 78, 121, 0.1)'
        ),
        row=1, col=1
    )

    colors = ['#28a745' if p >= 0 else '#dc3545' for p in df_hist['profit']]
    fig.add_trace(
        go.Bar(
            x=df_hist['time'],
            y=df_hist['profit'],
            marker_color=colors,
            name='Profit'
        ),
        row=2, col=1
    )

    fig.update_layout(
        height=600,
        showlegend=False,
        hovermode='x unified',
        margin=dict(l=10, r=10, t=40, b=10)
    )
    fig.update_xaxes(title_text="Date", row=2, col=1)
    fig.update_yaxes(title_text="Équité", row=1, col=1)
    fig.update_yaxes(title_text="Profit", row=2, col=1)

    st.plotly_chart(fig, use_container_width=True)

    # Tableau de l'historique
    with st.expander("📋 Détail de l'historique"):
        df_display = df_hist[['time', 'symbol', 'type', 'volume', 'price', 'profit', 'commission']].copy()
        df_display.columns = ['Date', 'Symbole', 'Type', 'Volume', 'Prix', 'Profit', 'Commission']
        df_display = df_display.sort_values('Date', ascending=False)
        st.dataframe(df_display, use_container_width=True, hide_index=True)


# ============================================================================
# ALERTES ET NOTIFICATIONS
# ============================================================================

st.markdown("### 🚨 Alertes")
alerts = []

if account and account['margin_level'] > 0 and account['margin_level'] < 200:
    alerts.append(('error', f"⛔ Niveau de marge faible : {account['margin_level']:.0f}% — Risque de margin call"))

if stats.get('profit_factor', 1) < 1 and stats.get('total_trades', 0) > 10:
    alerts.append(('warning', "⚠️ Profit factor < 1 sur 30 jours — La stratégie ne fonctionne pas dans les conditions actuelles"))

if account and account['equity'] < account['balance'] * 0.9:
    alerts.append(('warning', f"⚠️ Drawdown > 10% détecté"))

if not alerts:
    st.success("✅ Aucune alerte. Le bot fonctionne normalement.")
else:
    for level, msg in alerts:
        if level == 'error':
            st.error(msg)
        else:
            st.warning(msg)


# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    last_update = snapshot.get('timestamp', 'Jamais')
    if last_update != 'Jamais':
        try:
            dt = datetime.fromisoformat(last_update)
            last_update = dt.strftime('%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError):
            pass
    st.caption(f"🕐 Dernière mise à jour : {last_update}")
with col2:
    st.caption(f"🔗 Mode : {st.session_state.connection_mode}")
with col3:
    st.caption("💡 Le dashboard ne trade pas — surveillance seulement")


# Auto-refresh
if auto_refresh:
    time.sleep(refresh_interval)
    st.rerun()
