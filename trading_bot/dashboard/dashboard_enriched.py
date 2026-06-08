"""
Dashboard SafeTrendBot - Version enrichie
Inclut : surveillance bot + calendrier économique + actualités RSS + alertes Telegram

Lancement :
    streamlit run dashboard_enriched.py
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta, timezone
import sys
import os

# Import des modules locaux
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bot'))

try:
    from mt5_bridge import MT5Bridge, FileBridge, MT5_AVAILABLE
except ImportError:
    MT5_AVAILABLE = False

try:
    from economic_calendar import EconomicCalendar
    CALENDAR_AVAILABLE = True
except ImportError:
    CALENDAR_AVAILABLE = False

try:
    from news_feed import NewsFeed
    NEWS_AVAILABLE = True
except ImportError:
    NEWS_AVAILABLE = False

try:
    from telegram_alerts import AlertSystem
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False


# ============================================================================
# CONFIGURATION DE LA PAGE
# ============================================================================

st.set_page_config(
    page_title="SafeTrendBot Dashboard Pro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header { font-size: 2.2rem; font-weight: 700; color: #1f4e79; margin-bottom: 0.5rem; }
    .subheader { color: #6c757d; font-size: 0.9rem; margin-bottom: 2rem; }
    .news-card { background-color: #f8f9fa; padding: 0.8rem; border-left: 3px solid #1f4e79;
                 border-radius: 4px; margin-bottom: 0.5rem; }
    .high-impact { border-left-color: #dc3545 !important; background-color: #fff3f4; }
    .medium-impact { border-left-color: #ffc107 !important; }
</style>
""", unsafe_allow_html=True)


# ============================================================================
# ÉTAT DE LA SESSION
# ============================================================================

for key in ['bridge', 'connected', 'connection_mode', 'calendar_cache', 'news_cache']:
    if key not in st.session_state:
        st.session_state[key] = None


# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    st.markdown("### ⚙️ Configuration")

    connection_mode = st.radio(
        "Mode de connexion",
        ['Direct MT5 (Windows)', 'Fichier JSON (Linux/VPS)', 'Démo (sans MT5)'],
        help="Le mode Démo permet de voir les autres sections sans MT5."
    )

    if connection_mode == 'Direct MT5 (Windows)':
        st.session_state.connection_mode = 'direct'
        magic = st.number_input("Magic number", value=20260416)
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
                        st.error("Échec connexion")
                else:
                    st.error("MetaTrader5 non installé")
        with col2:
            if st.button("⏹️ Arrêter", use_container_width=True):
                if st.session_state.bridge:
                    st.session_state.bridge.disconnect()
                st.session_state.connected = False

    elif connection_mode == 'Fichier JSON (Linux/VPS)':
        st.session_state.connection_mode = 'file'
        st.session_state.json_path = st.text_input(
            "Chemin JSON", value="/tmp/mt5_snapshot.json"
        )
    else:
        st.session_state.connection_mode = 'demo'

    st.markdown("---")

    # Test Telegram
    st.markdown("### 📱 Alertes Telegram")
    if TELEGRAM_AVAILABLE:
        alerts = AlertSystem()
        if alerts.enabled:
            st.success("Configuré ✓")
            if st.button("Test d'envoi", use_container_width=True):
                if alerts.test():
                    st.success("Message envoyé !")
                else:
                    st.error("Échec")
        else:
            st.warning("Non configuré")
            with st.expander("Comment configurer"):
                st.code("""# Créer un fichier .env à la racine :
TELEGRAM_TOKEN=123:ABC...
TELEGRAM_CHAT_ID=123456

# Étapes :
# 1. Parler à @BotFather sur Telegram
# 2. /newbot → récupérer le TOKEN
# 3. Parler à @userinfobot → récupérer CHAT_ID""")

    st.markdown("---")
    st.markdown("### 🔄 Actualisation")
    if st.button("Actualiser tout", use_container_width=True, type="primary"):
        st.session_state.calendar_cache = None
        st.session_state.news_cache = None
        st.rerun()


# ============================================================================
# HEADER
# ============================================================================

st.markdown('<div class="main-header">📊 SafeTrendBot Dashboard Pro</div>',
            unsafe_allow_html=True)
st.markdown(
    '<div class="subheader">Surveillance du bot · Calendrier économique · Actualités · Alertes</div>',
    unsafe_allow_html=True
)


# ============================================================================
# ONGLETS PRINCIPAUX
# ============================================================================

tab_bot, tab_calendar, tab_news, tab_help = st.tabs([
    "🤖 Bot", "📅 Calendrier éco", "📰 Actualités", "❓ Aide"
])


# ============================================================================
# ONGLET 1 : BOT
# ============================================================================

def get_snapshot():
    mode = st.session_state.get('connection_mode')
    if mode == 'direct' and st.session_state.bridge and st.session_state.connected:
        return st.session_state.bridge.to_dict()
    elif mode == 'file':
        bridge = FileBridge(st.session_state.get('json_path', '/tmp/mt5_snapshot.json'))
        return bridge.read_snapshot()
    return None


with tab_bot:
    snapshot = get_snapshot()

    if snapshot is None:
        st.info("ℹ️ Connectez-vous depuis la sidebar pour voir l'état du bot. "
                "Les autres onglets restent accessibles en mode démo.")
    else:
        account = snapshot.get('account')
        stats = snapshot.get('stats', {})
        positions = snapshot.get('positions', [])
        history = snapshot.get('history', [])

        if account:
            st.markdown("### 💰 Compte")
            cols = st.columns(5)
            with cols[0]:
                st.metric("Balance", f"{account['balance']:,.2f} {account['currency']}")
            with cols[1]:
                delta = account['equity'] - account['balance']
                st.metric("Équité", f"{account['equity']:,.2f}",
                         delta=f"{delta:+,.2f}" if delta != 0 else None)
            with cols[2]:
                st.metric("Profit", f"{account['profit']:,.2f}")
            with cols[3]:
                st.metric("Marge libre", f"{account['free_margin']:,.2f}")
            with cols[4]:
                st.metric("Levier", f"1:{account['leverage']}")

        st.markdown("### 📈 Performance (30j)")
        cols = st.columns(4)
        cols[0].metric("Trades", stats.get('total_trades', 0))
        cols[1].metric("Win rate", f"{stats.get('win_rate', 0):.1f}%")
        pf = stats.get('profit_factor', 0)
        cols[2].metric("Profit factor", f"{pf:.2f}" if pf != float('inf') else "∞")
        cols[3].metric("P&L", f"{stats.get('total_profit', 0):+,.2f}")

        st.markdown("### 🔓 Positions ouvertes")
        if positions:
            df = pd.DataFrame(positions)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("Aucune position ouverte")

        if history:
            st.markdown("### 📉 Historique")
            df_h = pd.DataFrame(history)
            df_h['time'] = pd.to_datetime(df_h['time'])
            df_h = df_h.sort_values('time')
            df_h['cum_profit'] = df_h['profit'].cumsum()

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_h['time'], y=df_h['cum_profit'],
                mode='lines', line=dict(color='#1f4e79', width=2),
                fill='tozeroy', fillcolor='rgba(31, 78, 121, 0.1)'
            ))
            fig.update_layout(
                title="Profit cumulé",
                height=350, margin=dict(l=10, r=10, t=40, b=10)
            )
            st.plotly_chart(fig, use_container_width=True)


# ============================================================================
# ONGLET 2 : CALENDRIER ÉCONOMIQUE
# ============================================================================

with tab_calendar:
    st.markdown("### 📅 Calendrier économique — Événements à fort impact")
    st.caption("Source : ForexFactory (flux RSS public). Le bot s'abstient de trader "
               "±30 min autour des événements High.")

    if not CALENDAR_AVAILABLE:
        st.error("Module economic_calendar introuvable")
    else:
        # Cache simple en session
        if st.session_state.calendar_cache is None:
            with st.spinner("Chargement du calendrier..."):
                try:
                    cal = EconomicCalendar()
                    events = cal.get_upcoming_high_impact(hours_ahead=7 * 24)
                    st.session_state.calendar_cache = events
                except Exception as e:
                    st.error(f"Erreur : {e}")
                    events = []
        else:
            events = st.session_state.calendar_cache

        if not events:
            st.warning("Aucun événement récupéré. Vérifiez votre connexion.")
        else:
            # Vérification pour l'instant présent
            st.markdown("#### 🚦 Statut actuel")
            cal = EconomicCalendar()
            symbols_to_check = ['EURUSD', 'GBPUSD', 'USDJPY']
            cols = st.columns(len(symbols_to_check))
            for col, sym in zip(cols, symbols_to_check):
                safe, event = cal.is_safe_to_trade(sym)
                with col:
                    if safe:
                        st.success(f"✅ {sym}\nTrading OK")
                    else:
                        st.error(f"⛔ {sym}\n{event.title[:40] if event else ''}")

            # Prochains événements
            st.markdown("#### 📋 Prochains événements à fort impact (7 jours)")

            # Filtre par devise
            countries = sorted(set(e.country for e in events))
            selected = st.multiselect(
                "Filtrer par devise", countries, default=countries[:4] if len(countries) > 4 else countries
            )
            filtered = [e for e in events if e.country in selected] if selected else events

            if filtered:
                for event in filtered[:30]:
                    time_str = event.time.strftime('%Y-%m-%d %H:%M UTC')
                    time_until = event.time - datetime.now(timezone.utc)
                    hours_until = int(time_until.total_seconds() / 3600)

                    if hours_until < 0:
                        badge = "✓ Passé"
                    elif hours_until < 1:
                        badge = "🔴 < 1h"
                    elif hours_until < 24:
                        badge = f"🟠 dans {hours_until}h"
                    else:
                        badge = f"🟡 dans {hours_until//24}j"

                    st.markdown(
                        f'<div class="news-card high-impact">'
                        f'<b>{badge}</b> · {time_str} · <b>{event.country}</b><br>'
                        f'{event.title}'
                        + (f'<br><small>Prévision : {event.forecast} | '
                           f'Précédent : {event.previous}</small>'
                           if event.forecast else '')
                        + '</div>',
                        unsafe_allow_html=True
                    )


# ============================================================================
# ONGLET 3 : ACTUALITÉS
# ============================================================================

with tab_news:
    st.markdown("### 📰 Actualités financières")
    st.caption("Flux RSS de sources légitimes (Reuters, FT, CNBC, etc.). "
               "**Pour lecture humaine uniquement** — aucun trade automatique.")

    st.warning("⚠️ **Rappel important** : les études académiques montrent que le trading "
               "basé sur le sentiment des news est **statistiquement perdant** pour les "
               "particuliers. Lisez pour vous informer, pas pour trader impulsivement.")

    if not NEWS_AVAILABLE:
        st.error("Module news_feed introuvable")
    else:
        if st.session_state.news_cache is None:
            with st.spinner("Chargement des actualités..."):
                try:
                    feed = NewsFeed()
                    articles = feed.fetch_all(max_per_source=5)
                    st.session_state.news_cache = articles
                except Exception as e:
                    st.error(f"Erreur : {e}")
                    articles = []
        else:
            articles = st.session_state.news_cache

        if not articles:
            st.info("Aucun article disponible.")
        else:
            # Filtres
            col1, col2 = st.columns([2, 1])
            with col1:
                keywords = st.text_input(
                    "🔍 Filtrer par mots-clés (séparés par virgules)",
                    placeholder="ex: Fed, inflation, EUR"
                )
            with col2:
                sources = sorted(set(a.source for a in articles))
                selected_sources = st.multiselect(
                    "Sources", sources, default=sources
                )

            # Application des filtres
            filtered = articles
            if selected_sources:
                filtered = [a for a in filtered if a.source in selected_sources]
            if keywords:
                kw_list = [k.strip() for k in keywords.split(',')]
                feed = NewsFeed()
                filtered = feed.filter_by_keywords(filtered, kw_list)

            st.caption(f"{len(filtered)} articles affichés")

            for article in filtered[:50]:
                age = datetime.now(timezone.utc) - article.published
                if age.total_seconds() < 3600:
                    age_str = f"{int(age.total_seconds() / 60)}min"
                elif age.total_seconds() < 86400:
                    age_str = f"{int(age.total_seconds() / 3600)}h"
                else:
                    age_str = f"{age.days}j"

                st.markdown(
                    f'<div class="news-card">'
                    f'<small><b>{article.source}</b> · il y a {age_str}</small><br>'
                    f'<a href="{article.link}" target="_blank"><b>{article.title}</b></a><br>'
                    f'<small>{article.summary[:200]}...</small>'
                    f'</div>',
                    unsafe_allow_html=True
                )


# ============================================================================
# ONGLET 4 : AIDE
# ============================================================================

with tab_help:
    st.markdown("### 📖 Guide rapide")

    st.markdown("""
    #### Architecture du système

    Ce dashboard surveille 4 composants indépendants :

    1. **🤖 Bot** : l'Expert Advisor MT5 qui exécute les trades selon sa stratégie technique
    2. **📅 Calendrier éco** : le bot s'abstient automatiquement autour des news importantes
    3. **📰 Actualités** : flux RSS **pour vous**, pas pour le bot
    4. **📱 Alertes Telegram** : notifications push pour les événements critiques

    #### Ce que le bot fait vraiment
    - Analyse technique (EMA + RSI + ATR) à chaque nouvelle bougie
    - Trade uniquement si ≥4 conditions sont alignées
    - SL et TP obligatoires, ratio R:R 1:2 minimum
    - S'arrête seul en cas de dérive (pertes consécutives, drawdown journalier)
    - **Ne trade PAS** ±30 min autour des news à fort impact

    #### Ce que le bot ne fait PAS (intentionnellement)
    - ❌ Trader sur le sentiment Twitter/X
    - ❌ Suivre des signaux de groupes Telegram
    - ❌ Réagir automatiquement aux news
    - ❌ Scraper des sites sans API officielle

    Ces pratiques sont **statistiquement perdantes** pour les particuliers.
    Les études académiques (et les statistiques des brokers régulés) sont
    constantes là-dessus.

    #### Configuration des alertes Telegram

    1. Sur Telegram, chercher **@BotFather**
    2. Envoyer `/newbot` et suivre les instructions
    3. Copier le TOKEN fourni
    4. Démarrer une conversation avec votre nouveau bot (envoyer `/start`)
    5. Sur Telegram, chercher **@userinfobot**, envoyer `/start` → copier votre ID
    6. À la racine du projet, créer un fichier `.env` :
       ```
       TELEGRAM_TOKEN=123456:ABC-DEF...
       TELEGRAM_CHAT_ID=123456789
       ```

    #### Attentes réalistes

    | Paramètre | Valeur réaliste |
    |-----------|-----------------|
    | Trades / semaine | 2 à 8 |
    | Rendement annuel | 5-15% (bonne année) |
    | Drawdown à prévoir | 10-20% |
    | Mois perdants | 30-40% des mois |
    | Weekend (forex) | Marché fermé, 0 trade |

    Un bot ne rend personne riche rapidement. Le trading algorithmique est
    un **outil**, pas une machine à cash.
    """)


# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
cols = st.columns(3)
cols[0].caption(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
cols[1].caption(f"🔗 Mode : {st.session_state.get('connection_mode', 'non connecté')}")
cols[2].caption("💡 Dashboard de surveillance uniquement")
