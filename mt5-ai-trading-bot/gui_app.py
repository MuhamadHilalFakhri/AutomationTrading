"""MT5 AI Trading Bot — GUI Launcher (all-in-one, single EXE).

Semua konfigurasi via form (input + dropdown + checkbox), tanpa edit config.yaml manual.
Bot dijalankan IN-PROCESS (bukan subprocess) sehingga bisa dibungkus PyInstaller:

    pyinstaller --onefile --windowed --name MT5TradingBot --paths server ^
        --hidden-import config --hidden-import mt5_gateway --hidden-import engine ^
        --hidden-import notifier --hidden-import risk_guard --hidden-import trade_manager ^
        --hidden-import logger_setup --hidden-import ai.agent --hidden-import ai.chart_renderer ^
        --hidden-import ai.prompts --collect-all MetaTrader5 gui_app.py

Atau jalankan build_exe.bat. EXE membaca/menulis config.yaml di folder EXE berada.
Self-test headless:  MT5TradingBot.exe --selftest  (hasil -> _selftest.txt)
"""
import json
import os
import sys
import threading
import time
import traceback
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext


# ── paths (frozen-safe) ────────────────────────────────────────────
def _app_root() -> str:
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


ROOT = _app_root()
os.chdir(ROOT)                      # relative paths (custom.txt dll) resolve ke folder exe
SERVER_DIR = os.path.join(ROOT, 'server')
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

# windowed exe: stdout/stderr bisa None -> print() aman
if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w', encoding='utf-8')
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w', encoding='utf-8')

CONFIG_PATH = os.path.join(ROOT, 'config.yaml')
CONFIG_BAK = CONFIG_PATH + '.bak'
ACTIVE_PAIRS_FILE = os.path.join(ROOT, '.active_pairs.json')
LOG_PATH = os.path.join(ROOT, 'logs', 'engine.log')

# ── default config scaffold (nilai = setup Hilal) ──────────────────
DEFAULT_CONFIG = {
    'mt5': {
        'terminal_path': 'C:/Program Files/MetaTrader 5/terminal64.exe',
        'symbols': ['XAUUSD', 'EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'NAS100.r'],
        'max_symbols': 12,
    },
    'provider': {
        'base_url': 'http://localhost:20128/v1',
        'api_key_env': 'HERMES_CUSTOM_LOCALHOST_20128_API_KEY',
        'api_key': '',
        'model': 'COMBO',
        'temperature': 0.1,
        'max_tokens': 4096,
        'timeout_sec': 120,
        'vision': {'enabled': True, 'chart_candles': 120, 'chart_timeframe': 'M5',
                   'chart_width': 1400, 'chart_height': 800, 'indicators_overlay': True},
    },
    'strategy': {
        'name': 'adaptive',
        'timeframes': ['M5', 'M15', 'M30', 'H1', 'H4'],
        'default_timeframes': ['M5', 'M15', 'H1'],
        'symbol_timeframes': {'XAUUSD': ['M5', 'M15', 'M30', 'H1', 'H4']},
        'custom_prompt_file': 'custom.txt',
        'data_mode': 'compact',
        'compact_tail_last_n': 40,
        'compact_tail_tf': 'M5',
    },
    'execution': {
        'min_conf_for_entry': 0.55,
        'max_spread_points': 50,
        'max_spread_overrides': {'NAS100.r': 'unlimited'},
        'pending_max_distance_overrides': {'NAS100.r': 'unlimited'},
        'cooldown_minutes': 3,
        'magic_number': 20250903,
        'slippage_points': 20,
        'risk_mode': 'percent',
        'risk_percent': 0.01,
        'fixed_lots': 0.01,
        'min_risk_reward': 1.5,
        'max_lots_per_trade': 0.5,
        'lot_mode': 'auto',
        'manual_lot': 0.01,
        'min_sl_points': 50,
        'max_open_positions_per_symbol': 5,
        'max_correlated_positions': 2,
        'rr_by_symbol': {
            'XAUUSD': {'min_rr': 2.0, 'target_pips_min': 100, 'target_pips_max': 400},
            'NAS100.r': {'min_rr': 2.0, 'target_pips_min': 150, 'target_pips_max': 500},
            'EURUSD': {'min_rr': 1.5, 'target_pips_min': 40, 'target_pips_max': 150},
            'GBPUSD': {'min_rr': 1.5, 'target_pips_min': 40, 'target_pips_max': 150},
            'USDJPY': {'min_rr': 1.5, 'target_pips_min': 40, 'target_pips_max': 150},
            'AUDUSD': {'min_rr': 1.5, 'target_pips_min': 35, 'target_pips_max': 140},
        },
        'max_daily_loss_percent': 5.0,
        'allowed_order_types': ['market', 'pending'],
        'pending_max_distance_points': 5000,
        'min_sl_points': 10, 'max_sl_points': 20000,
        'min_tp_points': 10, 'max_tp_points': 40000,
        'time_filter': {'timezone': 'Asia/Jakarta', 'block_ranges': []},
    },
    'trade_management': {
        'enabled': True, 'use_bep': True, 'bep_aggressive': True,
        'bep_trigger_points': 30, 'bep_lock_points': 5,
        'use_trailing': True, 'trailing_start_points': 100, 'trailing_step_points': 20,
        'evaluate_positions': True, 'position_eval_interval_min': 15,
        'partial_tp_enabled': False, 'partial_tp_trigger_fraction': 0.5,
        'partial_tp_close_fraction': 0.5,
    },
    'telegram': {
        'enabled': True, 'token_env': 'TELEGRAM_BOT_TOKEN',
        'chat_id_env': 'TELEGRAM_CHAT_ID',
        'bot_token': '', 'chat_id': '',
        'send_charts': {'enabled': True, 'symbols': ['XAUUSD']},
    },
    'server': {'host': '127.0.0.1', 'port': 8790, 'api_key_env': 'MT5AI_API_KEY'},
    'app': {'loop_interval_sec': 60},
}

ALL_PAIRS = ['XAUUSD', 'EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'NAS100.r']
ALL_TFS = ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1']
MODELS = ['COMBO', 'h1', 'gpt-4o', 'claude-sonnet-4', 'claude-3.5-haiku', 'deepseek-v3']
STRATEGIES = ['adaptive', 'scalping', 'snd', 'trend', 'custom']


# ── config load/save ───────────────────────────────────────────────
def _load_cfg() -> dict:
    if not os.path.exists(CONFIG_PATH):
        return json.loads(json.dumps(DEFAULT_CONFIG))   # deep copy
    try:
        import yaml
        with open(CONFIG_PATH, encoding='utf-8') as f:
            d = yaml.safe_load(f) or {}
        return d
    except Exception as e:
        print(f'[gui] config.yaml rusak ({e}); pakai default. Backup dulu jika ada.')
        return json.loads(json.dumps(DEFAULT_CONFIG))


def _save_cfg(cfg: dict):
    import yaml
    if os.path.exists(CONFIG_PATH):
        os.replace(CONFIG_PATH, CONFIG_BAK)
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


# ── bot runner (in-process, thread) ────────────────────────────────
class BotRunner:
    """Jalankan BotEngine di background thread — pengganti subprocess run_bot.py."""

    def __init__(self, gui):
        self.gui = gui
        self.engine = None
        self.gw = None
        self.thread = None
        self._stop_evt = threading.Event()

    def is_alive(self) -> bool:
        return bool(self.thread and self.thread.is_alive())

    def start(self, interval: float):
        self._stop_evt.clear()
        self.thread = threading.Thread(
            target=self._run, args=(interval,), daemon=True, name='bot-engine')
        self.thread.start()

    def stop(self):
        self._stop_evt.set()
        if self.engine:
            try:
                self.engine.stop()
            except Exception:
                pass

    def detach(self):
        """Lepas referensi engine — thread daemon dibiarkan mati sendiri."""
        try:
            if self.engine:
                self.engine.stop()
        except Exception:
            pass
        self.thread = None

    def _run(self, interval: float):
        g = self.gui
        try:
            from config import Config
            from mt5_gateway import MT5Gateway
            from ai.agent import AIAgent
            from ai.chart_renderer import ChartRenderer
            from risk_guard import RiskGuard
            from trade_manager import TradeManager
            from engine import BotEngine
            from notifier import TelegramNotifier
            from logger_setup import setup_logger

            setup_logger('engine')
            g._log('⚙️ Memuat modul & konfigurasi...\n')
            cfg = Config(CONFIG_PATH)

            gw = MT5Gateway(cfg)
            if not gw.connect():
                g._log('❌ FATAL: tidak bisa konek MT5. Cek path terminal di tab Koneksi, '
                       'pastikan MT5 terbuka & sudah login.\n')
                g._status('error')
                return
            self.gw = gw
            g._log('✅ MT5 terhubung.\n')
            if self._stop_evt.is_set():
                g._log('⏹ Stop diminta saat startup — bot tidak dilanjutkan.\n')
                g._status('stopped')
                return

            renderer = ChartRenderer(
                width=int(cfg.get(['provider', 'vision', 'chart_width'], 1400)),
                height=int(cfg.get(['provider', 'vision', 'chart_height'], 800)),
                overlay=bool(cfg.get(['provider', 'vision', 'indicators_overlay'], True)),
                session_id=f"MT5AI-{cfg.magic_number()}",
            )
            ai = AIAgent(cfg)
            risk = RiskGuard(cfg, gw)
            tm = TradeManager(cfg, gw)
            notifier = TelegramNotifier(cfg)
            eng = BotEngine(cfg, gw, ai, risk, tm, chart_renderer=None, notifier=notifier)

            def render_for_ai(symbol, tf, n):
                d = gw.fetch_ohlcv(symbol, tf, n)
                if not d:
                    return None
                return renderer.render(symbol, tf, d)

            ai.chart_renderer = render_for_ai
            self.engine = eng
            g._log(f'▶ Bot loop jalan — scan tiap {interval:.0f}s. '
                   f'Menu Telegram aktif di background.\n')
            g._status('running')
            eng.run(loop_interval_sec=interval)
        except Exception as e:
            g._log(f'❌ Bot error: {e}\n{"".join(traceback.format_exc(limit=3))}\n')
            g._status('error')
        finally:
            try:
                if self.engine:
                    self.engine.stop()
            except Exception:
                pass
            try:
                if self.gw:
                    self.gw.shutdown()
            except Exception:
                pass
            self.engine = None
            self.gw = None
            g._status('stopped')
            g._log('⏸ Bot berhenti.\n')


# ── main GUI ───────────────────────────────────────────────────────
class BotGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title('AI Trading Bot — Control Panel')
        self.root.geometry('1020x800')
        self.root.minsize(880, 660)
        self._set_window_icon()
        self._setup_style()
        self.cfg = _load_cfg()
        # prefill API key dari env jika config kosong
        if not self._deep_get(self.cfg, ['provider', 'api_key'], ''):
            env_name = self._deep_get(self.cfg, ['provider', 'api_key_env'], '') or ''
            self._deep_set(self.cfg, ['provider', 'api_key'], os.environ.get(env_name, ''))
        self.runner = BotRunner(self)
        self._ui_state = 'stopped'
        self._pending_restart = False
        self._fields = []
        self._log_pos = os.path.getsize(LOG_PATH) if os.path.exists(LOG_PATH) else 0
        self._build_ui()
        self.root.protocol('WM_DELETE_WINDOW', self._on_close)
        self._poll()

    # ── icon window ────────────────────────────────────────────────
    def _set_window_icon(self):
        try:
            if getattr(sys, 'frozen', False):
                base = getattr(sys, '_MEIPASS', ROOT)
                cands = [os.path.join(base, 'assets', 'logo.png'),
                         os.path.join(base, 'assets', 'icon.ico')]
            else:
                cands = [os.path.join(ROOT, 'assets', 'logo.png'),
                         os.path.join(ROOT, 'assets', 'icon.ico')]
            for c in cands:
                if os.path.exists(c):
                    if c.endswith('.png'):
                        img = tk.PhotoImage(file=c)
                        self.root.iconphoto(True, img)
                        self._icon_ref = img   # simpan referensi biar tidak di-GC
                    else:
                        self.root.iconbitmap(c)
                    break
        except Exception:
            pass

    # ── style ──────────────────────────────────────────────────────
    def _setup_style(self):
        st = ttk.Style(self.root)
        try:
            st.theme_use('clam')
        except Exception:
            pass
        bg = '#0e1117'
        panel = '#161b24'
        field = '#1c2430'
        fg = '#e6e6e6'
        dim = '#9aa4b2'
        accent = '#2f81f7'
        self.root.configure(bg=bg)
        st.configure('.', background=bg, foreground=fg, fieldbackground=field,
                     bordercolor='#2a3442', lightcolor=bg, darkcolor=bg,
                     focuscolor=accent, font=('Segoe UI', 9))
        st.configure('TFrame', background=bg)
        st.configure('Panel.TFrame', background=panel)
        st.configure('TLabel', background=bg, foreground=fg)
        st.configure('Dim.TLabel', background=bg, foreground=dim)
        st.configure('Header.TLabel', background=bg, foreground='#ffffff',
                     font=('Segoe UI', 13, 'bold'))
        st.configure('Sub.TLabel', background=bg, foreground=dim,
                     font=('Segoe UI', 9))
        st.configure('TLabelframe', background=bg, bordercolor='#2a3442',
                     foreground='#c9d4e3', relief='solid')
        st.configure('TLabelframe.Label', background=bg, foreground='#c9d4e3',
                     font=('Segoe UI', 9, 'bold'))
        st.configure('TNotebook', background=bg, bordercolor='#2a3442')
        st.configure('TNotebook.Tab', background=panel, foreground=dim,
                     padding=(14, 6), font=('Segoe UI', 9))
        st.map('TNotebook.Tab', background=[('selected', '#1e2633')],
               foreground=[('selected', '#ffffff')])
        st.configure('TEntry', fieldbackground=field, foreground=fg,
                     insertcolor=fg, bordercolor='#2a3442')
        st.configure('TCombobox', fieldbackground=field, foreground=fg,
                     arrowcolor=fg, bordercolor='#2a3442')
        st.map('TCombobox', fieldbackground=[('readonly', field)])
        st.configure('TCheckbutton', background=bg, foreground=fg)
        st.map('TCheckbutton', background=[('active', bg)])
        st.configure('TButton', background=panel, foreground=fg,
                     bordercolor='#2a3442', padding=(10, 5),
                     font=('Segoe UI', 9, 'bold'))
        st.map('TButton', background=[('active', '#2a3442'), ('disabled', '#1a202b')],
               foreground=[('disabled', '#5b6675')])
        # tombol aksi berwarna
        st.configure('Start.TButton', background='#1a7f37', foreground='#ffffff')
        st.map('Start.TButton', background=[('active', '#238a42'), ('disabled', '#14321f')],
               foreground=[('disabled', '#7a8f80')])
        st.configure('Stop.TButton', background='#b01e28', foreground='#ffffff')
        st.map('Stop.TButton', background=[('active', '#c22b35'), ('disabled', '#3a1518')],
               foreground=[('disabled', '#a07074')])
        st.configure('Restart.TButton', background='#b06000', foreground='#ffffff')
        st.map('Restart.TButton', background=[('active', '#c57112'), ('disabled', '#3a2a12')],
               foreground=[('disabled', '#a08a62')])
        st.configure('Test.TButton', background=panel, foreground='#7cc4ff',
                     font=('Segoe UI', 9))
        st.map('Test.TButton', background=[('active', '#22303f'), ('disabled', '#1a202b')])
        st.configure('Save.TButton', background='#2f5d8a', foreground='#ffffff')
        st.map('Save.TButton', background=[('active', '#3a6ea0'), ('disabled', '#1e2f40')],
               foreground=[('disabled', '#6d7f92')])
        st.configure('Accent.TButton', background='#1d4f8a', foreground='#ffffff')
        st.map('Accent.TButton', background=[('active', '#265f9e')])
        st.configure('Status.TLabel', background=panel, foreground=fg,
                     font=('Consolas', 9), padding=(8, 4))
        st.configure('Acct.TLabel', background=bg, foreground='#7cc4ff',
                     font=('Consolas', 9, 'bold'))
        st.configure('Vertical.TSeparator', background='#2a3442')
        st.configure('Horizontal.TSeparator', background='#2a3442')

    # ── UI skeleton ────────────────────────────────────────────────
    def _build_ui(self):
        # header: logo + judul
        hdr = ttk.Frame(self.root, style='Header.TLabel')
        hdr.pack(fill='x', padx=14, pady=(12, 4))
        try:
            base = getattr(sys, '_MEIPASS', ROOT)
            logo_p = os.path.join(base, 'assets', 'logo.png')
            if os.path.exists(logo_p):
                self._logo_img = tk.PhotoImage(file=logo_p).subsample(6, 6)
                ttk.Label(hdr, image=self._logo_img).pack(side='left', padx=(0, 10))
        except Exception:
            pass
        ttl = ttk.Frame(hdr, style='Header.TLabel')
        ttl.pack(side='left')
        ttk.Label(ttl, text='AI TRADING BOT', style='Header.TLabel').pack(anchor='w')
        ttk.Label(ttl, text='MT5 + AI Vision (9Router) · Control Panel',
                  style='Sub.TLabel').pack(anchor='w')

        # toolbar
        ctrl = ttk.Frame(self.root)
        ctrl.pack(fill='x', padx=14, pady=(8, 2))
        self.btn_start = ttk.Button(ctrl, text='▶  Start Bot', style='Start.TButton',
                                    command=self._start_bot)
        self.btn_start.pack(side='left', padx=(0, 4))
        self.btn_stop = ttk.Button(ctrl, text='■  Stop Bot', style='Stop.TButton',
                                   command=self._stop_bot, state='disabled')
        self.btn_stop.pack(side='left', padx=4)
        self.btn_restart = ttk.Button(ctrl, text='🔄  Restart Bot', style='Restart.TButton',
                                      command=self._restart_bot, state='disabled')
        self.btn_restart.pack(side='left', padx=4)
        ttk.Separator(ctrl, orient='vertical').pack(side='left', fill='y', padx=8)
        ttk.Button(ctrl, text='💾  Simpan', style='Save.TButton',
                   command=self._save_clicked).pack(side='left', padx=4)
        ttk.Separator(ctrl, orient='vertical').pack(side='left', fill='y', padx=8)
        ttk.Button(ctrl, text='🔌 Test 9Router', style='Test.TButton',
                   command=self._test_router).pack(side='left', padx=4)
        ttk.Button(ctrl, text='🏛 Test MT5', style='Test.TButton',
                   command=self._test_mt5).pack(side='left', padx=4)
        ttk.Button(ctrl, text='📱 Test Telegram', style='Test.TButton',
                   command=self._test_tg).pack(side='left', padx=4)
        self.lbl_state = ttk.Label(ctrl, text='⏸ STOPPED', foreground='#9aa4b2',
                                   font=('Segoe UI', 10, 'bold'))
        self.lbl_state.pack(side='right', padx=6)

        nb = ttk.Notebook(self.root)
        nb.pack(fill='both', expand=True, padx=8, pady=4)
        self._tab_terminal(nb)
        self._tab_connection(nb)
        self._tab_symbols(nb)
        self._tab_risk(nb)
        self._tab_perpair(nb)
        self._tab_telegram(nb)
        self._tab_trademgmt(nb)
        self._tab_advanced(nb)

        # status akun (live)
        stat = ttk.Frame(self.root)
        stat.pack(fill='x', padx=14, pady=(0, 6))
        self.var_acct = ttk.Label(stat, text='MT5: —', style='Acct.TLabel')
        self.var_acct.pack(side='left')

    def _tab_terminal(self, nb):
        """Terminal/output bot sebagai halaman penuh (bukan kotak kecil di bawah)."""
        f = ttk.Frame(nb)
        nb.add(f, text=' 🖥 Terminal ')
        bar = ttk.Frame(f)
        bar.pack(fill='x', padx=8, pady=(8, 0))
        ttk.Button(bar, text='🗑 Bersihkan', style='Test.TButton',
                   command=lambda: self.log.delete('1.0', 'end')).pack(side='left')
        ttk.Button(bar, text='📋 Salin Semua', style='Test.TButton',
                   command=self._copy_log).pack(side='left', padx=6)
        self.log = scrolledtext.ScrolledText(f, bg='#0a0d12', fg='#c8d3e0',
                                             insertbackground='#c8d3e0',
                                             font=('Consolas', 10), wrap='word',
                                             relief='flat', highlightthickness=1,
                                             highlightbackground='#2a3442',
                                             highlightcolor='#2a3442')
        self.log.pack(fill='both', expand=True, padx=8, pady=(6, 8))
        self.log.tag_config('ok', foreground='#3fb950')
        self.log.tag_config('err', foreground='#f85149')
        self.log.tag_config('warn', foreground='#d29922')
        self.log.tag_config('info', foreground='#58a6ff')
        self.log.insert('end', '▶ Terminal siap. Start Bot untuk mulai memantau '
                               'aktivitas (log & menu Telegram jalan di background).\n')
        self.log.see('end')

    def _copy_log(self):
        txt = self.log.get('1.0', 'end')
        self.root.clipboard_clear()
        self.root.clipboard_append(txt)
        self._log('📋 Log disalin ke clipboard.\n')

    # ── tabs ───────────────────────────────────────────────────────
    def _tab_connection(self, nb):
        f = ttk.Frame(nb)
        nb.add(f, text=' 🔌 Koneksi ')
        p = self.cfg.setdefault('provider', {})
        v = p.setdefault('vision', {})
        self._pair_field(f, 'MT5 Terminal Path:', self.cfg, ['mt5', 'terminal_path'], row=0, width=52)
        self._pair_field(f, '9Router URL:', p, ['base_url'], row=1, width=40)
        self._pair_field(f, 'API Key (9Router):', p, ['api_key'], row=2, width=40, show='•')
        self._pair_field(f, 'API Key Env Var:', p, ['api_key_env'], row=3, width=40)
        self._pair_combo(f, 'Model AI:', p, ['model'], MODELS, row=4, editable=True)
        self._pair_combo(f, 'Strategi:', self.cfg.setdefault('strategy', {}), ['name'],
                         STRATEGIES, row=5, editable=True)
        self._pair_field(f, 'Custom Prompt File:', self.cfg['strategy'], ['custom_prompt_file'], row=6)
        self._pair_field(f, 'Temperature:', p, ['temperature'], row=7)
        self._pair_field(f, 'Timeout (detik):', p, ['timeout_sec'], row=8)
        self._pair_field(f, 'Max Tokens:', p, ['max_tokens'], row=9)
        ttk.Separator(f, orient='horizontal').grid(row=10, column=0, columnspan=3,
                                                   sticky='ew', padx=8, pady=6)
        ttk.Label(f, text='Vision (chart PNG ke AI):', font=('', 9, 'bold')).grid(
            row=11, column=0, sticky='e', padx=8)
        self._pair_check(f, 'Aktif', v, ['enabled'], row=12)
        self._pair_field(f, 'Jumlah Candle:', v, ['chart_candles'], row=13)
        self._pair_combo(f, 'Chart TF:', v, ['chart_timeframe'],
                         ['M1', 'M5', 'M15', 'M30', 'H1', 'H4'], row=14)
        self._pair_field(f, 'Lebar px:', v, ['chart_width'], row=15)
        self._pair_field(f, 'Tinggi px:', v, ['chart_height'], row=16)
        self._pair_check(f, 'Overlay indikator', v, ['indicators_overlay'], row=17)
        # scan interval
        self._pair_field(f, 'Scan Interval (detik):', self.cfg.setdefault('app', {}),
                         ['loop_interval_sec'], row=18)
        ttk.Button(f, text='🔍 Deteksi Otomatis (MT5 path + nama pair broker)',
                   style='Test.TButton', command=self._auto_detect).grid(
            row=19, column=0, columnspan=3, sticky='w', padx=8, pady=(10, 2))

    def _auto_detect(self):
        """Cari terminal64.exe + nama symbol asli broker, isi otomatis ke config."""
        # feedback segera — jangan biarkan user mengira tombol mati
        self._log('🔍 Deteksi otomatis dimulai — mencari MT5… (beberapa detik)\n')
        class _DictCfg:
            """Shim: dict GUI -> objek cfg ala Config (get dotted-path)."""
            def __init__(self, d): self._d = d
            def get(self, keys, default=None):
                o = self._d
                for k in keys:
                    if isinstance(o, dict) and k in o:
                        o = o[k]
                    else:
                        return default
                return o

        def run():
            try:
                from mt5_gateway import MT5Gateway
                probe = MT5Gateway(_DictCfg(self.cfg))
                p = probe.detect_terminal_path()
            except Exception as e:
                self._log(f'⚠ Gagal deteksi path: {e}\n')
                p = ''
            if p:
                cur = str(self._deep_get(self.cfg, ['mt5', 'terminal_path'], '') or '')
                if cur.strip().lower() != p.lower():
                    self._deep_set(self.cfg, ['mt5', 'terminal_path'], p)
                    # update juga field GUI-nya supaya terlihat
                    for obj, keys, var, _k in self._fields:
                        if keys == ['mt5', 'terminal_path']:
                            self.root.after(0, lambda v=var: v.set(p))
                    self._log(f'🔍 MT5 ditemukan otomatis: {p}\n')
                else:
                    self._log(f'🔍 MT5 path sudah benar: {p}\n')
            else:
                self._log('⚠ MT5 tidak ditemukan — set path manual.\n')
            # deteksi nama pair asli broker (butuh MT5 terkoneksi)
            import MetaTrader5 as mt5
            path = str(self._deep_get(self.cfg, ['mt5', 'terminal_path'], '') or '')
            ok = mt5.initialize(path) if path else mt5.initialize()
            if not ok:
                self._log(f'❌ MT5 initialize gagal: {mt5.last_error()}\n')
                return
            try:
                gw = MT5Gateway(_DictCfg(self.cfg))
                syms = gw.detect_broker_symbols(limit=15)
                if syms:
                    self._detected_pairs = syms
                    extra = ', '.join(syms)
                    self.root.after(0, lambda: self._extra_sym_var.set(extra))
                    self._log(f'🔍 {len(syms)} pair broker terdeteksi:\n   {extra}\n')
                    self._log('   → dicentangkan otomatis di tab "Symbol & TF" '
                              '(pair tambahan). Simpan agar dipakai bot.\n')
                    # centang otomatis pair yang terdeteksi di bagian universe
                    for s, var in list(self._sym_vars.items()):
                        if s in syms:
                            self.root.after(0, lambda v=var: v.set(True))
                        else:
                            self.root.after(0, lambda v=var: v.set(False))
                else:
                    self._log('⚠ Tidak ada pair terdeteksi (cek koneksi MT5 & '
                              'visibility symbol).\n')
            except Exception as e:
                self._log(f'❌ Gagal deteksi pair: {e}\n')
            finally:
                try:
                    mt5.shutdown()
                except Exception:
                    pass
        threading.Thread(target=run, daemon=True).start()

    def _tab_symbols(self, nb):
        f = ttk.Frame(nb)
        nb.add(f, text=' 📊 Symbol & TF ')
        s = self.cfg.setdefault('mt5', {})
        st = self.cfg.setdefault('strategy', {})
        ttk.Label(f, text='Pair yang diizinkan (universe):', font=('', 9, 'bold')).grid(
            row=0, column=0, columnspan=3, sticky='w', padx=8, pady=(6, 2))
        self._sym_vars = {}
        active = set(s.get('symbols', ALL_PAIRS) or [])
        for i, sym in enumerate(ALL_PAIRS):
            var = tk.BooleanVar(value=sym in active)
            self._sym_vars[sym] = var
            self._centang(f, sym, var).grid(
                row=1 + i // 3, column=i % 3, sticky='w', padx=16, pady=2)
        ttk.Label(f, text='Pair tambahan (pisah koma):').grid(row=2, column=0, sticky='e', padx=8)
        extra = [x for x in active if x not in ALL_PAIRS]
        self._extra_sym_var = tk.StringVar(value=', '.join(extra))
        ttk.Entry(f, textvariable=self._extra_sym_var, width=34).grid(
            row=2, column=1, columnspan=2, sticky='w', padx=4)

        ttk.Label(f, text='Pair aktif di-scan (subset; kosong = semua):',
                  font=('', 9, 'bold')).grid(row=3, column=0, columnspan=3, sticky='w',
                                             padx=8, pady=(10, 2))
        try:
            with open(ACTIVE_PAIRS_FILE) as fh:
                act = set(json.load(fh) or [])
        except Exception:
            act = set()
        self._active_vars = {}
        for i, sym in enumerate(ALL_PAIRS):
            var = tk.BooleanVar(value=sym in act)
            self._active_vars[sym] = var
            self._centang(f, sym, var).grid(
                row=4 + i // 3, column=i % 3, sticky='w', padx=16, pady=2)

        ttk.Label(f, text='Timeframes analisis:', font=('', 9, 'bold')).grid(
            row=6, column=0, columnspan=3, sticky='w', padx=8, pady=(10, 2))
        self._tf_vars = {}
        tfs = set(st.get('timeframes', ['M5', 'M15', 'M30', 'H1', 'H4']) or [])
        for i, tf in enumerate(ALL_TFS):
            var = tk.BooleanVar(value=tf in tfs)
            self._tf_vars[tf] = var
            self._centang(f, tf, var).grid(row=7, column=i, sticky='w', padx=6)

        ttk.Label(f, text='Default TF (pair tanpa override):').grid(row=8, column=0,
                                                                    sticky='e', padx=8, pady=(8, 0))
        self._deftf_var = tk.StringVar(value=', '.join(st.get('default_timeframes',
                                                             ['M5', 'M15', 'H1']) or []))
        ttk.Entry(f, textvariable=self._deftf_var, width=26).grid(row=8, column=1,
                                                                  sticky='w', padx=4, pady=(8, 0))

        ttk.Label(f, text='XAUUSD override TF (konfirmasi big-TF):',
                  font=('', 9, 'bold')).grid(row=9, column=0, columnspan=3, sticky='w',
                                             padx=8, pady=(10, 2))
        self._xau_tf_vars = {}
        xau = set(st.get('symbol_timeframes', {}).get('XAUUSD', ['M5', 'M15', 'M30', 'H1', 'H4']) or [])
        for i, tf in enumerate(ALL_TFS):
            var = tk.BooleanVar(value=tf in xau)
            self._xau_tf_vars[tf] = var
            self._centang(f, tf, var).grid(row=10, column=i, sticky='w', padx=6)

        ttk.Label(f, text='Data mode:', font=('', 9, 'bold')).grid(
            row=11, column=0, columnspan=3, sticky='w', padx=8, pady=(10, 2))
        self._pair_combo(f, 'Mode:', st, ['data_mode'], ['compact', 'full'], row=12, editable=False)
        self._pair_field(f, 'Tail N candle:', st, ['compact_tail_last_n'], row=13)
        self._pair_combo(f, 'Tail TF:', st, ['compact_tail_tf'],
                         ['M1', 'M5', 'M15', 'M30', 'H1', 'H4'], row=14, editable=False)

    def _tab_risk(self, nb):
        f = ttk.Frame(nb)
        nb.add(f, text=' ⚖️ Risk ')
        e = self.cfg.setdefault('execution', {})
        rows = [
            ('Min Confidence (0-1):', 'min_conf_for_entry'),
            ('Risk per Trade (%):', 'risk_percent'),
            ('Risk Mode:', 'risk_mode'),
            ('Fixed Lots:', 'fixed_lots'),
            ('Manual Lot:', 'manual_lot'),
            ('Lot Mode:', 'lot_mode'),
            ('Min RR:', 'min_risk_reward'),
            ('Max Lot / Trade:', 'max_lots_per_trade'),
            ('Max Posisi / Symbol:', 'max_open_positions_per_symbol'),
            ('Max Posisi Korelasi:', 'max_correlated_positions'),
            ('Max Spread (points):', 'max_spread_points'),
            ('Max Daily Loss (%):', 'max_daily_loss_percent'),
            ('Cooldown (menit):', 'cooldown_minutes'),
        ]
        combos = {'risk_mode': (['percent', 'fixed'], False),
                  'lot_mode': (['auto', 'manual'], False)}
        for i, (label, key) in enumerate(rows):
            if key in combos:
                vals, ed = combos[key]
                self._pair_combo(f, label, e, [key], vals, row=i, editable=ed)
            else:
                self._pair_field(f, label, e, [key], row=i)

    def _tab_perpair(self, nb):
        f = ttk.Frame(nb)
        nb.add(f, text=' 🎯 Per-Pair (RR & Spread) ')
        e = self.cfg.setdefault('execution', {})
        rr = e.get('rr_by_symbol', {}) or {}
        sp = e.get('max_spread_overrides', {}) or {}
        pd_ = e.get('pending_max_distance_overrides', {}) or {}
        head = ('Pair', 'Min RR', 'Pips Min', 'Pips Max', 'Spread Cap', 'Pending Dist')
        widths = (10, 8, 8, 8, 12, 12)
        for c, (h, w) in enumerate(zip(head, widths)):
            ttk.Label(f, text=h, font=('', 9, 'bold')).grid(row=0, column=c, padx=6, pady=(8, 2))
        self._pair_entries = {}
        for r, sym in enumerate(ALL_PAIRS, start=1):
            info = rr.get(sym, {}) or {}
            ttk.Label(f, text=sym, font=('', 9, 'bold')).grid(row=r, column=0, sticky='w', padx=8)
            ents = {}
            defaults = {
                'min_rr': str(info.get('min_rr', '')),
                'pips_min': str(info.get('target_pips_min', '')),
                'pips_max': str(info.get('target_pips_max', '')),
                'spread': str(sp.get(sym, '')),
                'pdist': str(pd_.get(sym, '')),
            }
            for c, key in enumerate(['min_rr', 'pips_min', 'pips_max', 'spread', 'pdist'], start=1):
                var = tk.StringVar(value=defaults[key])
                ent = ttk.Entry(f, textvariable=var, width=widths[c])
                ent.grid(row=r, column=c, padx=6, pady=2)
                ents[key] = var
            self._pair_entries[sym] = ents
        ttk.Label(f, foreground='gray',
                  text="Spread Cap / Pending Dist: kosong = pakai global, 'unlimited' = bebas, "
                       "atau angka points.\nContoh: NAS100.r spread 'unlimited' karena index "
                       "spread-nya lebar.").grid(row=len(ALL_PAIRS) + 2, column=0,
                                                 columnspan=6, sticky='w', padx=8, pady=8)

    def _tab_telegram(self, nb):
        f = ttk.Frame(nb)
        nb.add(f, text=' 📱 Telegram ')
        t = self.cfg.setdefault('telegram', {})
        sc = t.setdefault('send_charts', {})
        self._pair_check(f, 'Aktifkan Telegram', t, ['enabled'], row=0)
        # token: masked + toggle
        ttk.Label(f, text='Bot Token:').grid(row=1, column=0, sticky='e', padx=8, pady=2)
        self._tok_var = tk.StringVar(value=str(self._deep_get(t, ['bot_token'], '') or ''))
        self._tok_ent = ttk.Entry(f, textvariable=self._tok_var, width=44, show='•')
        self._tok_ent.grid(row=1, column=1, sticky='w', padx=8, pady=2)
        self._tok_shown = False
        ttk.Button(f, text='👁', width=3, command=self._toggle_token).grid(
            row=1, column=2, sticky='w')
        self._pair_field(f, 'Chat ID:', t, ['chat_id'], row=2)
        self._pair_field(f, 'Token Env Var:', t, ['token_env'], row=3)
        self._pair_field(f, 'Chat ID Env Var:', t, ['chat_id_env'], row=4)
        self._pair_check(f, 'Kirim chart saat ada sinyal', sc, ['enabled'], row=5)
        ttk.Label(f, text='Chart symbols (pisah koma, kosong = semua):').grid(
            row=6, column=0, sticky='e', padx=8, pady=2)
        self._chart_sym_var = tk.StringVar(value=', '.join(sc.get('symbols', ['XAUUSD']) or []))
        ttk.Entry(f, textvariable=self._chart_sym_var, width=34).grid(
            row=6, column=1, sticky='w', padx=8, pady=2)
        ttk.Label(f, foreground='gray',
                  text='Semua fitur Telegram (menu tombol, /pilihpair, /lot, /stop) otomatis '
                       'aktif saat bot jalan.\nToken kosong → Telegram dimatikan otomatis.'
                  ).grid(row=7, column=0, columnspan=3, sticky='w', padx=8, pady=6)

    def _tab_trademgmt(self, nb):
        f = ttk.Frame(nb)
        nb.add(f, text=' 📈 Trade Mgmt ')
        tm = self.cfg.setdefault('trade_management', {})
        tm.setdefault('enabled', True)
        tm.setdefault('use_bep', True)
        tm.setdefault('bep_aggressive', True)
        tm.setdefault('bep_trigger_points', 30)
        tm.setdefault('bep_lock_points', 5)
        tm.setdefault('use_trailing', True)
        tm.setdefault('trailing_start_points', 100)
        tm.setdefault('trailing_step_points', 20)
        tm.setdefault('evaluate_positions', True)
        tm.setdefault('position_eval_interval_min', 15)
        # partial TP — blok ini dipakai trade_manager
        tm.setdefault('partial_tp_enabled', True)
        tm.setdefault('partial_tp_trigger_fraction', 0.6)
        tm.setdefault('partial_tp_close_fraction', 0.5)
        # buang sisa blok lama yang salah tempat di 'server:'
        sv = self.cfg.get('server', {})
        for k in ('partial_tp_enabled', 'partial_tp_trigger_fraction',
                  'partial_tp_close_fraction', 'evaluate_positions',
                  'position_eval_interval_min', 'use_bep', 'bep_aggressive',
                  'bep_trigger_points', 'bep_lock_points', 'use_trailing',
                  'trailing_start_points', 'trailing_step_points'):
            sv.pop(k, None)
        self._pair_check(f, 'Aktifkan trade management', tm, ['enabled'], row=0)
        ttk.Separator(f, orient='horizontal').grid(row=1, column=0, columnspan=3,
                                                   sticky='ew', padx=8, pady=4)
        ttk.Label(f, text='Breakeven:', font=('', 9, 'bold')).grid(row=2, column=0,
                                                                   sticky='e', padx=8)
        self._pair_check(f, 'Gunakan BE', tm, ['use_bep'], row=3)
        self._pair_check(f, 'BE Agresif', tm, ['bep_aggressive'], row=4)
        self._pair_field(f, 'BE Trigger (points):', tm, ['bep_trigger_points'], row=5)
        self._pair_field(f, 'BE Lock (points):', tm, ['bep_lock_points'], row=6)
        ttk.Separator(f, orient='horizontal').grid(row=7, column=0, columnspan=3,
                                                   sticky='ew', padx=8, pady=4)
        ttk.Label(f, text='Trailing Stop:', font=('', 9, 'bold')).grid(row=8, column=0,
                                                                       sticky='e', padx=8)
        self._pair_check(f, 'Gunakan trailing', tm, ['use_trailing'], row=9)
        self._pair_field(f, 'Trailing Start (points):', tm, ['trailing_start_points'], row=10)
        self._pair_field(f, 'Trailing Step (points):', tm, ['trailing_step_points'], row=11)
        ttk.Separator(f, orient='horizontal').grid(row=12, column=0, columnspan=3,
                                                   sticky='ew', padx=8, pady=4)
        ttk.Label(f, text='Partial TP:', font=('', 9, 'bold')).grid(row=13, column=0,
                                                                    sticky='e', padx=8)
        self._pair_check(f, 'Aktifkan partial TP', tm, ['partial_tp_enabled'], row=14)
        self._pair_field(f, 'Trigger fraksi (0-1):', tm, ['partial_tp_trigger_fraction'], row=15)
        self._pair_field(f, 'Close fraksi (0-1):', tm, ['partial_tp_close_fraction'], row=16)
        ttk.Separator(f, orient='horizontal').grid(row=17, column=0, columnspan=3,
                                                   sticky='ew', padx=8, pady=4)
        self._pair_check(f, 'AI evaluasi posisi berkala', tm, ['evaluate_positions'], row=18)
        self._pair_field(f, 'Interval evaluasi (menit):', tm, ['position_eval_interval_min'], row=19)

    def _tab_advanced(self, nb):
        f = ttk.Frame(nb)
        nb.add(f, text=' ⚙️ Advanced ')
        e = self.cfg.setdefault('execution', {})
        tfil = e.setdefault('time_filter', {})
        s = self.cfg.setdefault('server', {})
        self._pair_field(f, 'Magic Number:', e, ['magic_number'], row=0)
        self._pair_field(f, 'Slippage (points):', e, ['slippage_points'], row=1)
        self._pair_field(f, 'Pending Max Dist (points):', e, ['pending_max_distance_points'], row=2)
        self._pair_field(f, 'Min SL (points):', e, ['min_sl_points'], row=3)
        self._pair_field(f, 'Max SL (points):', e, ['max_sl_points'], row=4)
        self._pair_field(f, 'Min TP (points):', e, ['min_tp_points'], row=5)
        self._pair_field(f, 'Max TP (points):', e, ['max_tp_points'], row=6)
        # allowed order types
        aot = set(e.get('allowed_order_types', ['market', 'pending']) or [])
        ttk.Label(f, text='Tipe Order Diizinkan:').grid(row=7, column=0, sticky='e', padx=8, pady=2)
        self._aot_vars = {}
        for i, t in enumerate(['market', 'pending']):
            var = tk.BooleanVar(value=t in aot)
            self._aot_vars[t] = var
            self._centang(f, t, var).grid(row=7, column=1 + i, sticky='w', pady=2)
        ttk.Separator(f, orient='horizontal').grid(row=8, column=0, columnspan=3,
                                                   sticky='ew', padx=8, pady=4)
        ttk.Label(f, text='Time Filter (blok jam trading):', font=('', 9, 'bold')).grid(
            row=9, column=0, columnspan=3, sticky='w', padx=8)
        self._pair_field(f, 'Timezone:', tfil, ['timezone'], row=10)
        ttk.Label(f, text='Block Ranges (JSON):').grid(row=11, column=0, sticky='e', padx=8)
        br = tfil.get('block_ranges', []) or []
        self._br_var = tk.StringVar(value=json.dumps(br) if br else '')
        ttk.Entry(f, textvariable=self._br_var, width=34).grid(row=11, column=1, sticky='w', padx=8)
        ttk.Label(f, foreground='gray',
                  text='contoh: [["03:00","04:00"]]  (kosong = 24 jam)').grid(row=11, column=2, sticky='w')
        ttk.Separator(f, orient='horizontal').grid(row=12, column=0, columnspan=3,
                                                   sticky='ew', padx=8, pady=4)
        ttk.Label(f, text='Server API (opsional):', font=('', 9, 'bold')).grid(
            row=13, column=0, columnspan=3, sticky='w', padx=8)
        self._pair_field(f, 'Host:', s, ['host'], row=14)
        self._pair_field(f, 'Port:', s, ['port'], row=15)
        self._pair_field(f, 'API Key Env:', s, ['api_key_env'], row=16)

    # ── form helpers ───────────────────────────────────────────────
    def _pair_field(self, parent, label, obj, keys, row, width=30, show=''):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky='e', padx=8, pady=2)
        val = self._deep_get(obj, keys, '')
        var = tk.StringVar(value='' if val is None else str(val))
        ent = ttk.Entry(parent, textvariable=var, width=width, show=show)
        ent.grid(row=row, column=1, sticky='w', padx=8, pady=2)
        self._fields.append((obj, keys, var, self._kind_of(val)))

    def _pair_combo(self, parent, label, obj, keys, values, row, editable=True):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky='e', padx=8, pady=2)
        val = self._deep_get(obj, keys, '')
        var = tk.StringVar(value='' if val is None else str(val))
        cmb = ttk.Combobox(parent, textvariable=var, values=values,
                           state='readonly' if not editable else 'normal', width=27)
        cmb.grid(row=row, column=1, sticky='w', padx=8, pady=2)
        # simpan referensi widget (untuk update runtime, mis. daftar model hasil deteksi)
        if not hasattr(self, '_combo_refs'):
            self._combo_refs = {}
        self._combo_refs[tuple(keys)] = cmb
        self._fields.append((obj, keys, var, 'str'))

    def _pair_check(self, parent, label, obj, keys, row):
        val = bool(self._deep_get(obj, keys, False))
        var = tk.BooleanVar(value=val)
        self._centang(parent, label, var).grid(
            row=row, column=1, sticky='w', padx=8, pady=2)
        self._fields.append((obj, keys, var, 'bool'))

    def _centang(self, parent, text, var):
        """Checkbox custom: ☑ (centang biru) saat aktif, ☐ saat nonaktif.
        Bukan checkbox native Windows (yang centangnya tampak seperti x)."""
        lbl = tk.Label(parent, text='☐ ' + text, bg='#0e1117',
                       fg='#9aa4b2', font=('Segoe UI', 9), cursor='hand2',
                       anchor='w')

        def _upd(*_):
            on = bool(var.get())
            lbl.config(text=('☑ ' if on else '☐ ') + text,
                       fg='#2f81f7' if on else '#9aa4b2')

        var.trace_add('write', _upd)
        lbl.bind('<Button-1>', lambda e: var.set(not var.get()))
        _upd()
        return lbl

    def _toggle_token(self):
        self._tok_shown = not self._tok_shown
        self._tok_ent.config(show='' if self._tok_shown else '•')

    @staticmethod
    def _kind_of(val):
        if isinstance(val, bool):
            return 'bool'
        if isinstance(val, int):
            return 'int'
        if isinstance(val, float):
            return 'float'
        return 'str'

    @staticmethod
    def _deep_get(obj, keys, default=None):
        for k in keys:
            if isinstance(obj, dict) and k in obj:
                obj = obj[k]
            else:
                return default
        return default if obj is None else obj

    @staticmethod
    def _deep_set(obj, keys, value):
        for k in keys[:-1]:
            if not isinstance(obj.get(k), dict):
                obj[k] = {}
            obj = obj[k]
        obj[keys[-1]] = value

    @staticmethod
    def _coerce(val, kind):
        """Konversi string field ke tipe aslinya. Return None = skip (jangan timpa)."""
        if kind == 'bool':
            return bool(val)
        s = str(val).strip()
        if s == '':
            return None
        if kind == 'int':
            try:
                return int(float(s))
            except ValueError:
                return None
        if kind == 'float':
            try:
                return float(s)
            except ValueError:
                return None
        return s

    def _live_value(self, keys):
        """Nilai field GUI saat ini (yang baru diketik user), fallback ke self.cfg.
        Dipakai tombol Test supaya membaca isi field, bukan config tersimpan.
        Kunci field bisa ['provider','x'] (absolute) atau ['x'] (relatif ke obj)."""
        want_rel = keys[1:] if len(keys) > 1 else keys
        for obj, k, var, _kind in getattr(self, '_fields', []):
            if k == keys or k == want_rel:
                return str(var.get())
        return str(self._deep_get(self.cfg, keys, '') or '')

    # ── collect / save ─────────────────────────────────────────────
    def _collect_config(self) -> dict:
        cfg = _load_cfg()
        # peta kunci relatif -> parent absolut di config (biar nilai field
        # tersimpan di tempat yang benar, bukan nyasar ke root)
        REL_PARENT = {
            'base_url': ['provider'], 'api_key': ['provider'],
            'api_key_env': ['provider'], 'model': ['provider'],
            'temperature': ['provider'], 'timeout_sec': ['provider'],
            'max_tokens': ['provider'],
            'enabled': ['provider', 'vision'], 'chart_candles': ['provider', 'vision'],
            'chart_timeframe': ['provider', 'vision'], 'chart_width': ['provider', 'vision'],
            'chart_height': ['provider', 'vision'], 'indicators_overlay': ['provider', 'vision'],
            'name': ['strategy'], 'timeframes': ['strategy'], 'default_timeframes': ['strategy'],
            'custom_prompt_file': ['strategy'], 'data_mode': ['strategy'],
            'compact_tail_last_n': ['strategy'], 'compact_tail_tf': ['strategy'],
            'terminal_path': ['mt5'], 'max_symbols': ['mt5'],
            'host': ['server'], 'port': ['server'],
            'token_env': ['telegram'], 'chat_id_env': ['telegram'],
            'chat_id': ['telegram'],
            'loop_interval_sec': ['app'],
        }
        for obj, keys, var, kind in self._fields:
            v = self._coerce(var.get(), kind)
            if v is None:
                continue
            if len(keys) == 1 and keys[0] in REL_PARENT and obj is not cfg:
                # field dari obj sub-dict (provider/strategy/dll) → tulis ke parent
                self._deep_set(cfg, REL_PARENT[keys[0]] + keys, v)
            else:
                self._deep_set(cfg, keys, v)
        # telegram token dari field khusus
        tok = self._tok_var.get().strip()
        self._deep_set(cfg, ['telegram', 'bot_token'], tok)
        if not tok:
            self._deep_set(cfg, ['telegram', 'enabled'], False)

        # symbols universe
        active = [s for s, v in self._sym_vars.items() if v.get()]
        extra = [x.strip().upper() for x in self._extra_sym_var.get().split(',') if x.strip()]
        syms = active + [x for x in extra if x not in active]
        if syms:
            self._deep_set(cfg, ['mt5', 'symbols'], syms)

        # pair aktif (subset) -> state file, konsisten dengan /pilihpair Telegram
        act = sorted(s for s, v in self._active_vars.items() if v.get())
        with open(ACTIVE_PAIRS_FILE, 'w') as fh:
            json.dump(act, fh)
        # Subset aktif = pair yang betul-betul di-scan. Kalau ada yang
        # dipilih, mt5.symbols ikut dibatasi ke subset itu supaya GUI dan
        # bot selalu konsisten (tanpa ini bot scan SEMUA universe meski
        # subset dicentang). Kosong = semua universe.
        if act:
            act_set = set(act)
            syms = [s for s in syms if s in act_set]
            if syms:
                self._deep_set(cfg, ['mt5', 'symbols'], syms)

        # timeframes
        tfs = [t for t, v in self._tf_vars.items() if v.get()]
        if tfs:
            self._deep_set(cfg, ['strategy', 'timeframes'], tfs)
        deftfs = [t.strip().upper() for t in self._deftf_var.get().split(',') if t.strip()]
        if deftfs:
            self._deep_set(cfg, ['strategy', 'default_timeframes'], deftfs)
        xau = [t for t, v in self._xau_tf_vars.items() if v.get()]
        stm = cfg.setdefault('strategy', {}).setdefault('symbol_timeframes', {})
        if xau:
            stm['XAUUSD'] = xau
        else:
            stm.pop('XAUUSD', None)

        # chart symbols
        cs = [x.strip() for x in self._chart_sym_var.get().split(',') if x.strip()]
        self._deep_set(cfg, ['telegram', 'send_charts', 'symbols'], cs)

        # per-pair RR + overrides (merge dengan yang ada)
        e = cfg.setdefault('execution', {})
        rr_map = dict(e.get('rr_by_symbol', {}) or {})
        sp_map = dict(e.get('max_spread_overrides', {}) or {})
        pd_map = dict(e.get('pending_max_distance_overrides', {}) or {})
        for sym, ents in self._pair_entries.items():
            mrr = ents['min_rr'].get().strip()
            pmin = ents['pips_min'].get().strip()
            pmax = ents['pips_max'].get().strip()
            if mrr or pmin or pmax:
                cur = dict(rr_map.get(sym, {}) or {})
                if mrr:
                    try:
                        cur['min_rr'] = float(mrr)
                    except ValueError:
                        pass
                if pmin:
                    try:
                        cur['target_pips_min'] = int(float(pmin))
                    except ValueError:
                        pass
                if pmax:
                    try:
                        cur['target_pips_max'] = int(float(pmax))
                    except ValueError:
                        pass
                rr_map[sym] = cur
            else:
                rr_map.pop(sym, None)
            for key, target in (('spread', sp_map), ('pdist', pd_map)):
                raw = ents[key].get().strip().lower()
                if not raw:
                    target.pop(sym, None)
                elif raw in ('unlimited', 'none', '∞'):
                    target[sym] = 'unlimited'
                else:
                    try:
                        target[sym] = float(raw)
                    except ValueError:
                        pass
        e['rr_by_symbol'] = rr_map
        e['max_spread_overrides'] = sp_map
        e['pending_max_distance_overrides'] = pd_map

        # allowed order types
        aot = [t for t, v in self._aot_vars.items() if v.get()]
        if aot:
            e['allowed_order_types'] = aot

        # block ranges JSON
        raw_br = self._br_var.get().strip()
        if raw_br:
            try:
                parsed = json.loads(raw_br)
                self._deep_set(cfg, ['execution', 'time_filter', 'block_ranges'], parsed)
            except json.JSONDecodeError:
                self._log('⚠️ Block Ranges bukan JSON valid — dilewati (pakai nilai lama).\n')
        else:
            self._deep_set(cfg, ['execution', 'time_filter', 'block_ranges'], [])
        return cfg

    def _save_clicked(self):
        self._save_config()
        messagebox.showinfo('Tersimpan', 'Config tersimpan ke config.yaml\n'
                                         '(pair aktif -> .active_pairs.json)')

    def _save_config(self):
        cfg = self._collect_config()
        _save_cfg(cfg)
        self.cfg = cfg
        self._log('💾 Config disimpan.\n')

    # ── start / stop ───────────────────────────────────────────────
    def _start_bot(self):
        if self.runner.is_alive():
            messagebox.showwarning('Sudah Jalan', 'Bot sedang berjalan.')
            return
        try:
            self._save_config()
        except Exception as e:
            messagebox.showerror('Gagal Simpan', f'Config gagal disimpan:\n{e}')
            return
        interval = float(self._deep_get(self.cfg, ['app', 'loop_interval_sec'], 60) or 60)
        self._status('starting')
        self._log(f'▶ Menjalankan bot (scan tiap {interval:.0f}s)...\n')
        self.runner.start(interval)

    def _stop_bot(self):
        if self.runner.is_alive():
            self._log('■ Stop bot diminta...\n')
            self._status('stopping')
            self.runner.stop()
            self.root.after(2500, self._force_stop_if_stuck)
        else:
            self._log('⏸ Bot tidak sedang jalan.\n')

    def _force_stop_if_stuck(self):
        """Setelah 2.5s: kalau engine masih nyangkut di AI call panjang,
        lepas referensi + biarkan thread daemon mati sendiri. UI langsung
        kembali responsif; MT5 gateway di-shutdown dari thread saat die."""
        if self._ui_state != 'stopping' or not self.runner.is_alive():
            return
        self._log('⚠ Engine belum berhenti — melepas kontrol. '
                  'Thread akan mati sendiri.\n')
        self.runner.detach()
        self._status('stopped')

    def _restart_bot(self):
        if not self.runner.is_alive():
            self._log('▶ Bot tidak jalan — Restart = Start.\n')
            self._start_bot()
            return
        self._log('🔄 Restart bot — stop, reload config, start ulang...\n')
        try:
            self._save_config()
        except Exception as e:
            self._log(f'⚠ Config gagal disimpan saat restart: {e}\n')
        self._status('stopping')
        self.runner.stop()
        self._pending_restart = True
        self.root.after(2500, self._force_stop_if_stuck)
        self._watch_restart()

    def _watch_restart(self):
        """Poll sampai engine benar-benar mati, lalu start ulang otomatis."""
        if self._pending_restart and self.runner.is_alive():
            self.root.after(500, self._watch_restart)
            return
        if not self._pending_restart:
            return
        self._pending_restart = False
        self._status('stopped')
        self._log('✅ Stop selesai — start ulang dengan config baru...\n')
        self._start_bot()

    # ── tests ──────────────────────────────────────────────────────
    def _test_router(self):
        def run():
            base = str(self._live_value(['provider', 'base_url'])).rstrip('/')
            # ── auto-detect API key env var ─────────────────────────────
            current_env = str(self._live_value(['provider', 'api_key_env']))
            key = str(self._live_value(['provider', 'api_key']))
            # kalau key kosong → cari dari env var yang dikenal (biar otomatis)
            if not key:
                candidates = [
                    current_env,
                    'HERMES_CUSTOM_LOCALHOST_20128_API_KEY',
                    '9ROUTER_API_KEY', 'OPENROUTER_API_KEY', 'OPENAI_API_KEY',
                    'ANTHROPIC_API_KEY', 'DEEPSEEK_API_KEY',
                    'MT5AI_API_KEY', 'HERMES_9ROUTER_API_KEY',
                ]
                found = ''
                for name in candidates:
                    if not name:
                        continue
                    v = os.environ.get(name, '')
                    if v.strip():
                        found = name
                        break
                if found:
                    key = os.environ.get(found, '')
                    if found != current_env:
                        self._deep_set(self.cfg, ['provider', 'api_key_env'], found)
                        # update field GUI "API Key Env Var" biar kelihatan
                        for obj, keys, var, _k in self._fields:
                            if keys == ['api_key_env']:
                                self.root.after(0, lambda v=var, s=found: v.set(s))
                                break
                        self._log(f'🔑 Auto-detect env var: {found} (dipakai otomatis)\n')
                    else:
                        self._log(f'🔑 Memakai env var: {found}\n')
                else:
                    self._log('ℹ API key kosong di field & tidak ada env var terdeteksi — '
                              'isi API key di field lalu Test lagi.\n')
            try:
                import urllib.request
                req = urllib.request.Request(
                    f'{base}/models',
                    headers={'Authorization': f'Bearer {key}'} if key else {})
                with urllib.request.urlopen(req, timeout=15) as r:
                    data = json.loads(r.read().decode())
                all_ids = [str(m.get('id')) for m in data.get('data', []) if m.get('id')]
                ids = all_ids[:30]
                self._log(f'🔌 9Router OK ({base}) — {len(all_ids)} model tersedia.\n')
                if ids:
                    shown = ', '.join(ids[:8]) + ('…' if len(ids) > 8 else '')
                    self._log(f'   Model: {shown}\n')
                    # isi otomatis dropdown "Model AI" (pertahankan COMBO/h1 jika ada)
                    merged = list(ids)
                    for keep in ('COMBO', 'h1'):
                        if keep not in merged:
                            merged.insert(0, keep)
                    merged = merged[:40]

                    def _upd(m=merged, first=ids[0]):
                        for kk in (('provider', 'model'), ('model',)):
                            cmb = self._combo_refs.get(kk)
                            if cmb is not None:
                                break
                        if cmb is not None:
                            cmb['values'] = m
                            if cmb.get() not in m:
                                cmb.set(first)
                    self.root.after(0, _upd)
                else:
                    self._log('   (response kosong — tidak ada model terdeteksi)\n')
            except Exception as e:
                self._log(f'❌ 9Router gagal: {e}\n')
        threading.Thread(target=run, daemon=True).start()

    def _test_mt5(self):
        def run():
            if self.runner.is_alive():
                self._log('🏛 Bot sedang jalan — MT5 sudah terkoneksi.\n')
                return
            try:
                import MetaTrader5 as mt5
                path = str(self._deep_get(self.cfg, ['mt5', 'terminal_path'], '') or '')
                ok = mt5.initialize(path) if path else mt5.initialize()
                if not ok:
                    self._log(f'❌ MT5 initialize gagal: {mt5.last_error()}\n')
                    return
                ti = mt5.terminal_info()
                ai = mt5.account_info()
                if ti and ai:
                    self._log(f'🏛 MT5 OK — akun {ai.login} ({ai.company}), '
                              f'balance {ai.balance:.2f}, connected={ti.connected}, '
                              f'trade_allowed={ti.trade_allowed}\n')
                    if not ti.trade_allowed:
                        self._log('   ⚠️ AutoTrading OFF — klik tombol "Algo Trading" di MT5!\n')
                else:
                    self._log('⚠️ MT5 terbuka tapi belum login / akun tidak terbaca.\n')
                mt5.shutdown()
            except Exception as e:
                self._log(f'❌ MT5 test gagal: {e}\n')
        threading.Thread(target=run, daemon=True).start()

    def _test_tg(self):
        def run():
            tok = self._tok_var.get().strip()
            if not tok:
                self._log('❌ Bot Token kosong — isi dulu di tab Telegram.\n')
                return
            try:
                import urllib.request
                with urllib.request.urlopen(
                        f'https://api.telegram.org/bot{tok}/getMe', timeout=8) as r:
                    data = json.loads(r.read().decode())
                if data.get('ok'):
                    b = data['result']
                    self._log(f"📱 Telegram OK — bot @{b.get('username')}\n")
                else:
                    self._log(f'❌ Telegram: {data}\n')
            except Exception as e:
                self._log(f'❌ Telegram gagal: {e}\n')
        threading.Thread(target=run, daemon=True).start()

    # ── status / poll / log ────────────────────────────────────────
    def _status(self, state):
        self._ui_state = state

    def _apply_status(self):
        st = self._ui_state
        alive = self.runner.is_alive()
        if st == 'starting':
            txt, col = '⏳ STARTING...', '#d29922'
        elif st == 'stopping':
            txt, col = '⏳ STOPPING...', '#d29922'
        elif st == 'error':
            txt, col = '⚠ ERROR — cek log', '#f85149'
        elif st == 'running' and alive:
            txt, col = '● RUNNING', '#3fb950'
        elif st in ('running', 'starting') and not alive:
            txt, col = '⏸ STOPPED', '#9aa4b2'
            self._ui_state = 'stopped'
            st = 'stopped'
        else:
            txt, col = '⏸ STOPPED', '#9aa4b2'
        if st == 'stopped':
            txt, col = ('⚠ ERROR — cek log', '#f85149') if self._ui_state == 'error' else (txt, col)
        self.lbl_state.config(text=txt, foreground=col)
        self.btn_start.config(state='disabled' if alive or st in ('starting', 'stopping') else 'normal')
        self.btn_stop.config(state='normal' if alive else 'disabled')
        self.btn_restart.config(state='normal' if alive else 'disabled')

    def _poll(self):
        try:
            self._apply_status()
            # live account info
            if self.runner.is_alive() and self.runner.gw:
                try:
                    acct = self.runner.gw.account_summary() or {}
                    pos = self.runner.gw.open_positions() or []
                    pnd = self.runner.gw.pending_orders() or []
                    self.var_acct.config(text=(
                        f"MT5 ● akun {acct.get('login', '?')} | "
                        f"Balance ${acct.get('balance', 0):.2f} | "
                        f"Equity ${acct.get('equity', 0):.2f} | "
                        f"Posisi {len(pos)} | Pending {len(pnd)}"))
                except Exception:
                    pass
            self._tail_log()
        except Exception:
            pass
        self.root.after(1000, self._poll)

    def _tail_log(self):
        try:
            size = os.path.getsize(LOG_PATH)
            if size < self._log_pos:      # rotated/truncated
                self._log_pos = 0
            if size > self._log_pos:
                with open(LOG_PATH, 'r', encoding='utf-8', errors='replace') as f:
                    f.seek(self._log_pos)
                    chunk = f.read()
                self._log_pos = size
                if chunk:
                    self._append_log(chunk)
        except OSError:
            pass

    def _append_log(self, msg):
        self.log.insert('end', msg)
        # warnai baris yang mengandung marker
        low = msg.lower()
        if '✅' in msg or 'selesai' in low or 'berhasil' in low or 'ok' in low.split():
            self.log.tag_add('ok', f'{self.log.index("end-1c")} linestart',
                             f'{self.log.index("end-1c")} lineend')
        elif '❌' in msg or 'error' in low or 'fatal' in low or 'gagal' in low:
            self.log.tag_add('err', f'{self.log.index("end-1c")} linestart',
                             f'{self.log.index("end-1c")} lineend')
        elif '⚠' in msg or 'warn' in low:
            self.log.tag_add('warn', f'{self.log.index("end-1c")} linestart',
                             f'{self.log.index("end-1c")} lineend')
        self.log.see('end')

    def _log(self, msg):
        """Thread-safe log dari thread manapun."""
        try:
            self.root.after(0, lambda: self._append_log(msg))
        except RuntimeError:
            pass

    # ── close ──────────────────────────────────────────────────────
    def _on_close(self):
        if self.runner.is_alive():
            if not messagebox.askyesno('Keluar', 'Bot masih berjalan. Stop bot & keluar?'):
                return
            self.runner.stop()
            t0 = time.time()
            while self.runner.is_alive() and time.time() - t0 < 3:
                self.root.update()
                time.sleep(0.1)
            if self.runner.is_alive():
                # engine masih nyangkut (AI call) — lepas kontrol & tutup.
                # Semua thread bot adalah daemon → proses mati dengan bersih.
                self.runner.detach()
        # auto-save: setting terakhir selalu tersimpan walau lupa klik Simpan
        try:
            self._save_config()
            self._log('💾 Config otomatis disimpan saat keluar.\n')
        except Exception as e:
            self._log(f'⚠ Config gagal disimpan saat keluar: {e}\n')
        self.root.destroy()

    def run(self):
        self.root.mainloop()


# ── headless self-test (untuk verifikasi build exe) ────────────────
def _selftest():
    lines = []
    try:
        gui = BotGUI()
        cfg = gui._collect_config()
        lines.append(f'ROOT={ROOT}')
        lines.append(f'CONFIG_PATH={CONFIG_PATH}')
        lines.append(f"provider.base_url={cfg.get('provider', {}).get('base_url')}")
        lines.append(f"provider.model={cfg.get('provider', {}).get('model')}")
        lines.append(f"strategy.name={cfg.get('strategy', {}).get('name')}")
        lines.append(f"execution.rr_by_symbol keys={sorted((cfg.get('execution', {}).get('rr_by_symbol', {}) or {}).keys())}")
        lines.append(f"telegram.enabled={cfg.get('telegram', {}).get('enabled')}")
        lines.append(f"mt5.symbols={cfg.get('mt5', {}).get('symbols')}")
        # jangan menulis config saat selftest
        gui.root.destroy()
        # modul berat harus bisa di-import (validasi bundle PyInstaller)
        for mod in ('MetaTrader5', 'matplotlib', 'yaml', 'numpy'):
            try:
                __import__(mod)
                lines.append(f'IMPORT_{mod}=OK')
            except Exception as e:
                lines.append(f'IMPORT_{mod}=FAIL {e}')
        lines.append('SELFTEST=OK')
    except Exception as e:
        lines.append(f'SELFTEST=FAIL {e}')
        lines.append(traceback.format_exc())
    out = os.path.join(ROOT, '_selftest.txt')
    with open(out, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print('\n'.join(lines))


if __name__ == '__main__':
    if '--selftest' in sys.argv:
        _selftest()
        sys.exit(0)
    BotGUI().run()
