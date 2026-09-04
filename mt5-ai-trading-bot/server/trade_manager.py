"""Trade manager: breakeven + trailing stop + partial TP for open positions (this bot's magic only)."""

import json
import os
import MetaTrader5 as mt5


class TradeManager:
    STATE_FILE = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        '.partial_tp_state.json')

    def __init__(self, cfg, gateway):
        self.cfg = cfg
        self.gw = gateway
        # tickets yang sudah di-partial close (persist across restarts)
        self._partial_done = self._load_state()

    # ---------------- state persist ----------------
    def _load_state(self) -> dict:
        try:
            with open(self.STATE_FILE) as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_state(self):
        try:
            with open(self.STATE_FILE, 'w') as f:
                json.dump(self._partial_done, f)
        except Exception:
            pass

    def manage(self):
        if not self.cfg.tm_enabled():
            return
        open_tickets = set()
        for p in self.gw.open_positions():
            open_tickets.add(p['ticket'])
            self._manage_one(p)
        # prune state: buang ticket yang sudah tidak terbuka
        stale = [t for t in self._partial_done if t not in open_tickets]
        for t in stale:
            del self._partial_done[t]
        if stale:
            self._save_state()

    # -------------------------------------------------------------
    # PARTIAL TP (scale out)
    # Saat profit capai trigger (fraksi dari jarak ke TP), close sebagian lot
    # (default 50%) + tarik SL ke BE. Sisa posisi jalan ke TP penuh tanpa risiko.
    # -------------------------------------------------------------
    def _try_partial_tp(self, p, si, tick, point, digits, profit_points) -> bool:
        if not bool(self.cfg.get(['trade_management', 'partial_tp_enabled'], True)):
            return False
        ticket = p['ticket']
        if ticket in self._partial_done:
            return False
        # butuh TP valid untuk hitung trigger
        tp = p.get('tp')
        if not tp:
            return False
        entry = p['price_open']
        is_buy = p['type'] == 'BUY'
        tp_dist_points = abs(tp - entry) / point
        if tp_dist_points <= 0:
            return False
        trigger_fraction = float(self.cfg.get(['trade_management', 'partial_tp_trigger_fraction'], 0.6))
        trigger_points = tp_dist_points * trigger_fraction
        if profit_points < trigger_points:
            return False
        # minimal lot tersisa harus valid (broker min lot)
        close_frac = float(self.cfg.get(['trade_management', 'partial_tp_close_fraction'], 0.5))
        vol = p['volume']
        close_vol = round(vol * close_frac, 2)
        min_lot = si.volume_min
        step = si.volume_step or 0.01
        if close_vol < min_lot or (vol - close_vol) < min_lot:
            return False
        # snap ke volume step
        close_vol = max(min_lot, round(close_vol / step) * step)
        cur = tick.bid if is_buy else tick.ask
        ok, msg = self.gw.close_position_partial(ticket, close_vol)
        if ok:
            self._partial_done[ticket] = {
                'closed_volume': close_vol, 'at_points': round(profit_points, 1)}
            self._save_state()
            # tarik SL ke BE+lock segera
            be = self._be_price(p, point, is_buy)
            be_valid = (cur - be) > (si.trade_stops_level or 0) * point if is_buy \
                else (be - cur) > (si.trade_stops_level or 0) * point
            if be_valid:
                ok2, msg2 = self.gw.modify_position_sl_tp(ticket, round(be, digits), tp)
                print(f"[tm] PARTIAL TP {p['symbol']} t{ticket} closed {close_vol} lots "
                      f"@ {cur:.{digits}f} ({profit_points:.0f} pts) "
                      f"SL->BE {'ok' if ok2 else 'failed: '+msg2}")
            else:
                print(f"[tm] PARTIAL TP {p['symbol']} t{ticket} closed {close_vol} lots "
                      f"@ {cur:.{digits}f} ({profit_points:.0f} pts) SL->BE skipped (too close)")
            import logging
            logging.getLogger('engine').info(
                f"PARTIAL TP {p['symbol']} t{ticket} {close_vol} lots @{cur:.{digits}f} "
                f"({profit_points:.0f} pts)")
            return True
        else:
            print(f"[tm] partial close failed t{ticket}: {msg}")
            return False

    def _be_price(self, p: dict, point, is_buy):
        """Price that locks at least breakeven + small lock for this position."""
        entry = p['price_open']
        lock = self.cfg.tm_bep_lock() * point
        return (entry + lock) if is_buy else (entry - lock)

    def _manage_one(self, p: dict):
        symbol = p['symbol']
        ticket = p['ticket']
        si = mt5.symbol_info(symbol)
        tick = mt5.symbol_info_tick(symbol)
        if not si or not tick:
            return
        point = si.point
        digits = si.digits
        is_buy = p['type'] == 'BUY'
        cur = tick.bid if is_buy else tick.ask
        entry = p['price_open']
        sl = p['sl']
        tp = p['tp']
        profit_points = (cur - entry) / point if is_buy else (entry - cur) / point

        trigger = self.cfg.tm_bep_trigger()
        aggressive = bool(self.cfg.get(['trade_management', 'bep_aggressive'], True))

        # --- PARTIAL TP: close sebagian lot saat profit capai trigger RR, SL -> BE ---
        if self._try_partial_tp(p, si, tick, point, digits, profit_points):
            return  # satu aksi per tick per posisi

        # --- breakeven: pull SL to BE+lock as soon as price moves trigger points in our favor ---
        if self.cfg.tm_use_bep() and profit_points >= trigger:
            be_price = self._be_price(p, point, is_buy)
            # only improve (never weaken) and stay valid vs broker stops level
            improves = (is_buy and (sl == 0 or be_price > sl)) or \
                       (not is_buy and (sl == 0 or be_price < sl))
            min_dist = (si.trade_stops_level or 0) * point
            valid = (cur - be_price) > min_dist if is_buy else (be_price - cur) > min_dist
            if improves and valid:
                ok, msg = self.gw.modify_position_sl_tp(ticket, round(be_price, digits), tp)
                if ok:
                    print(f"[tm] BE {symbol} t{ticket} SL->{be_price:.{digits}f} ({profit_points:.0f} pts)")
                    import logging
                    logging.getLogger('engine').info(f"BE {symbol} t{ticket} SL->{be_price:.{digits}f} ({profit_points:.0f} pts)")
                else:
                    print(f"[tm] BE move failed {symbol} t{ticket}: {msg}")
                return  # one action per tick per position

        # --- trailing stop ---
        if self.cfg.tm_use_trailing() and profit_points >= self.cfg.tm_trailing_start():
            step = self.cfg.tm_trailing_step() * point
            if is_buy:
                new_sl = cur - self.cfg.tm_trailing_start() * point
                improves = sl == 0 or new_sl > sl + step
                valid = (cur - new_sl) > (si.trade_stops_level or 0) * point
            else:
                new_sl = cur + self.cfg.tm_trailing_start() * point
                improves = sl == 0 or new_sl < sl - step
                valid = (new_sl - cur) > (si.trade_stops_level or 0) * point
            if improves and valid:
                ok, msg = self.gw.modify_position_sl_tp(ticket, round(new_sl, digits), tp)
                if ok:
                    print(f"[tm] TRAIL {symbol} t{ticket} SL->{new_sl:.{digits}f}")
                else:
                    print(f"[tm] TRAIL failed {symbol} t{ticket}: {msg}")
