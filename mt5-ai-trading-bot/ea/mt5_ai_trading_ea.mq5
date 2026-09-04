//+------------------------------------------------------------------+
//|                                             mt5_ai_trading_ea.mq5 |
//|  MT5 AI Trading Bot — EA Bridge (MQL5)                           |
//|  Polls the Python server via WebRequest for signals.              |
//|  Fallback: standalone mode can also parse local file.             |
//+------------------------------------------------------------------+
#property copyright "MT5 AI Bot"
#property version   "1.00"
#property link      ""
#property description "AI Trading EA — connects to Python server via WebRequest"
#property description "Server: http://localhost:8790"

#include <Trade/Trade.mqh>
#include <Trade/PositionInfo.mqh>
#include <Trade/OrderInfo.mqh>
#include <Trade/SymbolInfo.mqh>
#include <Trade/AccountInfo.mqh>

//+------------------------------------------------------------------+
//| Input parameters                                                  |
//+------------------------------------------------------------------+
input bool     InpUseServer        = true;      // Use Python server (WebRequest)
input string   InpServerUrl        = "http://127.0.0.1:8790";  // Server URL
input string   InpApiKey           = "";        // Server API key (X-API-Key)
input int      InpPollInterval     = 60;        // Poll interval (seconds)
input double   InpFixedLot         = 0.01;      // Fixed lot (if no risk from server)
input int      InpMagicNumber      = 20250903;  // Magic number
input bool     InpEnalbeTrailing   = true;      // Enable trailing stop (local)
input int      InpTrailingStart    = 120;       // Trailing start (points)
input int      InpTrailingStep     = 25;        // Trailing step (points)
input bool     InpUseBreakeven     = true;      // Breakeven SL
input int      InpBEStart          = 50;        // BE trigger (points)

//+------------------------------------------------------------------+
//| Globals                                                           |
//+------------------------------------------------------------------+
CTrade         Trade;
CPositionInfo  PositionInfo;
COrderInfo     OrderInfo;
CSymbolInfo    SymbolInfo;
CAccountInfo   AccountInfo;

string         g_serverUrl;
int            g_timerId = -1;
ulong          g_magic;
bool           g_initialized = false;

//+------------------------------------------------------------------+
//| Expert initialization function                                    |
//+------------------------------------------------------------------+
int OnInit()
{
   g_magic = (InpMagicNumber > 0) ? InpMagicNumber : 20250903;
   Trade.SetExpertMagicNumber(g_magic);
   Trade.SetDeviationInPoints(20);
   g_serverUrl = InpServerUrl;

   // Check if we should use the server
   if(InpUseServer)
   {
      // Verify WebRequest is allowed — test connection
      string result = HttpGet(g_serverUrl + "/health", 3000);
      if(result == "")
      {
         Print("WARNING: Server not reachable at ", g_serverUrl);
         Print("Will keep polling. Ensure URL is whitelisted: Tools > Options > Expert Advisors");
      }
      else
      {
         Print("Server reachable: ", result);
      }
   }

   g_timerId = EventSetTimer(InpPollInterval);
   if(g_timerId == -1)
   {
      Print("ERROR: EventSetTimer failed");
      return INIT_FAILED;
   }

   g_initialized = true;
   Print("MT5 AI EA initialized. Magic: ", g_magic, " Server: ", g_serverUrl);
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                  |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(g_timerId != -1)
      EventKillTimer();
   g_initialized = false;
   Print("MT5 AI EA deinitialized");
}

//+------------------------------------------------------------------+
//| Timer function — poll server for signals                          |
//+------------------------------------------------------------------+
void OnTimer()
{
   if(!g_initialized)
      return;

   // 1. Manage existing positions (trailing/BE)
   ManagePositions();

   // 2. Poll server for new signals
   if(InpUseServer)
      PollServer();
}

//+------------------------------------------------------------------+
//| Tick function — also check for trailing on every tick if enabled  |
//+------------------------------------------------------------------+
void OnTick()
{
   if(InpEnalbeTrailing && InpTrailingStart > 0)
      ManagePositions();
}

//+------------------------------------------------------------------+
//| Poll the Python server for trading signals                       |
//+------------------------------------------------------------------+
void PollServer()
{
   string url = g_serverUrl + "/scan";
   string headers = "Content-Type: application/json\r\n";
   if(InpApiKey != "")
      headers += "X-API-Key: " + InpApiKey + "\r\n";

   // POST empty body to trigger scan
   char data[];
   char result[];
   string resultHeaders;

   ResetLastError();
   int status = WebRequest("POST", url, headers, 15000, data, result, resultHeaders);

   if(status == -1)
   {
      int err = GetLastError();
      if(err == 4014)
         Print("ERROR: URL not whitelisted. Add: ", url);
      else if(err != 4060)  // 4060 = not allowed in tester
         Print("WebRequest error: ", err);
      return;
   }

   string response = CharArrayToString(result, 0, WHOLE_ARRAY, CP_UTF8);
   Print("Server response: ", response);

   // Parse the response to see if any trades were executed
   // (we don't need to execute anything — the server does it)
   if(StringFind(response, "\"action\":\"EXECUTED\"") != -1)
      Print("Server executed a trade");
}

//+------------------------------------------------------------------+
//| Manage open positions: trailing stop + breakeven                  |
//+------------------------------------------------------------------+
void ManagePositions()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(!PositionInfo.SelectByIndex(i))
         continue;
      if(PositionInfo.Magic() != g_magic)
         continue;

      string symbol = PositionInfo.Symbol();
      ulong  ticket = PositionInfo.Ticket();
      double entry  = PositionInfo.PriceOpen();
      double curr   = PositionInfo.PriceCurrent();
      double sl     = PositionInfo.StopLoss();
      double tp     = PositionInfo.TakeProfit();
      bool   isBuy  = (PositionInfo.PositionType() == POSITION_TYPE_BUY);

      SymbolInfo.Name(symbol);
      double point  = SymbolInfo.Point();
      int    digits = (int)SymbolInfo.Digits();

      // Calculate profit in points
      double profitPts = (isBuy ? (curr - entry) : (entry - curr)) / point;

      // --- Breakeven ---
      if(InpUseBreakeven && InpBEStart > 0)
      {
         if(profitPts >= InpBEStart)
         {
            double newSl = isBuy ? (entry + InpTrailingStep * point) : (entry - InpTrailingStep * point);
            bool improves = (isBuy && (sl == 0 || newSl > sl)) ||
                            (!isBuy && (sl == 0 || newSl < sl));
            if(improves)
            {
               if(Trade.PositionModify(ticket, NormalizeDouble(newSl, digits), tp))
                  Print("BE: ", symbol, " t", ticket, " SL->", newSl);
               continue;
            }
         }
      }

      // --- Trailing Stop ---
      if(InpEnalbeTrailing && InpTrailingStart > 0)
      {
         if(profitPts >= InpTrailingStart)
         {
            double newSl;
            if(isBuy)
            {
               newSl = curr - InpTrailingStart * point;
               if(sl == 0 || newSl > sl + InpTrailingStep * point)
               {
                  if(Trade.PositionModify(ticket, NormalizeDouble(newSl, digits), tp))
                     Print("TRAIL: ", symbol, " t", ticket, " SL->", newSl);
               }
            }
            else
            {
               newSl = curr + InpTrailingStart * point;
               if(sl == 0 || newSl < sl - InpTrailingStep * point)
               {
                  if(Trade.PositionModify(ticket, NormalizeDouble(newSl, digits), tp))
                     Print("TRAIL: ", symbol, " t", ticket, " SL->", newSl);
               }
            }
         }
      }
   }
}

//+------------------------------------------------------------------+
//| HTTP GET helper                                                   |
//+------------------------------------------------------------------+
string HttpGet(string url, int timeout = 5000)
{
   char data[];
   char result[];
   string resultHeaders;

   ResetLastError();
   int status = WebRequest("GET", url, "Content-Type: application/json\r\n",
                           timeout, data, result, resultHeaders);

   if(status == -1)
   {
      int err = GetLastError();
      if(err == 4014)
         Print("ERROR: URL not whitelisted: ", url);
      return "";
   }

   if(status != 200)
   {
      Print("HTTP ", status, " from ", url);
      return "";
   }

   return CharArrayToString(result, 0, WHOLE_ARRAY, CP_UTF8);
}
//+------------------------------------------------------------------+