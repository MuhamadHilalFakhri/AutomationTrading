"""FastAPI server exposing control endpoints + optional Telegram notifier.

Endpoints (API key via X-API-Key header):
  GET  /health                 -> status
  GET  /status                 -> account summary + positions + config overview
  POST /scan                   -> run_once() full scan
  POST /scan?symbol=EURUSD     -> single symbol scan
  POST /evaluate               -> trade management pass (BE/trailing)
  GET  /positions              -> open positions
  GET  /decision/{symbol}      -> ask AI only (no execution)
  POST /stop                   -> stop the loop
"""

import json
import os
import threading

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
import uvicorn

from config import Config
from mt5_gateway import MT5Gateway
from ai.agent import AIAgent
from ai.chart_renderer import ChartRenderer
from risk_guard import RiskGuard
from trade_manager import TradeManager
from engine import BotEngine


def build_engine(cfg: Config):
    gw = MT5Gateway(cfg)
    if not gw.connect():
        raise RuntimeError("MT5 initialize failed — is the terminal running & logged in?")
    renderer = ChartRenderer(
        width=cfg.get(['provider', 'vision', 'chart_width'], 1400),
        height=cfg.get(['provider', 'vision', 'chart_height'], 800),
        overlay=cfg.get(['provider', 'vision', 'indicators_overlay'], True),
        session_id=f"MT5AI-{cfg.magic_number()}",
    )
    ai = AIAgent(cfg, chart_renderer=None)
    risk = RiskGuard(cfg, gw)
    tm = TradeManager(cfg, gw)
    eng = BotEngine(cfg, gw, ai, risk, tm, chart_renderer=None)
    return gw, ai, risk, tm, eng, renderer


def create_app(cfg: Config):
    gw, ai, risk, tm, eng, renderer = build_engine(cfg)
    app = FastAPI(title="MT5 Automation Trading", version="1.0.0")
    app.state.engine = eng
    app.state.gateway = gw
    api_key = os.environ.get(cfg.get(['server', 'api_key_env'], 'MT5AI_API_KEY'), '')

    def auth(x_api_key: str = Header(default="")):
        if api_key and x_api_key != api_key:
            raise HTTPException(status_code=401, detail="invalid API key")

    @app.get("/health")
    def health():
        return {"status": "ok", "mt5": gw.connected,
                "account": gw.account_summary().get('login') if gw.connected else None}

    @app.get("/status")
    def status():
        acct = gw.account_summary()
        poss = gw.open_positions()
        pends = gw.pending_orders()
        return {"account": acct, "positions": poss, "pending_orders": pends,
                "symbols": eng._symbols[:20]}

    @app.post("/scan")
    def scan(symbol: str = None, x_api_key: str = Header(default="")):
        auth(x_api_key)
        if not gw.connected:
            return JSONResponse({"error": "MT5 not connected"}, status_code=503)
        results = eng.run_once(symbol=symbol)
        return {"results": results}

    @app.post("/evaluate")
    def evaluate(x_api_key: str = Header(default="")):
        auth(x_api_key)
        tm.manage()
        return {"ok": True}

    @app.get("/positions")
    def positions(x_api_key: str = Header(default="")):
        auth(x_api_key)
        return {"positions": gw.open_positions(), "pending": gw.pending_orders()}

    @app.get("/decision/{symbol}")
    def decision(symbol: str, x_api_key: str = Header(default="")):
        auth(x_api_key)
        tf = cfg.strategy_timeframes()
        ohlcv = {}
        for t in tf:
            d = gw.fetch_ohlcv(symbol, t, cfg.chart_candles())
            if d:
                ohlcv[t] = d
        extra = {"server_time": gw.server_time_str(),
                 "balance": 0, "equity": 0, "currency": "USD",
                 "open_positions": gw.open_positions(symbol)}
        decision_data = ai.decide(symbol, tf, ohlcv, [], extra)
        return {"decision": decision_data}

    return app


def main():
    cfg_path = os.environ.get("MT5AI_CONFIG", "config.yaml")
    cfg = Config(cfg_path)
    app = create_app(cfg)
    host = cfg.get(['server', 'host'], '127.0.0.1')
    port = int(cfg.get(['server', 'port'], 8790))
    print(f"[server] http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
