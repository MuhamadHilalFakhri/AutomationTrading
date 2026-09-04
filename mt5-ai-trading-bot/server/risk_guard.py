"""Risk guard: validates an AI decision against hard, non-negotiable rules
before any order is sent. Everything here is intentionally conservative."""

import time

import MetaTrader5 as mt5


class RiskGuard:
    def __init__(self, cfg, gateway):
        self.cfg = cfg
        self.gw = gateway
        # per-symbol last action times
        self._last_action: dict[str, float] = {}
        # daily loss tracking: start-of-day balance
        self._day_key = None
        self._day_start_balance = None
        self._halted_today = False

    # -------------------------------------------------------------
    def _update_day(self):
        import datetime as _dt
        today = _dt.date.today().isoformat()
        if self._day_key != today:
            self._day_key = today
            acct = self.gw.account_summary()
            self._day_start_balance = acct.get('balance', 0.0)
            self._halted_today = False

    def daily_loss_exceeded(self) -> bool:
        self._update_day()
        if self._halted_today:
            return True
        acct = self.gw.account_summary()
        eq = acct.get('equity', 0.0)
        start = self._day_start_balance or acct.get('balance', 0.0)
        if start <= 0:
            return False
        loss_pct = (start - eq) / start * 100.0
        if loss_pct >= self.cfg.max_daily_loss_percent():
            self._halted_today = True
            print(f"[risk] DAILY LOSS LIMIT HIT ({loss_pct:.2f}% >= "
                  f"{self.cfg.max_daily_loss_percent()}%) — trading halted for today")
            return True
        return False

    def _cooldown_ok(self, symbol: str) -> tuple[bool, float]:
        last = self._last_action.get(symbol, 0.0)
        wait = self.cfg.cooldown_minutes() * 60.0
        elapsed = time.time() - last
        return elapsed >= wait, max(0.0, wait - elapsed)

    def mark_action(self, symbol: str):
        self._last_action[symbol] = time.time()

    # -------------------------------------------------------------
    def check(self, decision: dict, symbol: str) -> tuple[bool, str]:
        """Return (allowed, reason). decision is the parsed AI dict."""
        d = decision['decision']
        conf = decision['confidence']

        if self.daily_loss_exceeded():
            return False, "daily loss limit reached — halted"

        allowed_types = self.cfg.allowed_order_types()
        is_pending = d.endswith('_LIMIT') or d.endswith('_STOP')
        if is_pending and 'pending' not in allowed_types:
            return False, "pending orders not allowed by config"
        if not is_pending and d in ('BUY', 'SELL') and 'market' not in allowed_types:
            return False, "market orders not allowed by config"

        if conf < self.cfg.min_conf():
            return False, f"confidence {conf:.2f} < min {self.cfg.min_conf():.2f}"

        ok, wait = self._cooldown_ok(symbol)
        if not ok:
            return False, f"cooldown {symbol}: wait {wait:.0f}s"

        # spread guard (per-symbol override; None = unlimited/bebas)
        info = self.gw.symbol_info(symbol)
        if not info:
            return False, f"no symbol info for {symbol}"
        spread = info.get('spread_points', 0)
        max_sp = self.cfg.max_spread_for(symbol)
        if max_sp is not None and spread > max_sp:
            return False, f"spread {spread} > max {max_sp:.0f}"

        # open positions cap
        poss = self.gw.open_positions(symbol)
        if len(poss) >= self.cfg.max_positions_per_symbol() and d != 'CLOSE':
            return False, f"max positions reached for {symbol} ({len(poss)})"

        if d in ('BUY', 'SELL', 'BUY_LIMIT', 'SELL_LIMIT', 'BUY_STOP', 'SELL_STOP'):
            entry, sl, tp = decision['entry'], decision['sl'], decision['tp']
            if sl <= 0 or tp <= 0:
                return False, "SL/TP required (got 0) — refusing naked entry"
            si = mt5.symbol_info(symbol)
            point = si.point if si else 0.00001
            sl_dist = abs(entry - sl) / point
            tp_dist = abs(tp - entry) / point
            min_sl = self.cfg.get(['execution', 'min_sl_points'], 10)
            max_sl = self.cfg.get(['execution', 'max_sl_points'], 20000)
            min_tp = self.cfg.get(['execution', 'min_tp_points'], 10)
            max_tp = self.cfg.get(['execution', 'max_tp_points'], 40000)
            if sl_dist < min_sl:
                return False, f"SL too tight ({sl_dist:.0f} pts < {min_sl})"
            if sl_dist > max_sl:
                return False, f"SL too wide ({sl_dist:.0f} pts > {max_sl})"
            if tp_dist < min_tp:
                return False, f"TP too tight ({tp_dist:.0f} pts < {min_tp})"
            if tp_dist > max_tp:
                return False, f"TP too wide ({tp_dist:.0f} pts > {max_tp})"

            # Risk:Reward guardrail — PER SYMBOL (adaptif, bukan flat 1.5)
            rr_cfg = self.cfg.rr_for(symbol)
            min_rr = float(rr_cfg.get('min_rr', 1.5))
            if sl_dist > 0:
                rr = tp_dist / sl_dist
                if rr < min_rr:
                    return False, f"RR {rr:.2f} < minimum {min_rr} for {symbol} (need TP {tp_dist:.0f}pts vs SL {sl_dist:.0f}pts)"

            # --- DUPLICATE ENTRY GUARD: cek apakah sudah ada posisi/pending di harga sama ---
            tick = mt5.symbol_info_tick(symbol)
            entry_price = decision.get('entry') or decision.get('pending_price') or 0
            if tick and entry_price > 0:
                point = si.point
                # cek posisi terbuka
                for pos in mt5.positions_get(symbol=symbol) or []:
                    if abs(pos.price_open - entry_price) < point * 10:  # toleransi 10 points
                        return False, f"entry price {entry_price} too close to existing position {pos.ticket}"
                # cek pending order
                for ord in mt5.orders_get(symbol=symbol) or []:
                    if abs(ord.price_open - entry_price) < point * 10:
                        return False, f"entry price {entry_price} too close to existing pending order {ord.ticket}"

            # directional sanity: BUY -> sl below entry, tp above; SELL inverse
            if d.startswith('BUY'):
                if sl >= entry:
                    return False, f"BUY with SL {sl} >= entry {entry}"
                if tp <= entry:
                    return False, f"BUY with TP {tp} <= entry {entry}"
            else:
                if sl <= entry:
                    return False, f"SELL with SL {sl} <= entry {entry}"
                if tp >= entry:
                    return False, f"SELL with TP {tp} >= entry {entry}"

            # pending distance guard
            if is_pending:
                max_dist = self.cfg.pending_max_distance_for(symbol)
                tick = mt5.symbol_info_tick(symbol)
                if tick and max_dist != float('inf'):
                    mkt = tick.ask if d.startswith('BUY') else tick.bid
                    dist = abs(decision['pending_price'] - mkt) / point
                    if dist > max_dist:
                        return False, f"pending price too far ({dist:.0f} pts > {max_dist})"

        return True, "ok"
