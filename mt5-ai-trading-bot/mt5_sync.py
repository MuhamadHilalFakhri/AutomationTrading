"""MT5 -> Trading Journal sync.

Pulls account info, open positions, and deal history from the MetaTrader 5
terminal and pushes them to the journal's /api/sync endpoint for
reconciliation (closes missed by webhook, manual trades, live positions).

Run alongside the bot (or standalone):
  python mt5_sync.py                 # one-shot sync
  python mt5_sync.py --loop 60       # sync every 60s
  python mt5_sync.py --days 180      # wider history window (default 90)
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timedelta

try:
    import MetaTrader5 as mt5
except ImportError:
    print("[mt5-sync] MetaTrader5 package not installed. pip install MetaTrader5", file=sys.stderr)
    sys.exit(1)

TJ_URL = os.environ.get("TJ_URL", "http://127.0.0.1:8500")
TERMINAL_PATH = os.environ.get(
    "MT5_TERMINAL_PATH",
    "C:/Program Files/MetaTrader 5/terminal64.exe",
)


def fetch(days: int) -> dict:
    if not mt5.initialize(path=TERMINAL_PATH):
        raise RuntimeError(f"mt5 initialize failed: {mt5.last_error()}")

    try:
        acc = mt5.account_info()
        if not acc:
            raise RuntimeError(f"account_info failed: {mt5.last_error()}")

        positions = []
        for p in (mt5.positions_get() or []):
            positions.append({
                "ticket": p.ticket, "symbol": p.symbol, "type": p.type,
                "volume": p.volume, "price_open": p.price_open,
                "sl": p.sl, "tp": p.tp, "profit": p.profit, "swap": p.swap,
                "time": p.time, "comment": p.comment, "magic": p.magic,
            })

        now = datetime.now()
        deals = []
        for d in (mt5.history_deals_get(now - timedelta(days=days), now + timedelta(days=1)) or []):
            deals.append({
                "ticket": d.ticket, "position_id": d.position_id, "order": d.order,
                "symbol": d.symbol, "type": d.type, "entry": d.entry,
                "volume": d.volume, "price": d.price, "profit": d.profit,
                "commission": d.commission, "swap": d.swap, "fee": d.fee,
                "time": d.time, "comment": d.comment, "magic": d.magic,
            })

        return {
            "account": {
                "login": acc.login, "server": acc.server, "currency": acc.currency,
                "balance": acc.balance, "equity": acc.equity, "margin_free": acc.margin_free,
            },
            "positions": positions,
            "deals": deals,
            "days": days,
        }
    finally:
        mt5.shutdown()


def sync(days: int) -> bool:
    try:
        payload = fetch(days)
    except RuntimeError as e:
        print(f"[mt5-sync] {e}")
        return False

    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{TJ_URL}/api/sync",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode())
            if result.get("ok"):
                print(
                    f"[mt5-sync] ok — deals:{result.get('processedDeals', 0)} "
                    f"new:{result.get('newTrades', 0)} closed:{result.get('closedTrades', 0)} "
                    f"reopened:{result.get('reopenedTrades', 0)} open-upd:{result.get('updatedOpen', 0)}"
                )
                return True
            print(f"[mt5-sync] server error: {result}")
            return False
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:300]
        print(f"[mt5-sync] HTTP {e.code}: {body}")
        return False
    except Exception as e:
        print(f"[mt5-sync] failed: {e}")
        return False


def main() -> None:
    ap = argparse.ArgumentParser(description="MT5 -> Trading Journal sync")
    ap.add_argument("--loop", type=int, default=0, help="loop every N seconds (0 = one-shot)")
    ap.add_argument("--days", type=int, default=90, help="history window in days (default 90)")
    ap.add_argument("--url", default="http://127.0.0.1:8500", help="journal base url")
    args = ap.parse_args()

    global TJ_URL
    TJ_URL = args.url.rstrip("/")

    if args.loop > 0:
        print(f"[mt5-sync] loop every {args.loop}s, window {args.days}d -> {TJ_URL}")
        while True:
            sync(args.days)
            time.sleep(args.loop)
    else:
        ok = sync(args.days)
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
