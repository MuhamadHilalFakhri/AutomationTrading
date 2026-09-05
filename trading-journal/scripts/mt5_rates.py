"""Read OHLC candles from the configured MetaTrader 5 terminal.

This helper is intentionally read-only. It prints one JSON response to stdout
so the Next.js server can expose chart data without changing the sync payload.
"""

import argparse
import json
import os
import sys

try:
    import MetaTrader5 as mt5
except ImportError:
    print(json.dumps({"ok": False, "error": "Package MetaTrader5 belum terpasang"}))
    sys.exit(1)


TIMEFRAMES = {
    "1": mt5.TIMEFRAME_M1,
    "5": mt5.TIMEFRAME_M5,
    "15": mt5.TIMEFRAME_M15,
    "60": mt5.TIMEFRAME_H1,
    "240": mt5.TIMEFRAME_H4,
    "D": mt5.TIMEFRAME_D1,
    "W": mt5.TIMEFRAME_W1,
}


def respond(payload: dict, exit_code: int = 0) -> None:
    print(json.dumps(payload, separators=(",", ":")))
    sys.exit(exit_code)


def main() -> None:
    parser = argparse.ArgumentParser(description="Read MT5 OHLC rates")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--timeframe", choices=TIMEFRAMES.keys(), default="15")
    parser.add_argument("--count", type=int, default=1000)
    args = parser.parse_args()

    terminal_path = os.environ.get("MT5_TERMINAL_PATH")
    initialized = mt5.initialize(path=terminal_path) if terminal_path else mt5.initialize()
    if not initialized:
        respond({"ok": False, "error": "Terminal MT5 tidak dapat dihubungkan"}, 1)

    try:
        info = mt5.symbol_info(args.symbol)
        if info is None:
            respond({"ok": False, "error": f"Symbol {args.symbol} tidak tersedia di broker"}, 1)

        if not info.visible and not mt5.symbol_select(args.symbol, True):
            respond({"ok": False, "error": f"Symbol {args.symbol} tidak dapat diaktifkan"}, 1)

        count = min(max(args.count, 100), 3000)
        rates = mt5.copy_rates_from_pos(args.symbol, TIMEFRAMES[args.timeframe], 0, count)
        if rates is None:
            respond({"ok": False, "error": "MT5 tidak mengembalikan data candle"}, 1)

        candles = [
            {
                "time": int(rate["time"]),
                "open": float(rate["open"]),
                "high": float(rate["high"]),
                "low": float(rate["low"]),
                "close": float(rate["close"]),
                "tickVolume": int(rate["tick_volume"]),
            }
            for rate in rates
        ]

        respond({
            "ok": True,
            "symbol": args.symbol,
            "timeframe": args.timeframe,
            "digits": int(info.digits),
            "candles": candles,
        })
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
