"""Run the bot: standalone loop mode (no FastAPI).

Usage:
  python run_bot.py [--once] [--symbol EURUSD] [--loop 60]
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'server'))

from config import Config
from mt5_gateway import MT5Gateway
from ai.agent import AIAgent
from ai.chart_renderer import ChartRenderer
from risk_guard import RiskGuard
from trade_manager import TradeManager
from engine import BotEngine
from notifier import TelegramNotifier
from logger_setup import setup_logger


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', default='config.yaml')
    ap.add_argument('--once', action='store_true', help='single scan then exit')
    ap.add_argument('--symbol', default=None)
    ap.add_argument('--loop', type=int, default=60, help='loop interval seconds')
    args = ap.parse_args()

    setup_logger('engine')
    cfg = Config(args.config)
    gw = MT5Gateway(cfg)
    if not gw.connect():
        print("FATAL: cannot connect to MT5")
        sys.exit(1)

    renderer = ChartRenderer(
        width=cfg.get(['provider', 'vision', 'chart_width'], 1400),
        height=cfg.get(['provider', 'vision', 'chart_height'], 800),
        overlay=cfg.get(['provider', 'vision', 'indicators_overlay'], True),
        session_id=f"MT5AI-{cfg.magic_number()}",
    )
    ai = AIAgent(cfg)
    risk = RiskGuard(cfg, gw)
    tm = TradeManager(cfg, gw)
    notifier = TelegramNotifier(cfg)
    eng = BotEngine(cfg, gw, ai, risk, tm, chart_renderer=None, notifier=notifier)

    # wire the AI's vision renderer to fetch data from MT5 on demand
    def render_for_ai(symbol, tf, n):
        d = gw.fetch_ohlcv(symbol, tf, n)
        if not d:
            return None
        return renderer.render(symbol, tf, d)

    ai.chart_renderer = render_for_ai

    try:
        if args.once:
            results = eng.run_once(symbol=args.symbol)
            import json
            print(json.dumps(results, indent=2, default=str))
        else:
            eng.run(loop_interval_sec=args.loop)
    except KeyboardInterrupt:
        print("\n[main] stopping...")
    finally:
        eng.stop()
        gw.shutdown()


if __name__ == '__main__':
    main()
