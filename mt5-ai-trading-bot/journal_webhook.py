"""Journal Webhook — pushes bot events to the Trading Journal web server.

Drop-in module. Use from engine.py:
  from journal_webhook import journal

  journal.push(kind='scan', symbol='XAUUSD', payload='fetching data...')
  journal.push(kind='decision', symbol='XAUUSD', payload=dec)
  journal.push(kind='executed', symbol=symbol, payload=result)
  journal.push(kind='close', symbol=symbol, payload=result)
  journal.push(kind='pnl', payload={"profit": x, "balance": y, "equity": z})
"""

import json
import os
import threading
import time
import urllib.request
import urllib.error

TJ_URL = os.environ.get("TJ_URL", "http://127.0.0.1:8500")
_locker = threading.Lock()
_last_print = 0.0


def push(kind: str, payload: dict, symbol: str | None = None):
    """Fire-and-forget POST to the journal server. Never blocks the bot."""
    def _send():
        global _last_print
        data = json.dumps({"kind": kind, "symbol": symbol, "payload": payload}).encode()
        try:
            req = urllib.request.Request(
                f"{TJ_URL}/api/event",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=3)
        except urllib.error.HTTPError as e:
            if e.code == 404 or e.code == 422:
                pass  # endpoint not running / bad request — skip silently
            else:
                now = time.time()
                if now - _last_print > 30:
                    print(f"[journal] HTTP {e.code} — journal server down?")
                    _last_print = now
        except Exception:
            now = time.time()
            if now - _last_print > 30:
                print(f"[journal] cannot reach {TJ_URL} — server offline?")
                _last_print = now

    threading.Thread(target=_send, daemon=True).start()