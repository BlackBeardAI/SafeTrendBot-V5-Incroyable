//+------------------------------------------------------------------+
//|                                                 SafeTrendBot.mq5 |
//|                     Bot de trading conservateur - Usage éducatif |
//|                                                                   |
//|  AVERTISSEMENT : Ce bot est fourni à des fins éducatives.         |
//|  Le trading comporte des risques de perte en capital.             |
//|  Testez TOUJOURS sur compte démo avant toute utilisation réelle.  |
//+------------------------------------------------------------------+
#property copyright "Educational use only"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\SymbolInfo.mqh>

//--- Paramètres d'entrée (modifiables dans MT5)
input group "=== Gestion du risque ==="
input double   RiskPercent        = 1.0;      // Risque par trade en % du capital (max recommandé: 2%)
input double   RiskRewardRatio    = 2.0;      // Ratio Risk/Reward (TP = SL * ce ratio)
input int      ATR_Period         = 14;       // Période ATR pour calcul des stops
input double   ATR_Multiplier     = 2.0;      // Multiplicateur ATR pour le stop loss
input int      MaxConsecutiveLoss = 3;        // Arrêt du bot après N pertes consécutives
input double   MaxDailyLossPercent = 3.0;     // Perte journalière max en % (arrêt du jour)

input group "=== Stratégie : Croisement EMA + RSI ==="
input int      FastEMA_Period     = 50;       // EMA rapide
input int      SlowEMA_Period     = 200;      // EMA lente (filtre de tendance)
input int      RSI_Period         = 14;       // Période RSI
input double   RSI_OverBought     = 70.0;     // Seuil RSI sur-acheté
input double   RSI_OverSold       = 30.0;     // Seuil RSI sur-vendu

input group "=== Filtres de trading ==="
input int      StartHour          = 8;        // Heure de début (serveur) - Session Londres
input int      EndHour            = 20;       // Heure de fin (serveur) - Fin session US
input bool     TradeOnFriday      = false;    // Trader le vendredi ?
input int      MinBarsBetweenTrades = 10;     // Nombre min de bougies entre 2 trades

input group "=== Identification ==="
input ulong    MagicNumber        = 20260416; // Numéro magique du bot
input string   TradeComment       = "SafeTrendBot";

//--- Variables globales
CTrade        trade;
CPositionInfo positionInfo;
CSymbolInfo   symbolInfo;

int    handleFastEMA;
int    handleSlowEMA;
int    handleRSI;
int    handleATR;

int    consecutiveLosses = 0;
double dailyStartBalance = 0;
datetime currentDay = 0;
datetime lastTradeTime = 0;
bool   tradingHaltedToday = false;

//+------------------------------------------------------------------+
//| Initialisation de l'Expert                                        |
//+------------------------------------------------------------------+
int OnInit()
{
   //--- Configuration du trade
   trade.SetExpertMagicNumber(MagicNumber);
   trade.SetMarginMode();
   trade.SetTypeFillingBySymbol(_Symbol);
   trade.SetDeviationInPoints(10);
   
   //--- Initialisation du symbole
   if(!symbolInfo.Name(_Symbol))
   {
      Print("Erreur: impossible d'initialiser le symbole");
      return(INIT_FAILED);
   }
   
   //--- Création des indicateurs
   handleFastEMA = iMA(_Symbol, PERIOD_CURRENT, FastEMA_Period, 0, MODE_EMA, PRICE_CLOSE);
   handleSlowEMA = iMA(_Symbol, PERIOD_CURRENT, SlowEMA_Period, 0, MODE_EMA, PRICE_CLOSE);
   handleRSI     = iRSI(_Symbol, PERIOD_CURRENT, RSI_Period, PRICE_CLOSE);
   handleATR     = iATR(_Symbol, PERIOD_CURRENT, ATR_Period);
   
   if(handleFastEMA == INVALID_HANDLE || handleSlowEMA == INVALID_HANDLE ||
      handleRSI == INVALID_HANDLE || handleATR == INVALID_HANDLE)
   {
      Print("Erreur lors de la création des indicateurs");
      return(INIT_FAILED);
   }
   
   //--- Vérification des paramètres
   if(RiskPercent <= 0 || RiskPercent > 5)
   {
      Print("ATTENTION: RiskPercent doit être entre 0.1 et 5 (recommandé: 1-2)");
      return(INIT_PARAMETERS_INCORRECT);
   }
   
   dailyStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   currentDay = iTime(_Symbol, PERIOD_D1, 0);
   
   Print("=== SafeTrendBot initialisé ===");
   Print("Capital initial: ", dailyStartBalance, " ", AccountInfoString(ACCOUNT_CURRENCY));
   Print("Risque par trade: ", RiskPercent, "%");
   Print("Ratio R:R: 1:", RiskRewardRatio);
   Print("Rappel: TOUJOURS tester sur compte démo d'abord !");
   
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Désinitialisation                                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   IndicatorRelease(handleFastEMA);
   IndicatorRelease(handleSlowEMA);
   IndicatorRelease(handleRSI);
   IndicatorRelease(handleATR);
   Print("SafeTrendBot arrêté. Raison: ", reason);
}

//+------------------------------------------------------------------+
//| Fonction principale - appelée à chaque tick                       |
//+------------------------------------------------------------------+
void OnTick()
{
   //--- Vérifier nouveau jour (reset des compteurs journaliers)
   CheckNewDay();
   
   //--- Vérifications de sécurité
   if(!IsSafeToTrade()) return;
   
   //--- Ne travailler qu'à l'ouverture d'une nouvelle bougie
   if(!IsNewBar()) return;
   
   //--- Si une position est déjà ouverte, ne rien faire de nouveau
   if(HasOpenPosition()) return;
   
   //--- Vérifier le délai minimum entre trades
   if(TimeCurrent() - lastTradeTime < MinBarsBetweenTrades * PeriodSeconds()) return;
   
   //--- Analyser les signaux
   int signal = AnalyzeSignal();
   
   if(signal == 1)       OpenBuyPosition();
   else if(signal == -1) OpenSellPosition();
}

//+------------------------------------------------------------------+
//| Vérifier si nouvelle bougie                                       |
//+------------------------------------------------------------------+
bool IsNewBar()
{
   static datetime lastBarTime = 0;
   datetime currentBarTime = iTime(_Symbol, PERIOD_CURRENT, 0);
   if(currentBarTime != lastBarTime)
   {
      lastBarTime = currentBarTime;
      return true;
   }
   return false;
}

//+------------------------------------------------------------------+
//| Vérifier nouveau jour et reset des compteurs                      |
//+------------------------------------------------------------------+
void CheckNewDay()
{
   datetime today = iTime(_Symbol, PERIOD_D1, 0);
   if(today != currentDay)
   {
      currentDay = today;
      dailyStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
      tradingHaltedToday = false;
      Print("Nouveau jour - Capital: ", dailyStartBalance);
   }
}

//+------------------------------------------------------------------+
//| Vérifications de sécurité avant de trader                         |
//+------------------------------------------------------------------+
bool IsSafeToTrade()
{
   //--- Trading autorisé ?
   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED)) return false;
   if(!MQLInfoInteger(MQL_TRADE_ALLOWED)) return false;
   if(!AccountInfoInteger(ACCOUNT_TRADE_ALLOWED)) return false;
   if(!AccountInfoInteger(ACCOUNT_TRADE_EXPERT)) return false;
   
   //--- Arrêt suite à pertes consécutives
   if(consecutiveLosses >= MaxConsecutiveLoss)
   {
      static bool warned = false;
      if(!warned)
      {
         Print("ARRÊT: ", MaxConsecutiveLoss, " pertes consécutives atteintes. Intervention manuelle requise.");
         warned = true;
      }
      return false;
   }
   
   //--- Arrêt si perte journalière dépassée
   if(tradingHaltedToday) return false;
   double currentBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   double dailyLossPercent = (dailyStartBalance - currentBalance) / dailyStartBalance * 100.0;
   if(dailyLossPercent >= MaxDailyLossPercent)
   {
      Print("ARRÊT: perte journalière max atteinte (", dailyLossPercent, "%). Reprise demain.");
      tradingHaltedToday = true;
      return false;
   }
   
   //--- Filtre horaire
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   if(dt.hour < StartHour || dt.hour >= EndHour) return false;
   
   //--- Filtre jour de la semaine (pas de weekend, optionnellement pas le vendredi)
   if(dt.day_of_week == 0 || dt.day_of_week == 6) return false;
   if(!TradeOnFriday && dt.day_of_week == 5) return false;
   
   //--- Spread raisonnable
   symbolInfo.RefreshRates();
   double spread = (symbolInfo.Ask() - symbolInfo.Bid()) / _Point;
   double maxSpread = 30; // points
   if(spread > maxSpread)
   {
      return false; // spread trop élevé (actualités, ouverture...)
   }
   
   return true;
}

//+------------------------------------------------------------------+
//| Analyser les signaux de trading                                   |
//| Retourne: 1 = achat, -1 = vente, 0 = pas de signal                |
//+------------------------------------------------------------------+
int AnalyzeSignal()
{
   double fastEMA[3], slowEMA[3], rsi[2];
   
   if(CopyBuffer(handleFastEMA, 0, 0, 3, fastEMA) < 3) return 0;
   if(CopyBuffer(handleSlowEMA, 0, 0, 3, slowEMA) < 3) return 0;
   if(CopyBuffer(handleRSI, 0, 0, 2, rsi) < 2) return 0;
   
   //--- Signal d'achat : 
   //    1. EMA rapide croise au-dessus EMA lente (tendance haussière)
   //    2. RSI n'est pas sur-acheté (évite d'acheter un sommet)
   //    3. Prix au-dessus de l'EMA lente (confirmation tendance)
   double currentPrice = symbolInfo.Bid();
   
   bool bullishCross = (fastEMA[1] <= slowEMA[1]) && (fastEMA[0] > slowEMA[0]);
   bool bullishTrend = currentPrice > slowEMA[0];
   bool rsiOkBuy     = rsi[0] < RSI_OverBought && rsi[0] > 40;
   
   if(bullishCross && bullishTrend && rsiOkBuy)
   {
      Print("Signal ACHAT détecté - RSI: ", rsi[0]);
      return 1;
   }
   
   //--- Signal de vente :
   //    1. EMA rapide croise en-dessous EMA lente (tendance baissière)
   //    2. RSI n'est pas sur-vendu (évite de vendre un creux)
   //    3. Prix en-dessous de l'EMA lente
   bool bearishCross = (fastEMA[1] >= slowEMA[1]) && (fastEMA[0] < slowEMA[0]);
   bool bearishTrend = currentPrice < slowEMA[0];
   bool rsiOkSell    = rsi[0] > RSI_OverSold && rsi[0] < 60;
   
   if(bearishCross && bearishTrend && rsiOkSell)
   {
      Print("Signal VENTE détecté - RSI: ", rsi[0]);
      return -1;
   }
   
   return 0;
}

//+------------------------------------------------------------------+
//| Vérifier s'il y a une position ouverte par ce bot                 |
//+------------------------------------------------------------------+
bool HasOpenPosition()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(positionInfo.SelectByIndex(i))
      {
         if(positionInfo.Symbol() == _Symbol && positionInfo.Magic() == MagicNumber)
            return true;
      }
   }
   return false;
}

//+------------------------------------------------------------------+
//| Calculer la taille de position selon le risque                    |
//+------------------------------------------------------------------+
double CalculateLotSize(double stopLossPoints)
{
   double accountBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   double riskAmount     = accountBalance * RiskPercent / 100.0;
   
   double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double point     = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   
   if(tickValue == 0 || tickSize == 0 || point == 0 || stopLossPoints == 0) return 0;
   
   double valuePerPoint = tickValue * (point / tickSize);
   double lotSize = riskAmount / (stopLossPoints * valuePerPoint);
   
   //--- Normaliser selon les contraintes du broker
   double minLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double lotStep = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   
   lotSize = MathFloor(lotSize / lotStep) * lotStep;
   lotSize = MathMax(minLot, MathMin(maxLot, lotSize));
   
   return NormalizeDouble(lotSize, 2);
}

//+------------------------------------------------------------------+
//| Ouvrir une position d'achat                                       |
//+------------------------------------------------------------------+
void OpenBuyPosition()
{
   double atr[1];
   if(CopyBuffer(handleATR, 0, 0, 1, atr) < 1) return;
   
   symbolInfo.RefreshRates();
   double ask = symbolInfo.Ask();
   double stopDistance = atr[0] * ATR_Multiplier;
   double stopLossPoints = stopDistance / _Point;
   
   double sl = NormalizeDouble(ask - stopDistance, _Digits);
   double tp = NormalizeDouble(ask + stopDistance * RiskRewardRatio, _Digits);
   
   double lotSize = CalculateLotSize(stopLossPoints);
   if(lotSize <= 0)
   {
      Print("Erreur: taille de lot invalide");
      return;
   }
   
   if(trade.Buy(lotSize, _Symbol, ask, sl, tp, TradeComment))
   {
      lastTradeTime = TimeCurrent();
      Print("ACHAT ouvert: ", lotSize, " lots @ ", ask, " SL:", sl, " TP:", tp);
   }
   else
   {
      Print("Échec ouverture achat: ", trade.ResultRetcodeDescription());
   }
}

//+------------------------------------------------------------------+
//| Ouvrir une position de vente                                      |
//+------------------------------------------------------------------+
void OpenSellPosition()
{
   double atr[1];
   if(CopyBuffer(handleATR, 0, 0, 1, atr) < 1) return;
   
   symbolInfo.RefreshRates();
   double bid = symbolInfo.Bid();
   double stopDistance = atr[0] * ATR_Multiplier;
   double stopLossPoints = stopDistance / _Point;
   
   double sl = NormalizeDouble(bid + stopDistance, _Digits);
   double tp = NormalizeDouble(bid - stopDistance * RiskRewardRatio, _Digits);
   
   double lotSize = CalculateLotSize(stopLossPoints);
   if(lotSize <= 0)
   {
      Print("Erreur: taille de lot invalide");
      return;
   }
   
   if(trade.Sell(lotSize, _Symbol, bid, sl, tp, TradeComment))
   {
      lastTradeTime = TimeCurrent();
      Print("VENTE ouverte: ", lotSize, " lots @ ", bid, " SL:", sl, " TP:", tp);
   }
   else
   {
      Print("Échec ouverture vente: ", trade.ResultRetcodeDescription());
   }
}

//+------------------------------------------------------------------+
//| Événement de trade - suivi des résultats                          |
//+------------------------------------------------------------------+
void OnTradeTransaction(const MqlTradeTransaction& trans,
                        const MqlTradeRequest& request,
                        const MqlTradeResult& result)
{
   //--- Suivre les fermetures de position pour compter les pertes consécutives
   if(trans.type == TRADE_TRANSACTION_DEAL_ADD)
   {
      if(HistoryDealSelect(trans.deal))
      {
         long magic = HistoryDealGetInteger(trans.deal, DEAL_MAGIC);
         long entry = HistoryDealGetInteger(trans.deal, DEAL_ENTRY);
         
         if(magic == MagicNumber && entry == DEAL_ENTRY_OUT)
         {
            double profit = HistoryDealGetDouble(trans.deal, DEAL_PROFIT)
                          + HistoryDealGetDouble(trans.deal, DEAL_SWAP)
                          + HistoryDealGetDouble(trans.deal, DEAL_COMMISSION);
            
            if(profit < 0)
            {
               consecutiveLosses++;
               Print("Trade perdant. Pertes consécutives: ", consecutiveLosses);
            }
            else if(profit > 0)
            {
               if(consecutiveLosses > 0)
                  Print("Trade gagnant - reset du compteur de pertes");
               consecutiveLosses = 0;
            }
         }
      }
   }
}
//+------------------------------------------------------------------+
