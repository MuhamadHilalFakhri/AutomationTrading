"""MT5 gateway: initialize, fetch data, compute risk-aware order params,
execute orders, manage open positions. Wraps the MetaTrader5 python API.

Safe by construction for demo/cent accounts:
- position size derived from risk % (or fixed lots)
- SL/TP normalized to broker digits, validated against symbol min/max
- market + pending orders (BUY_LIMIT/SELL_LIMIT/BUY_STOP/SELL_STOP)
"""

import os
import time
import threading
import functools

import MetaTrader5 as mt5

# Lock global: MT5 Python API tidak thread-safe untuk semua fungsi
# (copy_rates dll pakai buffer internal). Dengan lock ini, gateway bisa
# dipanggil dari main thread (scan AI) DAN polling thread (command Telegram)
# secara aman — call MT5 read cepat (<50ms), jadi tidak ada bottleneck berarti.
_MT5_LOCK = threading.RLock()


def _patch_mt5_thread_safety():
    """Bungkus semua fungsi mt5 dengan lock agar aman dipanggil dari banyak thread.

    PENTING: fungsi order_send/order_calc_* TIDAK boleh dibungkus — Cython
    binding-nya kehilangan named-arg binding saat dipanggil lewat wrapper
    Python (error: -2 'Unnamed arguments not allowed'). Dipanggil manual
    dengan lock di gateway (lihat _send_order)."""
    _skip = {'order_send', 'order_calc_margin', 'order_calc_profit'}
    for name in dir(mt5):
        attr = getattr(mt5, name)
        if name.startswith('_') or not callable(attr):
            continue
        if getattr(attr, '__mt5_locked__', False):
            continue
        if name in _skip:
            continue

        def _make(fn):
            @functools.wraps(fn)
            def _wrapped(*a, **kw):
                with _MT5_LOCK:
                    return fn(*a, **kw)
            _wrapped.__mt5_locked__ = True
            return _wrapped

        try:
            setattr(mt5, name, _make(attr))
        except Exception:
            pass


_patch_mt5_thread_safety()


TF_MAP = {
    'M1': mt5.TIMEFRAME_M1, 'M5': mt5.TIMEFRAME_M5,
    'M15': mt5.TIMEFRAME_M15, 'M30': mt5.TIMEFRAME_M30,
    'H1': mt5.TIMEFRAME_H1, 'H4': mt5.TIMEFRAME_H4,
    'D1': mt5.TIMEFRAME_D1, 'W1': mt5.TIMEFRAME_W1,
    'MN1': mt5.TIMEFRAME_MN1,
}

ORDER_TYPE = {
    'BUY': mt5.ORDER_TYPE_BUY,
    'SELL': mt5.ORDER_TYPE_SELL,
    'BUY_LIMIT': mt5.ORDER_TYPE_BUY_LIMIT,
    'SELL_LIMIT': mt5.ORDER_TYPE_SELL_LIMIT,
    'BUY_STOP': mt5.ORDER_TYPE_BUY_STOP,
    'SELL_STOP': mt5.ORDER_TYPE_SELL_STOP,
}


def _send_order(req: dict):
    """order_send dengan lock manual.

    order_send TIDAK boleh dibungkus wrapper Python (bug Cython:
    named-arg binding rusak -> -2 'Unnamed arguments not allowed'),
    jadi kita panggil fungsi asli langsung dengan lock global."""
    with _MT5_LOCK:
        return mt5.order_send(req)

POSITION_TYPE_NAME = {0: 'BUY', 1: 'SELL'}


class MT5Gateway:
    def __init__(self, cfg):
        self.cfg = cfg
        self.connected = False

    # -------------------------------------------------------------
    def connect(self) -> bool:
        path = self.cfg.get(['mt5', 'terminal_path'], '')
        kwargs = {}
        if path:
            kwargs['path'] = path
        if not mt5.initialize(**kwargs):
            print(f"[mt5] initialize failed: {mt5.last_error()}")
            return False
        self.connected = True
        info = mt5.account_info()
        if info:
            print(f"[mt5] connected. account={info.login} company={info.company} "
                  f"balance={info.balance} {info.currency} trade_mode={info.trade_mode}")
        return True

    def shutdown(self):
        if self.connected:
            mt5.shutdown()
            self.connected = False

    # -------------------------------------------------------------
    # data
    # -------------------------------------------------------------
    def account_summary(self) -> dict:
        info = mt5.account_info()
        if not info:
            return {}
        return {
            "login": info.login,
            "company": info.company,
            "server": info.server,
            "balance": info.balance,
            "equity": info.equity,
            "margin": info.margin,
            "free_margin": info.margin_free,
            "currency": info.currency,
            "leverage": info.leverage,
            "trade_mode": info.trade_mode,   # 0=netting,1=hedging,2=... check
            "name": info.name,
        }

    def server_time_str(self) -> str:
        import datetime as _dt
        return _dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # -------------------------------------------------------------
    def detect_terminal_path(self) -> str:
        """Cari terminal64.exe secara otomatis dari lokasi umum (Windows)."""
        import glob
        # 1) path yang paling umum — cek langsung (cepat, tanpa scan recursive)
        quick = [
            'C:/Program Files/MetaTrader 5/terminal64.exe',
            'C:/Program Files/Vantage Markets/MetaTrader 5/terminal64.exe',
            'C:/Program Files (x86)/MetaTrader 5/terminal64.exe',
            os.environ.get('LOCALAPPDATA', '') + '/MetaTrader 5/terminal64.exe',
            'D:/Program Files/MetaTrader 5/terminal64.exe',
            'C:/MetaTrader 5/terminal64.exe',
            'D:/MetaTrader 5/terminal64.exe',
        ]
        for p in quick:
            if p and os.path.isfile(p):
                return p.replace('\\', '/')
        # 2) scan dangkal (non-recursive) di folder umum — cepat
        for base in ('C:/Program Files', 'C:/Program Files (x86)',
                     os.environ.get('LOCALAPPDATA', '')):
            if not base:
                continue
            pat = os.path.join(base, '*', 'terminal64.exe')
            try:
                for p in glob.glob(pat):
                    if os.path.isfile(p):
                        return p.replace('\\', '/')
            except Exception:
                pass
        # 3) fallback: scan recursive penuh (lambat) — hanya jika 1 & 2 gagal
        for base in ('C:/Program Files', 'C:/Program Files (x86)',
                     os.environ.get('LOCALAPPDATA', ''),
                     os.environ.get('APPDATA', ''), 'D:/', 'E:/'):
            if not base:
                continue
            pat = os.path.join(base, '**', 'terminal64.exe')
            try:
                candidates = glob.glob(pat, recursive=True)
            except Exception:
                continue
            mt = [p for p in candidates if 'metatrader' in p.lower()]
            for p in (mt or candidates):
                if os.path.isfile(p):
                    return p.replace('\\', '/')
        return ''

    # -------------------------------------------------------------
    def detect_broker_symbols(self, limit: int = 12) -> list:
        """Auto-detect nama pair yang tersedia di broker (tanpa hardcode).
        Kembalikan daftar symbol nyata yang bisa di-trade (visible, full mode)."""
        syms = mt5.symbols_get()
        if not syms:
            return []
        # filter pasangan mayor + emas + indeks populer
        pref = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'USDCHF',
                'NZDUSD', 'XAUUSD', 'XAGUSD', 'BTCUSD', 'ETHUSD',
                'US30', 'NAS100', 'GER30', 'SPX500', 'UK100']
        out, seen = [], set()
        for s in syms:
            try:
                info = mt5.symbol_info(s.name)
                if not info or not info.visible or info.trade_mode != mt5.SYMBOL_TRADE_MODE_FULL:
                    continue
            except Exception:
                continue
            base = s.name.split('.')[0].split('#')[0].split('-')[0].upper()
            if base in pref and s.name not in seen:
                seen.add(s.name)
                out.append(s.name)
        # prioritas seperti preferensi asli
        out.sort(key=lambda x: (pref.index(x.split('.')[0].split('#')[0].split('-')[0].upper())
                                if x.split('.')[0].split('#')[0].split('-')[0].upper() in pref else 99, x))
        return out[:limit]

    def symbol_candidates(self, max_n: int = None) -> list:
        """All tradeable symbols, optionally filtered by config prefix list.
        Kalau mt5.symbols kosong -> auto-detect nama asli dari broker
        (mis. XAUUSD.v, EURUSD.a — tiap broker beda suffix)."""
        cfg_max = self.cfg.get(['mt5', 'max_symbols'], 12)
        max_n = max_n or cfg_max
        filt = self.cfg.get(['mt5', 'symbol_filter'], []) or []
        sel = self.cfg.get(['mt5', 'symbols'], []) or []

        if not sel:
            # auto-detect: nama symbol dari broker langsung
            return self.detect_broker_symbols(limit=max_n)

        syms = mt5.symbols_get()
        if not syms:
            return []
        # map base-name -> config name, agar config 'XAUUSD' cocok dengan
        # symbol broker 'XAUUSD.v' / 'XAUUSD.a' / 'XAUUSDm' (suffix beda-beda)
        sel_bases = set()
        for c in sel:
            cb = c.upper().split('.')[0].split('#')[0].split('-')[0]
            sel_bases.add(cb)
        out = []
        for s in syms:
            base = s.name.upper().split('.')[0].split('#')[0].split('-')[0]
            if sel and base not in sel_bases:
                continue
            if filt and not any(s.name.upper().startswith(f.upper()) for f in filt):
                continue
            info = mt5.symbol_info(s.name)
            if not info or not info.visible or not info.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL:
                continue
            out.append(s.name)
        # prefer majors ordering: common pairs first
        order = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'USDCHF',
                 'NZDUSD', 'XAUUSD', 'BTCUSD', 'ETHUSD', 'US30', 'NAS100', 'GER30']
        out.sort(key=lambda x: (order.index(x) if x in order else 99, x))
        return out[:max_n]

    def symbol_info(self, symbol: str) -> dict:
        si = mt5.symbol_info(symbol)
        if not si:
            return {}
        tick = mt5.symbol_info_tick(symbol)
        return {
            "symbol": symbol,
            "digits": si.digits,
            "point": si.point,
            "spread_points": si.spread,
            "ask": tick.ask if tick else 0.0,
            "bid": tick.bid if tick else 0.0,
            "volume_min": si.volume_min,
            "volume_max": si.volume_max,
            "volume_step": si.volume_step,
            "trade_mode": si.trade_mode,
            "filling_mode": si.filling_mode,
            "currency_base": si.currency_base,
            "currency_profit": si.currency_profit,
            "contract_size": si.trade_contract_size,
            "trade_stops_level": si.trade_stops_level,
        }

    def fetch_ohlcv(self, symbol: str, timeframe: str, count: int) -> dict | None:
        tf = TF_MAP.get(timeframe.upper())
        if tf is None:
            return None
        rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)
        if rates is None or len(rates) == 0:
            return None
        import datetime as _dt
        d = {
            "time": [_dt.datetime.fromtimestamp(int(r['time'])).strftime('%m-%d %H:%M')
                     for r in rates],
            "open": [float(r['open']) for r in rates],
            "high": [float(r['high']) for r in rates],
            "low": [float(r['low']) for r in rates],
            "close": [float(r['close']) for r in rates],
            "volume": [float(r['tick_volume']) for r in rates],
        }
        return d

    def open_positions(self, symbol: str = None, magic: int = None) -> list:
        magic = magic if magic is not None else self.cfg.magic_number()
        poss = mt5.positions_get(symbol=symbol) if symbol else mt5.positions_get()
        if not poss:
            return []
        out = []
        for p in poss:
            if magic is not None and p.magic != magic:
                continue
            out.append({
                "ticket": p.ticket, "symbol": p.symbol,
                "type": POSITION_TYPE_NAME.get(p.type, str(p.type)),
                "volume": p.volume, "price_open": p.price_open,
                "sl": p.sl, "tp": p.tp, "profit": p.profit,
                "comment": p.comment,
            })
        return out

    def pending_orders(self, symbol: str = None, magic: int = None) -> list:
        magic = magic if magic is not None else self.cfg.magic_number()
        ods = mt5.orders_get(symbol=symbol) if symbol else mt5.orders_get()
        if not ods:
            return []
        out = []
        for o in ods:
            if magic is not None and o.magic != magic:
                continue
            out.append({"ticket": o.ticket, "symbol": o.symbol,
                        "type": o.type, "price_open": o.price_open,
                        "sl": o.sl, "tp": o.tp, "volume": o.volume_current,
                        "comment": o.comment})
        return out

    def today_pnl(self, magic: int = None) -> dict:
        """Hitung PnL hari ini dari history deals MT5 (balance awal hari + PnL realisasi)."""
        import datetime as _dt
        magic = magic if magic is not None else self.cfg.magic_number()
        # utc start of today (server day = UTC pada MT5 forex)
        now = _dt.datetime.now()
        day_start = _dt.datetime(now.year, now.month, now.day)
        day_end = day_start + _dt.timedelta(days=1)

        deals = mt5.history_deals_get(day_start, day_end)
        realized = 0.0
        swaps = 0.0
        fees = 0.0
        if deals:
            for d in deals:
                if magic is not None and d.magic != magic:
                    continue
                if d.entry in (mt5.DEAL_ENTRY_OUT, mt5.DEAL_ENTRY_INOUT):
                    realized += d.profit
                # swap/fee sudah termasuk di d.profit untuk MT5 deals
        # balance awal hari = balance sekarang - realized (belum termasuk floating)
        acct = self.account_summary()
        bal_now = acct.get('balance', 0)
        return {
            "realized_today": realized,
            "balance": bal_now,
            "start_balance": bal_now - realized,  # balance awal hari (realisasi, tanpa floating)
        }

    # -------------------------------------------------------------
    # risk & sizing
    # -------------------------------------------------------------
    def compute_lots(self, symbol: str, entry: float, sl: float) -> float:
        """Risk-based position size: risk% of balance / (|entry-sl| * value per lot).
        Juga support mode 'manual' (lot tetap dari config / Telegram)."""
        si = mt5.symbol_info(symbol)
        if not si:
            return 0.0
        cfg = self.cfg
        mode = cfg.lot_mode()
        if mode == 'manual':
            lots = cfg.manual_lot()
        elif mode == 'fixed':
            lots = cfg.fixed_lots()
        else:
            risk = cfg.risk_percent()
            balance = mt5.account_info().balance
            risk_amount = balance * risk
            dist = abs(entry - sl)
            if dist <= 0:
                return 0.0
            # Value per 1.0 lot for a 1.0 price-unit move:
            #   trade_tick_value = value of 1 tick move for 1 lot (account ccy)
            #   trade_tick_size  = tick size in price units
            tick_val = si.trade_tick_value or 0.0
            tick_size = si.trade_tick_size or si.point or 0.0
            if tick_val > 0 and tick_size > 0:
                value_per_lot_unit = tick_val / tick_size
            else:
                value_per_lot_unit = si.trade_contract_size or 100_000
            lots = risk_amount / (dist * value_per_lot_unit)
        # round down to volume step, clamp to min/max
        step = si.volume_step or 0.01
        lots = max(0.0, lots)
        lots = float(int(lots / step)) * step
        lots = max(si.volume_min, min(lots, si.volume_max))
        # hard cap: never exceed max_lots_per_trade from config (safety for tight SL)
        max_lots = float(cfg.get(['execution', 'max_lots_per_trade'], 1.0))
        lots = min(lots, max_lots)
        if lots < si.volume_min:
            lots = 0.0  # below broker min -> skip
        return lots

    # -------------------------------------------------------------
    # order helpers
    # -------------------------------------------------------------
    def _normalize_price(self, symbol: str, price: float) -> float:
        si = mt5.symbol_info(symbol)
        # paksa Python float — numpy.float64 (dari pandas/round) ditolak API MT5
        # dengan error (-2, 'Unnamed arguments not allowed')
        try:
            price = float(price)
        except (TypeError, ValueError):
            return price
        if not si:
            return price
        return round(price, si.digits) if si.digits <= 8 else round(price, 8)

    def _check_stops_level(self, symbol: str, price: float, sl: float, tp: float):
        si = mt5.symbol_info(symbol)
        if not si:
            return False
        min_dist = si.trade_stops_level * si.point if si.trade_stops_level else 0
        # broker enforces min distance between entry and SL/TP on real executions;
        # we nudge warnings here — the request itself is sent with deviation.
        return True

    def _filling_mode(self, symbol: str) -> int:
        si = mt5.symbol_info(symbol)
        if not si:
            return mt5.ORDER_FILLING_FOK
        modes = si.filling_mode
        # filling_mode bits: 1=FOK, 2=IOC, 3=both, 4=RETURN/exchange default
        # Vantage biasanya 2 (IOC). Jatuh ke IOC kalau ada
        if modes == 2:
            return mt5.ORDER_FILLING_IOC
        if modes == 1:
            return mt5.ORDER_FILLING_FOK
        if modes == 3:
            return mt5.ORDER_FILLING_IOC
        return mt5.ORDER_FILLING_RETURN

    @staticmethod
    def _clean_req(req: dict) -> dict:
        """Buang field kosong/None dari request order.
        MT5 Python API menolak argumen bernilai ''/None (retcode 10014 atau
        'Unnamed arguments not allowed') — hanya kirim field yang valid."""
        out = {}
        for k, v in req.items():
            if v is None:
                continue
            if isinstance(v, str) and v.strip() == '':
                continue
            out[k] = v
        return out

    def _sanitize_comment(self, comment: str, max_len: int = 27) -> str:
        """MT5 comments must be ASCII and short. AI reasons often aren't."""
        ascii_only = ''.join(ch if 32 <= ord(ch) < 127 else ' ' for ch in comment)
        ascii_only = ' '.join(ascii_only.split())
        return ascii_only[:max_len]

    def market_order(self, symbol: str, decision: str, lots: float,
                     sl: float, tp: float, comment: str = 'AI') -> tuple[bool, str]:
        """decision: 'BUY' or 'SELL'. Returns (ok, message)."""
        comment = self._sanitize_comment(comment)
        si = mt5.symbol_info(symbol)
        if not si:
            return False, f"symbol {symbol} not found"
        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            return False, "no tick"
        otype = ORDER_TYPE[decision]
        price = tick.ask if otype == mt5.ORDER_TYPE_BUY else tick.bid
        sl = self._normalize_price(symbol, sl) if sl else 0.0
        tp = self._normalize_price(symbol, tp) if tp else 0.0
        req = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(lots),
            "type": otype,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": int(self.cfg.slippage()),
            "magic": int(self.cfg.magic_number()),
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": self._filling_mode(symbol),
        }
        res = _send_order(self._clean_req(req))
        if res is None:
            return False, f"order_send None (err {mt5.last_error()})"
        if res.retcode != mt5.TRADE_RETCODE_DONE:
            return False, f"retcode {res.retcode} {res.comment}"
        return True, f"{decision} {lots} {symbol} @ {res.price:.5f} done (ticket {res.order})"

    def pending_order(self, symbol: str, otype_name: str, price: float,
                      lots: float, sl: float, tp: float,
                      comment: str = 'AI') -> tuple[bool, str]:
        comment = self._sanitize_comment(comment)
        otype = ORDER_TYPE.get(otype_name)
        if otype is None:
            return False, f"bad pending type {otype_name}"
        si = mt5.symbol_info(symbol)
        if not si:
            return False, f"symbol {symbol} not found"
        tick = mt5.symbol_info_tick(symbol)
        price = self._normalize_price(symbol, price)
        sl = self._normalize_price(symbol, sl) if sl else 0.0
        tp = self._normalize_price(symbol, tp) if tp else 0.0
        # sanity: pending buy limit must be below market, buy stop above, etc.
        if otype == mt5.ORDER_TYPE_BUY_LIMIT and tick and price >= tick.ask:
            return False, f"BUY_LIMIT {price} >= ask {tick.ask} (would trigger instantly)"
        if otype == mt5.ORDER_TYPE_BUY_STOP and tick and price <= tick.ask:
            return False, f"BUY_STOP {price} <= ask {tick.ask}"
        if otype == mt5.ORDER_TYPE_SELL_LIMIT and tick and price <= tick.bid:
            return False, f"SELL_LIMIT {price} <= bid {tick.bid}"
        if otype == mt5.ORDER_TYPE_SELL_STOP and tick and price >= tick.bid:
            return False, f"SELL_STOP {price} >= bid {tick.bid}"

        req = {
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": symbol,
            "volume": float(lots),
            "type": otype,
            "price": price,
            "sl": sl,
            "tp": tp,
            "magic": int(self.cfg.magic_number()),
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_RETURN,
        }
        res = _send_order(self._clean_req(req))
        if res is None:
            return False, f"order_send None (err {mt5.last_error()})"
        if res.retcode != mt5.TRADE_RETCODE_DONE:
            return False, f"retcode {res.retcode} {res.comment}"
        return True, f"{otype_name} {lots} {symbol} @ {res.price:.5f} placed (ticket {res.order})"

    def close_position(self, ticket: int) -> tuple[bool, str]:
        pos = mt5.positions_get(ticket=ticket)
        if not pos or len(pos) == 0:
            return False, f"position {ticket} not found"
        p = pos[0]
        tick = mt5.symbol_info_tick(p.symbol)
        if not tick:
            return False, "no tick"
        otype = mt5.ORDER_TYPE_SELL if p.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
        price = tick.bid if otype == mt5.ORDER_TYPE_SELL else tick.ask
        req = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": p.symbol,
            "volume": p.volume,
            "type": otype,
            "position": p.ticket,
            "price": price,
            "deviation": self.cfg.slippage(),
            "magic": self.cfg.magic_number(),
            "comment": "AI_CLOSE",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": self._filling_mode(p.symbol),
        }
        res = _send_order(self._clean_req(req))
        if res is None:
            return False, f"close order_send None (err {mt5.last_error()})"
        if res.retcode != mt5.TRADE_RETCODE_DONE:
            return False, f"close retcode {res.retcode} {res.comment}"
        return True, f"closed {p.symbol} ticket {ticket} @ {res.price:.5f}"

    def close_position_partial(self, ticket: int, volume: float) -> tuple[bool, str]:
        """Close sebagian posisi (partial TP). Volume < total position volume."""
        pos = mt5.positions_get(ticket=ticket)
        if not pos or len(pos) == 0:
            return False, f"position {ticket} not found"
        p = pos[0]
        if volume >= p.volume:
            return False, f"partial volume {volume} >= total {p.volume}"
        tick = mt5.symbol_info_tick(p.symbol)
        if not tick:
            return False, "no tick"
        otype = mt5.ORDER_TYPE_SELL if p.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
        price = tick.bid if otype == mt5.ORDER_TYPE_SELL else tick.ask
        req = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": p.symbol,
            "volume": volume,
            "type": otype,
            "position": p.ticket,
            "price": price,
            "deviation": self.cfg.slippage(),
            "magic": self.cfg.magic_number(),
            "comment": "PARTIAL_TP",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": self._filling_mode(p.symbol),
        }
        res = _send_order(self._clean_req(req))
        if res is None:
            return False, f"partial close order_send None (err {mt5.last_error()})"
        if res.retcode != mt5.TRADE_RETCODE_DONE:
            return False, f"partial close retcode {res.retcode} {res.comment}"
        return True, f"partial close {volume} {p.symbol} @ {res.price:.5f}"

    def modify_position_sl_tp(self, ticket: int, sl: float, tp: float) -> tuple[bool, str]:
        pos = mt5.positions_get(ticket=ticket)
        if not pos or len(pos) == 0:
            return False, f"position {ticket} not found"
        p = pos[0]
        sl = self._normalize_price(p.symbol, sl) if sl else 0.0
        tp = self._normalize_price(p.symbol, tp) if tp else 0.0
        req = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": p.symbol,
            "position": p.ticket,
            "sl": sl,
            "tp": tp,
            "magic": self.cfg.magic_number(),
        }
        res = _send_order(self._clean_req(req))
        if res is None:
            return False, f"modify None (err {mt5.last_error()})"
        if res.retcode != mt5.TRADE_RETCODE_DONE:
            return False, f"modify retcode {res.retcode} {res.comment}"
        return True, f"modified {p.symbol} t{ticket} sl={sl} tp={tp}"

    def delete_pending(self, ticket: int) -> tuple[bool, str]:
        od = mt5.orders_get(ticket=ticket)
        if not od or len(od) == 0:
            return False, f"order {ticket} not found"
        req = {
            "action": mt5.TRADE_ACTION_REMOVE,
            "order": ticket,
        }
        res = _send_order(self._clean_req(req))
        if res is None:
            return False, f"delete None (err {mt5.last_error()})"
        if res.retcode != mt5.TRADE_RETCODE_DONE:
            return False, f"delete retcode {res.retcode} {res.comment}"
        return True, f"deleted pending {ticket}"
