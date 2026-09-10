"""Telegram notifier — menu tombol lengkap (inline + reply keyboard), bahasa Indonesia.

Menu:
  /start, /menu      -> menu utama (tombol inline + keyboard menetap)
  /status            -> ringkasan akun + posisi + pending
  /pnl               -> laporan profit/loss
  /posisi            -> daftar posisi terbuka & pending
  /sinyal            -> sinyal AI terakhir
  /setting           -> konfigurasi bot saat ini
  /bantuan           -> panduan command
  /stop              -> hentikan bot
"""

import json
import os
import re
import urllib.request
import urllib.parse


# label tombol (dikirim sebagai teks saat reply-keyboard ditekan) -> command
BUTTON_TO_CMD = {
    "📊 Status": "status",
    "📈 PnL": "pnl",
    "📌 Posisi": "posisi",
    "🧠 Sinyal": "sinyal",
    "⚙️ Setting": "setting",
    "ℹ️ Bantuan": "bantuan",
    "📋 Menu": "menu",
    "🛑 Stop Bot": "stop",
    "🎯 Pilih Pair": "pilihpair",
    "🔢 Lot": "lot",
}

CMD_TO_LABEL = {
    "status": "📊 Status",
    "pnl": "📈 PnL",
    "posisi": "📌 Posisi",
    "sinyal": "🧠 Sinyal",
    "setting": "⚙️ Setting",
    "bantuan": "ℹ️ Bantuan",
    "menu": "📋 Menu",
    "stop": "🛑 Stop Bot",
    "pilihpair": "🎯 Pilih Pair",
    "lot": "🔢 Lot",
}


class TelegramNotifier:
    def __init__(self, cfg):
        self.cfg = cfg
        self._pair_draft = None  # draft pair selector (set of upper symbols)
        self.enabled = bool(cfg.get(['telegram', 'enabled'], False))
        self.token = (cfg.get(['telegram', 'bot_token'], '')
                      or os.environ.get(cfg.get(['telegram', 'token_env'], 'TELEGRAM_BOT_TOKEN'), ''))
        self.chat_id = (str(cfg.get(['telegram', 'chat_id'], ''))
                        or os.environ.get(cfg.get(['telegram', 'chat_id_env'], 'TELEGRAM_CHAT_ID'), ''))
        self._last_update_id = 0
        self._update_id_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            '.tg_update_id')
        # restore last update_id dari file agar tidak replay command lama
        try:
            with open(self._update_id_file) as f:
                self._last_update_id = int(f.read().strip())
        except Exception:
            pass
        if not self.token or not self.chat_id:
            self.enabled = False
            print("[tg] disabled (token/chat_id tidak disetel)")
        else:
            print(f"[tg] aktif (chat {self.chat_id})")

    # ---------------------------------------------------------------
    # low-level API
    # ---------------------------------------------------------------
    def _api(self, method: str, params: dict) -> dict:
        url = f"https://api.telegram.org/bot{self.token}/{method}"
        # reply_markup harus JSON string
        if 'reply_markup' in params and isinstance(params['reply_markup'], dict):
            params = dict(params)
            params['reply_markup'] = json.dumps(params['reply_markup'])
        data = urllib.parse.urlencode(params).encode()
        try:
            req = urllib.request.Request(url, data=data)
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            # kasih detail biar polling error (409/webhook/network) kelihatan
            detail = ''
            if hasattr(e, 'read'):
                try:
                    detail = e.read().decode('utf-8', 'replace')[:300]
                except Exception:
                    detail = ''
            print(f"[tg] ⚠️ {method} gagal: {e} {detail}")
            return {}

    def send(self, text: str, reply_markup: dict = None) -> bool:
        if not self.enabled:
            return False
        params = {'chat_id': self.chat_id, 'text': text, 'parse_mode': 'HTML'}
        if reply_markup:
            params['reply_markup'] = reply_markup
        res = self._api('sendMessage', params)
        if res.get('ok'):
            return True
        # fallback: HTML parse gagal (karakter aneh) -> kirim tanpa parse_mode
        params.pop('parse_mode', None)
        return bool(self._api('sendMessage', params).get('ok'))

    def send_photo(self, png_bytes: bytes, caption: str = "") -> bool:
        """Kirim foto (PNG) ke Telegram via multipart/form-data."""
        if not self.enabled:
            return False
        import uuid
        boundary = uuid.uuid4().hex
        body = b""
        body += f"--{boundary}\r\n".encode()
        body += b'Content-Disposition: form-data; name="chat_id"\r\n\r\n'
        body += f"{self.chat_id}\r\n".encode()
        body += f"--{boundary}\r\n".encode()
        body += b'Content-Disposition: form-data; name="caption"\r\n\r\n'
        body += f"{caption}\r\n".encode()
        body += f"--{boundary}\r\n".encode()
        body += b'Content-Disposition: form-data; name="photo"; filename="chart.png"\r\n'
        body += b"Content-Type: image/png\r\n\r\n"
        body += png_bytes
        body += f"\r\n--{boundary}--\r\n".encode()
        url = f"https://api.telegram.org/bot{self.token}/sendPhoto"
        try:
            req = urllib.request.Request(
                url, data=body,
                headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                obj = json.loads(resp.read().decode())
                return bool(obj.get('ok'))
        except Exception as e:
            print(f"[tg] sendPhoto gagal: {e}")
            return False

    # ---------------------------------------------------------------
    # keyboards
    # ---------------------------------------------------------------
    def _menu_inline(self) -> dict:
            return {"inline_keyboard": [
                [{"text": "📊 Status", "callback_data": "status"},
                 {"text": "📈 PnL", "callback_data": "pnl"}],
                [{"text": "📌 Posisi", "callback_data": "posisi"},
                 {"text": "🧠 Sinyal", "callback_data": "sinyal"}],
                [{"text": "🎯 Pilih Pair", "callback_data": "pilihpair"},
                 {"text": "🔢 Lot", "callback_data": "lot"}],
                [{"text": "⚙️ Setting", "callback_data": "setting"},
                 {"text": "ℹ️ Bantuan", "callback_data": "bantuan"}],
                [{"text": "🛑 Stop", "callback_data": "stop"}],
            ]}

    def _reply_keyboard(self) -> dict:
        return {"keyboard": [
            [{"text": "📊 Status"}, {"text": "📈 PnL"}],
            [{"text": "📌 Posisi"}, {"text": "🧠 Sinyal"}],
            [{"text": "🎯 Pilih Pair"}, {"text": "⚙️ Setting"}],
            [{"text": "📋 Menu"}, {"text": "ℹ️ Bantuan"}],
            [{"text": "🛑 Stop Bot"}],
        ], "resize_keyboard": True, "persistent": True}

    # ---------------------------------------------------------------
    # polling
    # ---------------------------------------------------------------
    def poll_updates(self) -> dict:
        """Ambil update baru. Return {'cmds': [...], 'callbacks': [{id,data}]}."""
        if not self.enabled:
            return {'cmds': [], 'callbacks': []}
        res = self._api('getUpdates', {
            'offset': self._last_update_id + 1, 'timeout': 0,
            'allowed_updates': ['message', 'callback_query']})
        cmds, callbacks = [], []
        for upd in res.get('result', []):
            self._last_update_id = max(self._last_update_id, upd['update_id'])
            # persist update_id agar restart tidak replay command lama
            try:
                with open(self._update_id_file, 'w') as f:
                    f.write(str(self._last_update_id))
            except Exception:
                pass
            if 'message' in upd:
                msg = upd['message']
                chat_id = str(msg.get('chat', {}).get('id') or '')
                if str(self.chat_id) and chat_id != str(self.chat_id):
                    print(f"[tg] ⚠️ pesan dari chat {chat_id} diabaikan "
                          f"(harus {self.chat_id})")
                    continue
                text = (msg.get('text') or '').strip()
                if not text:
                    continue
                # bisa berupa /command atau label tombol reply-keyboard
                cmd = self._normalize(text)
                if cmd:
                    cmds.append(cmd)
                    print(f"[tg] 📥 command: '{cmd}' (dari chat {chat_id})")
                else:
                    print(f"[tg] ⚠️ teks tidak dikenal (diabaikan): '{text}'")
            elif 'callback_query' in upd:
                cb = upd['callback_query']
                cb_chat = str(cb.get('message', {}).get('chat', {}).get('id') or '')
                if str(self.chat_id) and cb_chat != str(self.chat_id):
                    print(f"[tg] ⚠️ callback dari chat {cb_chat} diabaikan "
                          f"(harus {self.chat_id})")
                    continue
                callbacks.append({'id': cb.get('id'), 'data': cb.get('data', '')})
        return {'cmds': cmds, 'callbacks': callbacks}

    def _normalize(self, text: str) -> str:
        """Map '/status' atau '📊 Status' -> 'status'. 
        Untuk /lot, kembalikan teks lengkap (contoh: 'lot 0.05')."""
        t = text.strip()
        if t.startswith('/'):
            parts = t[1:].split()
            cmd = parts[0].split('@')[0].lower()
            if cmd == 'lot' and len(parts) > 1:
                return f"lot {parts[1]}"  # preserve arg
            return cmd
        # label tombol reply keyboard
        return BUTTON_TO_CMD.get(t, '')

    def answer_callback(self, callback_id: str) -> None:
        if self.enabled:
            self._api('answerCallbackQuery', {'callback_query_id': callback_id})

    # ---------------------------------------------------------------
    # proses update -> balas
    # ---------------------------------------------------------------
    def process_command(self, cmd: str, account: dict, positions: list,
                        pending: list, signals: list, daily: dict = None) -> bool:
        """Jalankan satu command dari queue. Return True jika /stop diminta."""
        cmd = (cmd or '').strip().lower()
        if not cmd:
            return False
        # --- pair selector callbacks: toggle stateful, tanpa build_reply ---
        if cmd == 'pilihpair':
            self._pair_draft = set(s.upper() for s in self.cfg.active_pairs())
            text = self._pilihpair_text(self._pair_draft)
            self.send(text, reply_markup=self._pilihpair_inline(self._pair_draft))
            return False
        if cmd.startswith('pair:'):
            sym = cmd.split(':', 1)[1].upper()
            if self._pair_draft is None:
                self._pair_draft = set(s.upper() for s in self.cfg.active_pairs())
            if sym in self._pair_draft:
                self._pair_draft.discard(sym)
            else:
                self._pair_draft.add(sym)
            text = self._pilihpair_text(self._pair_draft)
            self.send(text, reply_markup=self._pilihpair_inline(self._pair_draft))
            return False
        if cmd == 'pair_save':
            if self._pair_draft is None:
                self._pair_draft = set()
            self.cfg.set_active_pairs(sorted(self._pair_draft))
            self._pair_draft = None
            active = self.cfg.active_pairs()
            msg = ("✅ Pair aktif disimpan: " +
                   (', '.join(active) if active else 'SEMUA pair'))
            self.send(msg, reply_markup=self._menu_inline())
            return False
        if cmd == 'pair_cancel':
            self._pair_draft = None
            self.send("❌ Dibatalkan.", reply_markup=self._menu_inline())
            return False
        if cmd == 'lot':
            mode = self.cfg.lot_mode()
            manual = self.cfg.manual_lot()
            text = self._lot_text(mode, manual)
            self.send(text, reply_markup=self._lot_inline(mode))
            return False
        if cmd.startswith('lot:'):
            sub = cmd.split(':', 1)[1]
            if sub == 'auto':
                self.cfg.set_lot('auto')
                self.send("✅ Mode lot: <b>Auto</b> (risk-based).", reply_markup=self._menu_inline())
            elif sub == 'manual':
                m = self.cfg.manual_lot()
                self.cfg.set_lot('manual', m)
                self.send("✅ Mode lot: <b>Manual</b> (tetap).", reply_markup=self._menu_inline())
            elif sub.startswith('set:'):
                try:
                    v = float(sub.split(':', 1)[1])
                    if v <= 0:
                        self.send("⚠️ Lot harus > 0.")
                        return False
                    self.cfg.set_lot('manual', v)
                    self.send(f"✅ Lot manual: <b>{v}</b>", reply_markup=self._menu_inline())
                except (ValueError, IndexError):
                    self.send("⚠️ Format: /lot 0.05")
            return False
        if cmd.startswith('lot '):
            # /lot 0.05 — set lot manual langsung
            try:
                v = float(cmd.split(' ', 1)[1])
                if v <= 0:
                    self.send("⚠️ Lot harus > 0.")
                    return False
                self.cfg.set_lot('manual', v)
                self.send(f"✅ Mode lot: <b>Manual</b> — lot <b>{v}</b>", reply_markup=self._menu_inline())
            except (ValueError, IndexError):
                self.send("⚠️ Format: /lot 0.05")
            return False

        is_menu = cmd in ('start', 'menu', 'bantuan')
        text, inline = self.build_reply(cmd, account, positions, pending, signals, daily)
        if text:
            rk = self._reply_keyboard() if is_menu else None
            self.send(text, reply_markup=inline or rk)
        return cmd == 'stop'

    # ---------------------------------------------------------------
    # reply builder
    # ---------------------------------------------------------------
    def build_reply(self, cmd: str, account: dict, positions: list,
                    pending: list, signals: list, daily: dict = None) -> tuple:
        """Return (text, inline_keyboard_or_None)."""
        cmd = (cmd or '').strip().lower()
        if cmd in ('start', 'menu'):
            return self._menu_text(account), self._menu_inline()
        if cmd == 'status':
            return self._status_text(account, positions, pending), self._menu_inline()
        if cmd == 'pnl':
            dp = (daily or {}).get('realized_today')
            sb = (daily or {}).get('start_balance')
            return self._pnl_text(account, positions, pending, dp, sb), self._menu_inline()
        if cmd == 'posisi':
            return self._positions_text(positions, pending), self._menu_inline()
        if cmd == 'sinyal':
            return self._signals_text(signals), self._menu_inline()
        if cmd == 'setting':
            return self._setting_text(), self._menu_inline()
        if cmd == 'bantuan':
            return self._bantuan_text(), self._menu_inline()
        if cmd == 'pilihpair':
            return self._pilihpair_text(), self._pilihpair_inline()
        if cmd == 'stop':
            return "🛑 Menghentikan bot...", None
        return "", None

    # ---------------------------------------------------------------
    # teks balasan
    # ---------------------------------------------------------------
    def _menu_text(self, account):
        return (f"🤖 <b>MT5 Automation Trading</b>\n"
                f"Akun: {account.get('login')} ({account.get('company', '')})\n\n"
                f"Pilih menu di bawah 👇\n"
                f"(atau ketik perintah: /status /pnl /posisi /sinyal /setting /bantuan /stop)")

    def _status_text(self, account, positions, pending):
        bal = account.get('balance', 0)
        eq = account.get('equity', 0)
        free = account.get('free_margin', 0)
        fl = eq - bal
        return (f"🤖 <b>Status Bot</b>\n"
                f"├ Akun: {account.get('login')} ({account.get('company', '')})\n"
                f"├ Balance: ${bal:.2f}\n"
                f"├ Equity: ${eq:.2f}\n"
                f"├ Floating: ${fl:+.2f}\n"
                f"├ Free margin: ${free:.2f}\n"
                f"├ Posisi terbuka: {len(positions)}\n"
                f"└ Pending order: {len(pending)}")

    def _pnl_text(self, account, positions, pending, daily_pnl=None, daily_start=None):
        bal = account.get('balance', 0)
        eq = account.get('equity', 0)
        fl = eq - bal
        txt = (f"📈 <b>Laporan PnL</b>\n"
               f"├ Balance: ${bal:.2f}\n"
               f"├ Equity: ${eq:.2f}\n"
               f"├ Floating PnL: ${fl:+.2f}")
        if daily_pnl is not None:
            txt += f"\n├ PnL Hari Ini: ${daily_pnl:+.2f}"
        if daily_start is not None:
            txt += f"\n├ Balance Awal Hari: ${daily_start:.2f}"
        txt += f"\n└ Free Margin: ${account.get('free_margin', 0):.2f}"
        if positions:
            txt += "\n\n<b>Posisi:</b>"
            for p in positions:
                txt += (f"\n├ {p.get('type')} {p.get('symbol')} {p.get('volume')}"
                        f" @ {p.get('price_open')} → ${p.get('profit', 0):+.2f}")
        else:
            txt += "\n\nTidak ada posisi terbuka."
        return txt

    def _positions_text(self, positions, pending):
        txt = ""
        if positions:
            txt = "<b>📌 Posisi terbuka:</b>"
            for p in positions:
                txt += (f"\n├ {p.get('type')} {p.get('symbol')} {p.get('volume')}"
                        f" entry={p.get('price_open')} sl={p.get('sl')} tp={p.get('tp')}"
                        f" → ${p.get('profit', 0):+.2f}")
        else:
            txt = "<b>📌 Posisi terbuka:</b>\n└ Tidak ada"
        if pending:
            txt += "\n\n<b>Pending order:</b>"
            for p in pending:
                txt += f"\n├ {p.get('type', '?')} {p.get('symbol')} @ {p.get('price_open')}"
        else:
            txt += "\n\n<b>Pending order:</b>\n└ Tidak ada"
        return txt

    def _signals_text(self, signals):
        if not signals:
            return "🧠 <b>Sinyal AI</b>\n└ Belum ada sinyal tercatat."
        txt = "🧠 <b>Sinyal AI terakhir:</b>"
        for s in signals[-10:]:
            txt += (f"\n├ {s.get('time', '')} {s.get('symbol')} → "
                    f"{s.get('decision')} ({s.get('strategy', '')}, conf {s.get('confidence', 0):.0%})")
        return txt

    def _setting_text(self):
        cfg = self.cfg
        pairs = cfg.get(['mt5', 'symbols'], []) or []
        return (f"⚙️ <b>Pengaturan Bot</b>\n"
                f"├ Model AI: {cfg.provider_model()}\n"
                f"├ Strategi: {cfg.strategy_name()}\n"
                f"├ Pair: {', '.join(pairs)}\n"
                f"├ Risk per trade: {cfg.risk_percent()*100:.1f}%\n"
                f"├ RR minimal: 1:{cfg.get(['execution', 'min_risk_reward'], 1.5)}\n"
                f"├ Max lot: {cfg.get(['execution', 'max_lots_per_trade'], 0.5)}\n"
                f"└ Max posisi/symbol: {cfg.max_positions_per_symbol()}")

    def _bantuan_text(self):
        return (f"ℹ️ <b>Bantuan</b>\n\n"
                f"<b>Command:</b>\n"
                f"/status — ringkasan akun & posisi\n"
                f"/pnl — laporan profit/loss\n"
                f"/posisi — daftar posisi & pending\n"
                f"/sinyal — sinyal AI terakhir\n"
                f"/pilihpair — pilih pair yang di-scan\n"
                f"/setting — konfigurasi bot\n"
                f"/menu — tampilkan menu\n"
                f"/stop — hentikan bot\n\n"
                f"Gunakan tombol di bawah untuk navigasi cepat.")

    # ---------------------------------------------------------------
    # pilih pair aktif
    # ---------------------------------------------------------------
    def _pilihpair_text(self, draft: set = None):
        if draft is None:
            draft = set(s.upper() for s in self.cfg.active_pairs())
        if draft:
            txt = (f"🎯 <b>Pilih Pair Aktif</b>\n"
                   f"├ Aktif sekarang: <b>{', '.join(sorted(draft))}</b>\n"
                   f"└ Tap pair untuk ON/OFF. Simpan jika selesai.")
        else:
            txt = (f"🎯 <b>Pilih Pair Aktif</b>\n"
                   f"├ Aktif sekarang: <b>SEMUA pair</b>\n"
                   f"└ Tap pair untuk ON/OFF. Simpan jika selesai.")
        return txt

    def _pilihpair_inline(self, draft: set = None):
        if draft is None:
            draft = set(s.upper() for s in self.cfg.active_pairs())
        all_pairs = self.cfg.get(['mt5', 'symbols'], []) or []
        rows = []
        row = []
        for sym in all_pairs:
            mark = "✅" if sym.upper() in draft else "⬜"
            row.append({"text": f"{mark} {sym}", "callback_data": f"pair:{sym}"})
            if len(row) == 2:
                rows.append(row)
                row = []
        if row:
            rows.append(row)
        rows.append([
            {"text": "💾 Simpan", "callback_data": "pair_save"},
            {"text": "❌ Batal", "callback_data": "pair_cancel"},
        ])
        rows.append([{"text": "« Menu", "callback_data": "menu"}])
        return {"inline_keyboard": rows}

    # ---------------------------------------------------------------
    # lot mode (auto | manual)
    # ---------------------------------------------------------------
    def _lot_text(self, mode: str, manual: float) -> str:
        mode_txt = ("Auto — risk-based, menyesuaikan balance & jarak SL"
                    if mode == 'auto' else f"Manual — lot tetap {manual}")
        return (f"🔢 <b>Mode Lot</b>\n"
                f"├ Mode saat ini: <b>{mode_txt}</b>\n"
                f"├ Risk/trade: {self.cfg.risk_percent()*100:.1f}% (saat auto)\n"
                f"└ Max lot: {self.cfg.get(['execution', 'max_lots_per_trade'], 0.5)}\n\n"
                f"Pilih mode di bawah, atau ketik /lot 0.05 untuk set manual.")

    def _lot_inline(self, mode: str) -> dict:
        mark_a = "✅" if mode == 'auto' else "⬜"
        mark_m = "✅" if mode == 'manual' else "⬜"
        manual = self.cfg.manual_lot()
        rows = [
            [{"text": f"{mark_a} Auto (menyesuaikan market)", "callback_data": "lot:auto"}],
            [{"text": f"{mark_m} Manual (lot tetap {manual})", "callback_data": "lot:manual"}],
        ]
        # preset lot cepat
        presets = [0.01, 0.02, 0.05, 0.10]
        row = []
        for v in presets:
            row.append({"text": f"{v}", "callback_data": f"lot:set:{v}"})
            if len(row) == 4:
                rows.append(row)
                row = []
        if row:
            rows.append(row)
        rows.append([{"text": "« Menu", "callback_data": "menu"}])
        return {"inline_keyboard": rows}

    # ---------------------------------------------------------------
    # notifikasi trade (bahasa Indonesia)
    # ---------------------------------------------------------------
    def notify_trade(self, action: dict) -> None:
        if not self.enabled:
            return
        symbol = action.get('symbol', '?')
        act = action.get('action', '?')
        dec = action.get('decision', {})
        order_type = action.get('order_type', dec.get('decision', ''))
        strat = dec.get('strategy', '')
        reason = dec.get('reason', '')
        conf = dec.get('confidence', 0)

        if act == 'EXECUTED':
            msg = (f"✅ <b>{order_type} {symbol}</b>\n"
                   f"├ Lot: {action.get('lots', 0)}\n"
                   f"├ Entry: {action.get('entry', 0)}\n"
                   f"├ SL: {action.get('sl', 0)} | TP: {action.get('tp', 0)}\n"
                   f"├ Confidence: {conf:.0%} | Strategi: {strat}")
            if reason:
                msg += f"\n└ <i>Alasan: {reason[:220]}</i>"

        elif act == 'FAILED':
            msg = (f"❌ <b>Order gagal: {order_type} {symbol}</b>\n"
                   f"└ {action.get('message', '')}")

        elif act == 'RISK_BLOCK':
            msg = (f"🚫 <b>Ditolak risk: {symbol}</b>\n"
                   f"└ {action.get('reason', '')}")

        elif act == 'CLOSE':
            msg = f"🔒 <b>Tutup {symbol}</b>\n"
            for r in action.get('results', []):
                status = 'OK' if r.get('ok') else f"GAGAL {r.get('msg','')}"
                msg += f"├ t{r.get('ticket')}: {status}\n"
            msg = msg.rstrip('\n')
        else:
            msg = f"ℹ️ {act} {symbol}"

        self.send(msg)

    def notify_pnl(self, account: dict, positions: list, pending: list,
                   daily_pnl: float = None, day_start: float = None) -> None:
        if not self.enabled:
            return
        self.send(self._pnl_text(account, positions, pending, daily_pnl, day_start))

    def notify_status(self, account: dict) -> None:
        if not self.enabled:
            return
        self.send(self._status_text(account, [], []))

    def notify_error(self, symbol: str, err: str) -> None:
        if not self.enabled:
            return
        self.send(f"⚠️ <b>Error {symbol}</b>\n└ {err[:200]}")
