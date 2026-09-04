"""Test Telegram command response — tanpa scan AI.

Menjalankan engine dengan scan AI dimatikan (interval sangat besar),
hanya polling Telegram. Bot trading TIDAK melakukan order apapun.
Untuk memverifikasi: klik tombol di Telegram → harus respons <2 detik.
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'server'))

from config import Config
from mt5_gateway import MT5Gateway
from ai.agent import AIAgent
from risk_guard import RiskGuard
from trade_manager import TradeManager
from engine import BotEngine
from notifier import TelegramNotifier
from logger_setup import setup_logger


def main():
    setup_logger('engine')
    cfg = Config('config.yaml')
    gw = MT5Gateway(cfg)
    if not gw.connect():
        print("FATAL: cannot connect to MT5")
        sys.exit(1)

    ai = AIAgent(cfg)
    risk = RiskGuard(cfg, gw)
    tm = TradeManager(cfg, gw)
    notifier = TelegramNotifier(cfg)
    eng = BotEngine(cfg, gw, ai, risk, tm, chart_renderer=None, notifier=notifier)

    try:
        # scan interval sangat besar → tidak akan pernah AI scan (hanya command)
        eng._last_scan = time.time()  # reset
        print("[test] starting engine with scan DISABLED (interval 86400s)")
        print("[test] klik tombol di Telegram — respon harus <2 detik")
        eng.run(loop_interval_sec=86400)
    except KeyboardInterrupt:
        print("\n[test] stopping...")
    finally:
        eng.stop()
        gw.shutdown()


if __name__ == '__main__':
    main()
