"""Bot engine: the main loop that scans symbols, calls AI, executes, manages.

Designed for both:
- continuous loop (run()) — standalone daemon
- one-shot (run_once) — via API or cron trigger
"""

import threading
import time
import traceback

from logger_setup import setup_logger

try:
    from journal_webhook import push as journal_push
except Exception:
    journal_push = None


def _jp(kind, symbol=None, payload=None):
    if journal_push is not None:
        try:
            journal_push(kind, symbol=symbol, payload=payload or {})
        except Exception:
            pass


class BotEngine:
    def __init__(self, cfg, gateway, ai_agent, risk_guard, trade_manager,
                 chart_renderer=None, notifier=None):
        self.cfg = cfg
        self.gw = gateway
        self.ai = ai_agent
        self.risk = risk_guard
        self.tm = trade_manager
        self.chart_renderer = chart_renderer
        self.notifier = notifier
        self.log = setup_logger('engine')

        self._running = False
        self._last_scan = 0.0
        self._last_pos_eval = 0.0
        self._last_pnl_report = 0.0
        self._pnl_report_interval_min = 30.0
        self._signal_history = []  # for /sinyal command
        self._symbols: list[str] = []
        self._tick_cooldown = 0.0  # min seconds between full scans
        self._tg_thread = None
        self._tg_stop = threading.Event()

    # -------------------------------------------------------------
    def run(self, loop_interval_sec: float = 60.0):
        """Continuous loop with Telegram polling in background thread."""
        self._running = True
        print(f"[engine] starting loop every {loop_interval_sec}s")
        self.log.info(f"loop started every {loop_interval_sec}s")
        
        # Start Telegram polling in background thread (only getUpdates, queue commands)
        self._tg_stop.clear()
        self._tg_thread = threading.Thread(target=self._tg_poll_loop, daemon=True)
        self._tg_thread.start()
        
        while self._running and not self._tg_stop.is_set():
            try:
                # scan AI hanya jika sudah waktunya. Command Telegram
                # diproses di poll thread (instan), bukan di sini.
                if time.time() - self._last_scan >= max(loop_interval_sec, 5.0):
                    self.run_once()
                    self._eval_positions()
                    self._maybe_send_pnl_report()
            except Exception as e:
                print(f"[engine] ERROR in tick: {e}")
                self.log.exception("error in tick")
                traceback.print_exc()
            time.sleep(1.0)

    def _tg_poll_loop(self):
        """Background thread: poll Telegram getUpdates + proses command LANGSUNG di sini.
        Tidak antre ke main loop — klik tombol respons instan (≤2 detik) walau
        AI scan sedang berjalan. MT5 aman lintas thread via lock di mt5_gateway."""
        import time as _t
        while self._running and not self._tg_stop.is_set():
            try:
                if self.notifier and self.notifier.enabled:
                    upd = self.notifier.poll_updates()
                    callbacks = upd.get('callbacks', [])
                    cmds = upd.get('cmds', [])
                    if callbacks or cmds:
                        self._process_tg_items(callbacks, cmds)
            except Exception as e:
                print(f"[tg-poll] error: {e}")
            _t.sleep(1.0)

    def _process_tg_items(self, callbacks: list, cmds: list):
        """Jawab callback + jalankan command langsung dari poll thread."""
        # ambil data MT5 sekali untuk seluruh batch (thread-safe via lock)
        try:
            acct = self.gw.account_summary()
            poss = self.gw.open_positions()
            pends = self.gw.pending_orders()
            daily = self.gw.today_pnl()
        except Exception as e:
            print(f"[tg-poll] mt5 data error: {e}")
            # tetap answer callback agar spinner di tombol tidak muter terus
            for cb in callbacks:
                try:
                    self.notifier.answer_callback(cb.get('id', ''))
                except Exception:
                    pass
            # jangan buang command teks: proses dengan data kosong agar
            # user tetap dapat balasan (bukan diam total)
            acct, poss, pends, daily = {}, [], [], {}
        for cb in callbacks:
            try:
                self.notifier.answer_callback(cb.get('id', ''))
            except Exception:
                pass
            cmd = cb.get('data', '')
            try:
                stop_requested = self.notifier.process_command(
                    cmd, acct, poss, pends, self._signal_history, daily)
            except Exception as e:
                print(f"[tg-poll] callback error '{cmd}': {e}")
                traceback.print_exc()
                stop_requested = False
            if stop_requested:
                self.notifier.send("🛑 Bot dihentikan sesuai perintah.")
                self.stop()
                return
        for cmd in cmds:
            try:
                stop_requested = self.notifier.process_command(
                    cmd, acct, poss, pends, self._signal_history, daily)
            except Exception as e:
                print(f"[tg-poll] command error '{cmd}': {e}")
                traceback.print_exc()
                stop_requested = False
            if stop_requested:
                self.notifier.send("🛑 Bot dihentikan sesuai perintah.")
                self.stop()
                return

    def stop(self):
        self._running = False
        self._tg_stop.set()
        # jangan join diri sendiri (stop bisa dipanggil dari poll thread via /stop)
        if (self._tg_thread and self._tg_thread.is_alive()
                and self._tg_thread is not threading.current_thread()):
            self._tg_thread.join(timeout=3.0)

    # -------------------------------------------------------------
    def run_once(self, symbol: str = None) -> list[dict]:
        """Single scan + decisions. Returns list of actions taken."""
        # Catat waktu di awal. Jika fetch/AI gagal sebelum fungsi selesai,
        # loop tetap menunggu interval berikutnya (tidak retry tiap 1 detik).
        self._last_scan = time.time()
        # hot-reload config: perubahan dari GUI 'Simpan' langsung apply
        # tanpa restart (mt5.symbols, active_pairs, risk, dsb)
        try:
            self.cfg.reload()
        except Exception:
            pass
        self._refresh_symbols()
        if symbol:
            symbols = [s for s in self._symbols if s.upper() == symbol.upper()]
        else:
            symbols = self._symbols

        if not symbols:
            print("[engine] no symbols to scan")
            self.log.info("Tidak ada pair untuk di-scan (daftar kosong).")
            return []

        decisions = []
        print(f"[engine] scan dimulai: {', '.join(symbols)}")
        self.log.info(f"🔍 Scan dimulai: {', '.join(symbols)}")
        # ===== PARALLEL AI PIPELINE =====
        # 1) Fetch data MT5 SEQUENTIAL di main thread (MT5 not thread-safe)
        fetched = {}
        for sym in symbols:
            if not self._running:
                return []
            print(f"[engine]   fetch {sym}")
            self.log.info(f"   • Fetch data {sym} …")
            data = self._fetch_symbol_data(sym)
            if data:
                fetched[sym] = data
                print(f"[engine]   {sym}: {len(data)} baris")
                self.log.info(f"   • {sym}: {len(data)} baris data siap")
            else:
                print(f"[engine]   {sym}: tidak ada data")
                self.log.warning(f"   • {sym}: tidak ada data (skip)")

        # 2) AI calls PARALEL via daemon threads (bukan ThreadPoolExecutor —
        #    thread-nya non-daemon, bikin Close gak bisa mati saat AI call
        #    nyangkut). Setiap thread daemon; join di-loop dengan cek stop.
        ai_results = {}
        if fetched and self._running:
            import threading
            _lock = threading.Lock()
            _threads = []
            def _ai_work(sym, data):
                try:
                    r = self._ai_decide_only(sym, data)
                    with _lock:
                        ai_results[sym] = r
                except Exception as e:
                    print(f"[engine] parallel AI error {sym}: {e}")
            for _sym, _data in fetched.items():
                _t = threading.Thread(target=_ai_work, args=(_sym, _data), daemon=True)
                _t.start()
                _threads.append(_t)
            for _t in _threads:
                while _t.is_alive():
                    if not self._running:
                        break  # stop diminta — biarkan daemon mati
                    _t.join(0.5)
            print(f"[engine] AI selesai: {len(ai_results)}/{len(fetched)} simbol")
            self.log.info(f"   • AI selesai ({len(ai_results)}/{len(fetched)} simbol) → evaluasi keputusan")

        # 3) Handle decisions SEQUENTIAL di main thread (order send = MT5 call)
        for sym, decision in ai_results.items():
            if not self._running:
                break
            if not decision:
                continue
            try:
                action = self._handle_decision(sym, fetched[sym], decision)
                if action:
                    decisions.append(action)
            except Exception as e:
                print(f"[engine] handle error {sym}: {e}")
        self._last_scan = time.time()
        return decisions

    # -------------------------------------------------------------
    def _tick(self, interval: float):
        """Legacy single tick (dipakai test/manual). Scan bila sudah waktunya."""
        now = time.time()
        if now - self._last_scan < max(interval, 5.0):
            return
        self.run_once()
        self._eval_positions()
        self._maybe_send_pnl_report()

    # -------------------------------------------------------------
    def _refresh_symbols(self):
        self._symbols = self.gw.symbol_candidates()
        # filter by active_pairs (jika tidak kosong)
        active = self.cfg.active_pairs()
        if active:
            active_set = set(s.upper() for s in active)
            self._symbols = [s for s in self._symbols if s.upper() in active_set]
            print(f"[engine] active pairs: {self._symbols}")

    # -------------------------------------------------------------
    def _eval_positions(self):
        if not self.cfg.tm_evaluate_positions():
            return
        now = time.time()
        # BE/trailing/partial TP harus jalan tiap scan kalau ada posisi open —
        # interval hanya menahan saat tidak ada posisi (hemat panggilan MT5).
        try:
            poss = self.gw.open_positions() or []
        except Exception:
            return
        if not poss and now - self._last_pos_eval < self.cfg.tm_position_eval_interval_min() * 60:
            return
        self._last_pos_eval = now
        if poss:
            print(f"[engine] positions evaluation + trade management ({len(poss)} open)")
        self.tm.manage()

    # -------------------------------------------------------------
    def _maybe_send_pnl_report(self):
        """Send PnL summary via Telegram every N minutes."""
        if not self.notifier or not self.notifier.enabled:
            return
        now = time.time()
        if now - self._last_pnl_report < self._pnl_report_interval_min * 60:
            return
        self._last_pnl_report = now
        try:
            acct = self.gw.account_summary()
            poss = self.gw.open_positions()
            pends = self.gw.pending_orders()
            daily = self.gw.today_pnl()
            self.notifier.notify_pnl(acct, poss, pends,
                                     daily.get('realized_today'), daily.get('start_balance'))
            _jp('pnl', None, {
                'balance': acct.get('balance', 0),
                'equity': acct.get('equity', 0),
                'profit': acct.get('equity', 0) - acct.get('balance', 0),
            })
        except Exception as e:
            print(f"[engine] pnl report error: {e}")

    # -------------------------------------------------------------
    def _compute_indicators(self, ohlcv: dict) -> dict:
        """Hitung RSI/MACD/Stochastic dari OHLCV (menggunakan fungsi chart_renderer)."""
        if not ohlcv or not ohlcv.get('close'):
            return {}
        try:
            from ai.chart_renderer import _rsi, _macd, _stochastic
        except ImportError:
            from chart_renderer import _rsi, _macd, _stochastic
        import numpy as _np
        c = ohlcv['close']
        out = {}
        rsi_arr = _rsi(c, 14)
        if rsi_arr is not None and not _np.isnan(rsi_arr[-1]):
            out['rsi14'] = round(float(rsi_arr[-1]), 1)
        macd_line, macd_sig, macd_hist = _macd(c)
        if macd_line is not None:
            out['macd'] = round(float(macd_line[-1]), 6)
            out['macd_signal'] = round(float(macd_sig[-1]), 6)
            out['macd_hist'] = round(float(macd_hist[-1]), 6)
        st_k, st_d = _stochastic(ohlcv.get('high', []), ohlcv.get('low', []), c)
        if st_k is not None and not _np.isnan(st_k[-1]):
            out['stoch_k'] = round(float(st_k[-1]), 1)
            out['stoch_d'] = round(float(st_d[-1]), 1)
        # EMA20/50 terakhir (untuk konfirmasi trend) — nilai, bukan hanya garis
        try:
            from ai.chart_renderer import _ema
        except ImportError:
            from chart_renderer import _ema
        e20 = _ema(_np.asarray(c, float), 20)
        e50 = _ema(_np.asarray(c, float), 50)
        if e20 is not None:
            out['ema20'] = round(float(e20[-1]), 5)
        if e50 is not None:
            out['ema50'] = round(float(e50[-1]), 5)
        return out

    # -------------------------------------------------------------
    def _process_symbol(self, symbol: str) -> dict | None:
        """Process one symbol SEQUENTIAL mode (used when parallel disabled)."""
        data = self._fetch_symbol_data(symbol)
        if not data:
            return None
        decision = self._ai_decide_only(symbol, data)
        if decision is None:
            return None
        return self._handle_decision(symbol, data, decision)

    @staticmethod
    def _account_type(account: dict) -> str:
        """Return the MT5 account margin type for the AI context.

        ``account_info().trade_mode`` is the account environment
        (demo/contest/real: 0/1/2), while ``margin_mode`` is the account
        position model (netting/exchange/hedging: 0/1/2).
        """
        margin_mode = account.get('margin_mode')
        try:
            return {0: 'netting', 1: 'exchange', 2: 'hedging'}.get(
                int(margin_mode), 'unknown')
        except (TypeError, ValueError):
            return 'unknown'

    # -------------------------------------------------------------
    def _fetch_symbol_data(self, symbol: str) -> dict | None:
        """Fetch semua data MT5 untuk 1 symbol (MAIN THREAD ONLY — MT5 not thread-safe)."""
        _jp('scan', symbol, {'state': 'fetching'})
        # TFs per symbol: pakai override kalau ada, kalau tidak pakai default
        tf_map = self.cfg.get(['strategy', 'symbol_timeframes'], {}) or {}
        default_tfs = self.cfg.get(['strategy', 'default_timeframes'],
                                   self.cfg.strategy_timeframes())
        timeframes = tf_map.get(symbol, default_tfs)
        ohlcv = {}
        for tf in timeframes:
            count = self.cfg.chart_candles() if tf == self.cfg.chart_timeframe() else 60
            d = self.gw.fetch_ohlcv(symbol, tf, count)
            if d:
                ohlcv[tf] = d

        if not ohlcv:
            print(f"[engine] no data for {symbol}")
            return None

        # account context
        acct = self.gw.account_summary()
        si = self.gw.symbol_info(symbol)
        tick = None
        if si:
            import MetaTrader5 as mt5
            t = mt5.symbol_info_tick(symbol)
            tick = {"ask": t.ask, "bid": t.bid} if t else None
        open_pos = self.gw.open_positions(symbol)

        # ATR approximation: range of last 20 candles on M5
        atr = 0
        m5_ohlcv = ohlcv.get('M5') or ohlcv.get(list(ohlcv.keys())[0])
        if m5_ohlcv and len(m5_ohlcv['high']) >= 20:
            ranges = [m5_ohlcv['high'][i] - m5_ohlcv['low'][i]
                      for i in range(-20, 0)]
            atr = round(sum(ranges) / len(ranges), 5) if ranges else 0

        # Indikator momentum (RSI/MACD/Stochastic) — dihitung di sini
        # dan dikirim sebagai angka agar AI pakai untuk konfirmasi eksekusi.
        ind = self._compute_indicators(m5_ohlcv)

        # render chart PNG di MAIN THREAD (matplotlib + MT5 fetch) —
        # dikirim ke AI worker sebagai bytes (thread-safe)
        png_bytes = None
        if self.vision_enabled():
            try:
                tf = self.cfg.chart_timeframe()
                n = self.cfg.chart_candles()
                d = ohlcv.get(tf)
                if d is None:
                    d = self.gw.fetch_ohlcv(symbol, tf, n)
                if d:
                    png_bytes = self.chart_renderer.render(symbol, tf, d)
            except Exception as e:
                print(f"[engine] render failed {symbol}: {e}")

        extra = {
            "server_time": self.gw.server_time_str(),
            "balance": acct.get('balance', 0),
            "equity": acct.get('equity', 0),
            "currency": acct.get('currency', 'USD'),
            # account_info.trade_mode adalah DEMO/CONTEST/REAL;
            # tipe akun netting/hedging berasal dari margin_mode.
            "account_type": self._account_type(acct),
            "spread_points": si.get('spread_points', 0) if si else 0,
            "atr_points": atr / (si.get('point', 0.00001) or 0.00001) if si and atr > 0 else 0,
            "open_positions": open_pos,
            "indicators": ind,
        }
        return {
            "symbol": symbol,
            "timeframes": timeframes,
            "ohlcv": ohlcv,
            "open_pos": open_pos,
            "extra": extra,
            "png_bytes": png_bytes,
        }

    def vision_enabled(self) -> bool:
        return bool(self.cfg.get(['provider', 'vision', 'enabled'], False)) and \
               self.chart_renderer is not None

    # -------------------------------------------------------------
    def _ai_decide_only(self, symbol: str, data: dict) -> dict | None:
        """AI call only (network-only, thread-safe) — dipanggil di worker thread."""
        try:
            return self.ai.decide(symbol, data['timeframes'], data['ohlcv'],
                                  data['open_pos'], data['extra'],
                                  png_bytes=data['png_bytes'])
        except Exception as e:
            print(f"[engine] AI error {symbol}: {e}")
            traceback.print_exc()
            return None

    # -------------------------------------------------------------
    def _handle_decision(self, symbol: str, data: dict, decision: dict) -> dict | None:
        """Handle decision di main thread (MT5 calls: cancel, close, execute)."""
        open_pos = data['open_pos']
        print(f"[engine] {symbol} AI: {decision['decision']} conf={decision['confidence']:.2f} "
              f"reason={decision['reason'][:60]}")
        self.log.info(f"{symbol} AI: {decision['decision']} conf={decision['confidence']:.2f} "
                      f"reason={decision['reason'][:100]}")
        _jp('decision', symbol, decision)
        # record signal history for /sinyal command
        import datetime as _dt
        self._signal_history.append({
            "time": _dt.datetime.now().strftime('%H:%M'),
            "symbol": symbol,
            "decision": decision['decision'],
            "strategy": decision.get('strategy', ''),
            "confidence": decision['confidence'],
        })
        self._signal_history = self._signal_history[-50:]

        # Kirim screenshot chart ke Telegram bila diaktifkan & pair dipilih
        try:
            self._maybe_send_chart(symbol, decision, png_bytes=data['png_bytes'])
        except Exception as e:
            print(f"[engine] send_chart error {symbol}: {e}")

        if decision['decision'] == 'HOLD':
            # Cancel pending order symbol ini jika AI bilang HOLD (tidak fresh/tidak valid lagi)
            self._cancel_stale_pending(symbol, decision)
            return {"symbol": symbol, "action": "HOLD", "decision": decision}

        if decision['decision'] == 'CLOSE':
            if open_pos:
                action = self._close(symbol, open_pos, decision)
            else:
                action = {"symbol": symbol, "action": "NO_CLOSE_TARGET", "decision": decision}
            return action

        # --- correlation guard (posisi baru tidak boleh bikin exposure tak sehat) ---
        allowed, reason = self._correlation_check(decision, symbol)
        if not allowed:
            print(f"[engine] CORRELATION BLOCK {symbol}: {reason}")
            self.log.warning(f"CORRELATION BLOCK {symbol}: {reason}")
            result = {"symbol": symbol, "action": "CORRELATION_BLOCK", "reason": reason,
                      "decision": decision}
            if self.notifier:
                self.notifier.notify_trade(result)
            return result

        # --- risk check ---
        allowed, reason = self.risk.check(decision, symbol)
        if not allowed:
            print(f"[engine] RISK BLOCK {symbol}: {reason}")
            self.log.warning(f"RISK BLOCK {symbol}: {reason}")
            result = {"symbol": symbol, "action": "RISK_BLOCK", "reason": reason,
                      "decision": decision}
            _jp('risk_block', symbol, result)
            if self.notifier:
                self.notifier.notify_trade(result)
            return result

        # --- execute ---
        return self._execute_market_or_pending(symbol, decision)

    # -------------------------------------------------------------
    # CORRELATION GUARD
    # Pairs yang berkorelasi tinggi: bergerak hampir identik (atau berlawanan).
    # Kalau semua posisi searah di pair berkorelasi, 1 pergerakan USD bisa
    # membuat SEMUA posisi loss bersamaan = 1 risiko dikali banyak.
    # -------------------------------------------------------------
    CORRELATION_GROUPS = [
        {"EURUSD", "GBPUSD", "AUDUSD"},          # USD-bearish trio (positively correlated)
        {"USDJPY", "USDCAD", "USDCHF"},          # USD-bullish trio
        {"XAUUSD"},                               # gold sendiri
        {"NAS100.r", "US30"},                     # index US
    ]

    def _correlation_check(self, decision: dict, symbol: str) -> tuple[bool, str]:
        """Tolak entry baru jika terlalu banyak posisi searah di grup korelasi."""
        if decision['decision'] not in ('BUY', 'SELL', 'BUY_LIMIT', 'SELL_LIMIT',
                                        'BUY_STOP', 'SELL_STOP'):
            return True, "ok"
        cfg_max = self.cfg.get(['execution', 'max_correlated_positions'], 2)
        if not cfg_max:
            return True, "ok"
        side = 'BUY' if decision['decision'].startswith('BUY') else 'SELL'
        group = next((g for g in self.CORRELATION_GROUPS if symbol in g), None)
        if not group:
            return True, "ok"
        # hitung posisi terbuka searah di grup yang sama (pending dihitung juga)
        same_side = 0
        for p in self.gw.open_positions():
            if p.get('symbol') in group and str(p.get('type')).startswith(side):
                same_side += 1
        for o in self.gw.pending_orders():
            ot = str(o.get('type'))
            otype_name = {2: 'BUY', 3: 'SELL', 4: 'BUY', 5: 'SELL'}.get(o.get('type'), '')
            if o.get('symbol') in group and otype_name == side:
                same_side += 1
        if same_side >= cfg_max:
            return False, (f"correlated {side} exposure in {group} = {same_side} "
                           f"(max {cfg_max}). Tunggu posisi lama close atau cari pair lain.")
        return True, "ok"

    # -------------------------------------------------------------
    def _maybe_send_chart(self, symbol: str, decision: dict, png_bytes: bytes = None):
        """Kirim chart PNG ke Telegram bila fitur aktif & symbol termasuk daftar."""
        if not self.notifier or not self.notifier.enabled:
            return
        # cek config: aktif?
        cfg_charts = self.cfg.get(['telegram', 'send_charts'], {}) or {}
        if not cfg_charts.get('enabled', False):
            return
        # cek: apakah symbol ini termasuk daftar? (empty list = semua symbol)
        allowed = cfg_charts.get('symbols', [])
        if allowed and symbol not in allowed:
            return
        # hanya kirim jika AI kasih decision (bukan HOLD)
        if decision.get('decision') == 'HOLD':
            return
        # caption ringkas
        dec = decision.get('decision', '?')
        conf = decision.get('confidence', 0)
        strat = decision.get('strategy', '')
        reason = (decision.get('reason') or '')[:100]
        caption = (f"📊 <b>{symbol}</b>\n"
                   f"Decision: <b>{dec}</b> (conf {conf:.0%})\n"
                   f"Strategy: {strat}\n"
                   f"Reason: {reason}")
        # kalau AI sudah render chart-nya, kirim langsung (hemat waktu)
        if png_bytes:
            try:
                self.notifier.send_photo(png_bytes, caption)
                return
            except Exception as e:
                print(f"[engine] send_chart (png AI) error {symbol}: {e}")
                # fallback: render ulang di bawah
        # render chart
        try:
            tf = self.cfg.chart_timeframe()
            n = self.cfg.chart_candles()
            d = self.gw.fetch_ohlcv(symbol, tf, n)
            if not d or not self.chart_renderer:
                return
            png = self.chart_renderer.render(symbol, tf, d)
            if not png:
                return
            self.notifier.send_photo(png, caption)
        except Exception as e:
            print(f"[engine] send_chart error {symbol}: {e}")

    # -------------------------------------------------------------
    def _cancel_stale_pending(self, symbol: str, decision: dict):
        """Cancel pending orders symbol ini jika AI bilang HOLD (setup tidak fresh)."""
        import MetaTrader5 as mt5
        try:
            pending = self.gw.pending_orders(symbol)
        except Exception as e:
            print(f"[engine] cancel_pending error: {e}")
            return
        if not pending:
            return
        for p in pending:
            ticket = p.get('ticket')
            if not ticket:
                continue
            req = {"action": mt5.TRADE_ACTION_REMOVE, "order": ticket}
            res = mt5.order_send(req)
            if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                print(f"[engine] CANCEL pending {ticket} {symbol} (AI HOLD)")
                self.log.info(f"CANCEL pending {ticket} {symbol} (AI HOLD)")
                if self.notifier and self.notifier.enabled:
                    self.notifier.send(
                        f"🗑️ <b>Cancel pending</b>\n"
                        f"├ {symbol} ticket {ticket}\n"
                        f"└ AI: setup tidak fresh lagi (HOLD)")
            else:
                err = res.comment if res else 'no response'
                print(f"[engine] CANCEL FAILED {ticket}: {err}")

    # -------------------------------------------------------------
    def _execute_market_or_pending(self, symbol: str, decision: dict) -> dict:
        d = decision['decision']
        entry = decision['entry']
        sl = decision['sl']
        tp = decision['tp']
        reason = decision['reason']

        is_pending = d.endswith('_LIMIT') or d.endswith('_STOP')
        lots = self.gw.compute_lots(symbol, entry, sl)

        if is_pending:
            price = decision.get('pending_price', entry)
            ok, msg = self.gw.pending_order(symbol, d, price, lots, sl, tp, comment=reason[:30])
        else:
            ok, msg = self.gw.market_order(symbol, d, lots, sl, tp, comment=reason[:30])

        if ok:
            self.risk.mark_action(symbol)
            self.log.info(f"ORDER OK {symbol}: {msg}")
        else:
            print(f"[engine] ORDER FAIL {symbol}: {msg}")
            self.log.error(f"ORDER FAIL {symbol}: {msg}")

        result = {
            "symbol": symbol,
            "action": "EXECUTED" if ok else "FAILED",
            "order_type": d,
            "lots": lots,
            "entry": entry,
            "sl": sl,
            "tp": tp,
            "message": msg,
            "decision": decision,
        }
        _jp('executed' if ok else 'failed', symbol, result)
        if self.notifier:
            self.notifier.notify_trade(result)
        return result

    # -------------------------------------------------------------
    def _close(self, symbol: str, positions: list[dict], decision: dict) -> dict:
        results = []
        for p in positions:
            ok, msg = self.gw.close_position(p['ticket'])
            self.log.info(f"CLOSE {symbol} t{p['ticket']}: ok={ok} {msg}")
            results.append({"ticket": p['ticket'], "ok": ok, "msg": msg})
        self.risk.mark_action(symbol)
        result = {"symbol": symbol, "action": "CLOSE", "results": results, "decision": decision}
        _jp('close', symbol, result)
        if self.notifier:
            self.notifier.notify_trade(result)
        return result