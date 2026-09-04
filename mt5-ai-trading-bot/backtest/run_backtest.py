"""Backtest engine v2 — supports market + pending orders, multi-TF context, proper PnL.

Usage:
  python backtest/run_backtest.py --symbol EURUSD --tf M5 --bars 500 --steps 50
  python backtest/run_backtest.py --symbol EURUSD --tf M5 --bars 300 --steps 20 --strategy snd
"""

import argparse
import hashlib
import json
import os
import sys
import time
import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'server'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from config import Config
from mt5_gateway import MT5Gateway
from ai.agent import AIAgent
from ai.prompts import build_system_prompt, build_market_context
from ai.chart_renderer import ChartRenderer


class SimTrade:
    def __init__(self, bar_idx, bar_time, decision, entry, sl, tp, lots, confidence, is_pending, pending_price=0):
        self.open_idx = bar_idx
        self.open_time = bar_time
        self.decision = decision
        self.entry = entry
        self.sl = sl
        self.tp = tp
        self.lots = lots
        self.confidence = confidence
        self.is_pending = is_pending
        self.pending_price = pending_price
        self.filled_idx = None
        self.filled_time = None
        self.filled_price = None
        self.close_idx = None
        self.close_time = None
        self.exit_price = None
        self.pnl = 0.0
        self.exit_reason = "OPEN"

    def is_buy(self):
        return self.decision.startswith('BUY')

    def check_pending_trigger(self, idx, bar_time, high, low):
        """Check if a pending order gets triggered. Returns fill price or None."""
        if self.filled_price is not None:
            return None
        pp = self.pending_price
        if self.is_buy:
            # BUY_LIMIT: price must go DOWN to pending_price (low <= pending_price)
            # BUY_STOP: price must go UP to pending_price (high >= pending_price)
            if self.decision == 'BUY_LIMIT' and low <= pp and high >= pp:
                return pp
            elif self.decision == 'BUY_STOP' and high >= pp:
                return pp
        else:
            if self.decision == 'SELL_LIMIT' and high >= pp and low <= pp:
                return pp
            elif self.decision == 'SELL_STOP' and low <= pp:
                return pp
        return None

    def fill(self, idx, bar_time, price):
        self.filled_idx = idx
        self.filled_time = bar_time
        self.filled_price = price
        self.entry = price  # actual fill price

    def check_sl_tp(self, high, low):
        if self.filled_price is None:
            return None, None, None, None
        if self.is_buy():
            if low <= self.sl:
                return True, False, self.sl, "SL"
            if high >= self.tp:
                return False, True, self.tp, "TP"
        else:
            if high >= self.sl:
                return True, False, self.sl, "SL"
            if low <= self.tp:
                return False, True, self.tp, "TP"
        return None, None, None, None

    def close(self, price, reason, idx=None):
        self.close_idx = idx or self.filled_idx
        self.exit_price = price
        self.exit_reason = reason
        # PnL for forex: (price_diff / point) * lots * contract_size * point = price_diff * lots * 100000
        # For 0.01 lots: (price_diff) * 0.01 * 100000 = price_diff * 1000
        if self.is_buy():
            self.pnl = (price - self.entry) * self.lots * 100000
        else:
            self.pnl = (self.entry - price) * self.lots * 100000
        return self.pnl


    def to_dict(self):
        return {
            "symbol": "", "type": self.decision.replace("_LIMIT", "").replace("_STOP", ""),
            "volume": self.lots, "price_open": self.entry,
            "sl": self.sl, "tp": self.tp, "profit": self.pnl,
        }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--symbol', default='EURUSD')
    ap.add_argument('--tf', default='M5')
    ap.add_argument('--bars', type=int, default=500)
    ap.add_argument('--steps', type=int, default=0)
    ap.add_argument('--start', type=int, default=200)
    ap.add_argument('--strategy', default='', help='override strategy name from config')
    ap.add_argument('--no-cache', action='store_true')
    ap.add_argument('--output', default='')
    args = ap.parse_args()

    cfg = Config(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config.yaml'))
    if args.strategy:
        cfg.data['strategy']['name'] = args.strategy

    # Fetch data
    gw = MT5Gateway(cfg)
    if not gw.connect():
        print("FATAL: MT5 not connected")
        sys.exit(1)

    print(f"Fetching {args.bars} bars of {args.symbol} {args.tf}...")
    ohlcv_raw = gw.fetch_ohlcv(args.symbol, args.tf, args.bars)
    gw.shutdown()

    if not ohlcv_raw or len(ohlcv_raw['close']) < 100:
        print("FATAL: not enough data")
        sys.exit(1)

    n = len(ohlcv_raw['close'])
    print(f"Got {n} bars, {ohlcv_raw['time'][0]} to {ohlcv_raw['time'][-1]}")

    renderer = ChartRenderer()
    ai = AIAgent(cfg)
    use_cache = not args.no_cache
    cache = {}
    cache_hits = 0
    cache_misses = 0

    start = max(args.start, 50)
    step_size = max(1, (n - start) // max(args.steps, 1)) if args.steps > 0 else 1
    steps = list(range(start, n, step_size))
    print(f"Steps: {len(steps)} (step_size={step_size})")

    trades = []
    balance = 10000.0
    equity_curve = []
    trade_num = 0

    for step_idx in steps:
        bar = {
            "time": ohlcv_raw['time'][step_idx],
            "open": ohlcv_raw['open'][step_idx],
            "high": ohlcv_raw['high'][step_idx],
            "low": ohlcv_raw['low'][step_idx],
            "close": ohlcv_raw['close'][step_idx],
        }

        # Check pending order fills BEFORE checking SL/TP of existing filled positions
        for t in trades:
            if t.filled_price is not None or not t.is_pending:
                continue
            fill_price = t.check_pending_trigger(
                step_idx, bar['time'], bar['high'], bar['low'])
            if fill_price is not None:
                t.fill(step_idx, bar['time'], fill_price)
                print(f"  FILLED {t.decision} {args.symbol} @ {fill_price:.5f} (bar {step_idx})")

        # Check SL/TP for filled positions
        for t in trades:
            if t.exit_price is not None:
                continue
            if t.filled_price is None:
                continue
            hit_sl, hit_tp, px, reason = t.check_sl_tp(bar['high'], bar['low'])
            if hit_sl or hit_tp:
                t.close(px, reason, step_idx)
                balance += t.pnl
                print(f"  CLOSE {t.decision} {args.symbol} @ {px:.5f} ({reason}) PnL={t.pnl:.2f}")

        # Slice data up to this bar for context
        slice_data = {}
        for tf in cfg.strategy_timeframes():
            if tf == args.tf:
                slice_data[tf] = {
                    "time": ohlcv_raw['time'][:step_idx + 1],
                    "open": ohlcv_raw['open'][:step_idx + 1],
                    "high": ohlcv_raw['high'][:step_idx + 1],
                    "low": ohlcv_raw['low'][:step_idx + 1],
                    "close": ohlcv_raw['close'][:step_idx + 1],
                    "volume": ohlcv_raw['volume'][:step_idx + 1],
                }
            else:
                # Fetch higher TF data from MT5 for context
                d = gw.fetch_ohlcv(args.symbol, tf, 60)
                if d:
                    slice_data[tf] = d

        # Cache key
        prompt_key = json.dumps({
            "symbol": args.symbol, "close": bar['close'],
            "step": step_idx, "strategy": args.strategy or cfg.strategy_name(),
        }, sort_keys=True)
        p_hash = hashlib.md5(prompt_key.encode()).hexdigest()[:12]

        if use_cache and p_hash in cache:
            decision = cache[p_hash]
            cache_hits += 1
        else:
            cache_misses += 1
            extra = {
                "server_time": ohlcv_raw['time'][step_idx],
                "balance": balance,
                "equity": balance,
                "currency": "USD",
                "spread_points": 5,
                "open_positions": [t.to_dict() for t in trades if t.exit_price is None],
            }
            try:
                decision = ai.decide(args.symbol, cfg.strategy_timeframes(),
                                     slice_data, [], extra)
            except Exception as e:
                print(f"  AI error step {step_idx}: {e}")
                decision = {"decision": "HOLD", "confidence": 0.0,
                            "entry": 0, "sl": 0, "tp": 0, "pending_price": 0,
                            "reason": "error"}
            if use_cache:
                cache[p_hash] = decision

        d = decision['decision']
        conf = decision['confidence']
        if d in ('BUY', 'SELL', 'BUY_LIMIT', 'SELL_LIMIT', 'BUY_STOP', 'SELL_STOP') and conf >= cfg.min_conf():
            lots = 0.01
            is_pending = d in ('BUY_LIMIT', 'SELL_LIMIT', 'BUY_STOP', 'SELL_STOP')
            entry = bar['close'] if not is_pending else decision['entry']
            pending_price = decision.get('pending_price', 0) if is_pending else 0
            sl = decision['sl']
            tp = decision['tp']

            # Basic sanity: skip if SL/TP invalid
            if sl <= 0 or tp <= 0:
                print(f"  SKIP {d} — no SL/TP")
                continue

            t = SimTrade(step_idx, ohlcv_raw['time'][step_idx], d, entry, sl, tp,
                         lots, conf, is_pending, pending_price)
            if not is_pending:
                t.fill(step_idx, bar['time'], entry)
            trades.append(t)
            trade_num += 1
            order_type = "MKT" if not is_pending else d
            print(f"[{trade_num}] STEP {step_idx} {order_type} conf={conf:.2f} "
                  f"entry={entry:.5f} SL={sl:.5f} TP={tp:.5f} | {decision['reason'][:60]}")

        # Calc equity
        floating = 0.0
        for t in trades:
            if t.exit_price is not None:
                continue
            if t.filled_price is None:
                continue
            if t.is_buy():
                floating += (bar['close'] - t.entry) * t.lots * 100000
            else:
                floating += (t.entry - bar['close']) * t.lots * 100000
        equity_curve.append(balance + floating)

    # Summary
    closed = [t for t in trades if t.exit_price is not None]
    wins = [t for t in closed if t.pnl > 0]
    losses = [t for t in closed if t.pnl < 0]
    total_pnl = sum(t.pnl for t in closed)
    win_rate = len(wins) / len(closed) * 100 if closed else 0
    max_drawdown = 0
    peak = equity_curve[0] if equity_curve else balance
    for eq in equity_curve:
        if eq > peak:
            peak = eq
        dd = (peak - eq) / peak * 100 if peak > 0 else 0
        if dd > max_drawdown:
            max_drawdown = dd

    pending_filled = len([t for t in trades if t.is_pending and t.filled_price is not None])
    pending_unfilled = len([t for t in trades if t.is_pending and t.filled_price is None])

    print("\n" + "=" * 60)
    print(f"BACKTEST — {args.symbol} {args.tf} | strategy={args.strategy or cfg.strategy_name()}")
    print("=" * 60)
    print(f"Bars: {n} | Steps: {len(steps)} | AI calls: {cache_misses}")
    print(f"Trades: {len(trades)} | Closed: {len(closed)} | Wins: {len(wins)} | Losses: {len(losses)}")
    print(f"Pending: {pending_filled} filled, {pending_unfilled} unfilled")
    print(f"Win rate: {win_rate:.1f}%")
    print(f"Total PnL: {total_pnl:.2f}")
    print(f"Final balance: {balance:.2f} | Max DD: {max_drawdown:.2f}%")
    if cache_hits > 0:
        print(f"Cache hits: {cache_hits}")

    strat_name = args.strategy or cfg.strategy_name()
    out = args.output or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), '..', 'reports',
        f"backtest_{args.symbol}_{args.tf}_{strat_name}_{datetime.date.today()}.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    report = {
        "symbol": args.symbol, "timeframe": args.tf,
        "strategy": args.strategy or cfg.strategy_name(),
        "bars": n, "steps": len(steps), "ai_calls": cache_misses,
        "trades": len(trades), "closed": len(closed),
        "wins": len(wins), "losses": len(losses),
        "pending_filled": pending_filled, "pending_unfilled": pending_unfilled,
        "win_rate_pct": round(win_rate, 1), "total_pnl": round(total_pnl, 2),
        "final_balance": round(balance, 2), "max_drawdown_pct": round(max_drawdown, 2),
        "equity_curve": [round(e, 2) for e in equity_curve],
        "trades": [
            {"decision": t.decision, "entry": t.entry, "sl": t.sl, "tp": t.tp,
             "lots": t.lots, "pnl": round(t.pnl, 2), "exit_reason": t.exit_reason,
             "confidence": t.confidence, "is_pending": t.is_pending,
             "filled_price": t.filled_price}
            for t in closed
        ],
    }
    with open(out, 'w') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"Report: {out}")


if __name__ == '__main__':
    main()