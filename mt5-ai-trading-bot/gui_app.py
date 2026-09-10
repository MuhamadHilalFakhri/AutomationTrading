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
import urllib.parse
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
# Model manual/alias yang tetap tersedia walaupun 9Router tidak menampilkannya
# di GET /models (contoh: tunnel membutuhkan credential provider tertentu).
MODELS = ['COMBO', 'h1', 'zr', 'tunnel', 'gpt-4o', 'claude-sonnet-4',
          'claude-3.5-haiku', 'deepseek-v3']
STRATEGIES = ['adaptive', 'scalping', 'snd', 'trend', 'custom']


# UI palette is intentionally small and opaque.  Keeping these values in one
# place makes the desktop terminal feel consistent without touching any of the
# trading/configuration code below.
UI = {
    'bg': '#0B0F14',
    'panel': '#111821',
    'panel_alt': '#151E29',
    'field': '#1B2633',
    'border': '#2A3747',
    'text': '#F1F5F9',
    'muted': '#94A3B8',
    'blue': '#3B82F6',
    'green': '#22C55E',
    'red': '#EF4444',
    'amber': '#F59E0B',
    'cyan': '#38BDF8',
    'terminal': '#0A0E13',
}
FONT_UI = ('Segoe UI', 10)
FONT_UI_MEDIUM = ('Segoe UI', 10, 'bold')
FONT_HEADING = ('Segoe UI', 20, 'bold')
FONT_MONO = ('Consolas', 10)
FONT_MONO_BOLD = ('Consolas', 10, 'bold')


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
        self.root.title('AI Trading Bot — MT5 Terminal')
        self.root.geometry('1280x860')
        self.root.minsize(1040, 700)
        self._set_window_icon()
        self._setup_style()
        self._set_dark_titlebar()
        self.cfg = _load_cfg()
        # prefill API key dari env jika config kosong
        if not self._deep_get(self.cfg, ['provider', 'api_key'], ''):
            env_name = self._deep_get(self.cfg, ['provider', 'api_key_env'], '') or ''
            self._deep_set(self.cfg, ['provider', 'api_key'], os.environ.get(env_name, ''))
        self.runner = BotRunner(self)
        self._ui_state = 'stopped'
        self._pending_restart = False
        self._fields = []
        self._field_errors = {}
        self._test_buttons = []
        self._last_activity = 'Ready'
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

        self.root.configure(bg=UI['bg'])
        st.configure('.', background=UI['bg'], foreground=UI['text'],
                     fieldbackground=UI['field'], bordercolor=UI['border'],
                     lightcolor=UI['bg'], darkcolor=UI['bg'],
                     focuscolor=UI['blue'], font=FONT_UI)
        st.configure('TFrame', background=UI['bg'])
        st.configure('Panel.TFrame', background=UI['panel'])
        st.configure('AltPanel.TFrame', background=UI['panel_alt'])
        st.configure('TLabel', background=UI['panel'], foreground=UI['text'],
                     font=FONT_UI)
        st.configure('Dim.TLabel', background=UI['panel'], foreground=UI['muted'],
                     font=('Segoe UI', 9))
        st.configure('Header.TLabel', background=UI['bg'], foreground=UI['text'],
                     font=FONT_HEADING)
        st.configure('Sub.TLabel', background=UI['bg'], foreground=UI['muted'],
                     font=('Segoe UI', 10))
        st.configure('Card.TLabelframe', background=UI['panel'],
                     bordercolor=UI['border'], foreground=UI['text'],
                     relief='solid', borderwidth=1, padding=12)
        st.configure('Card.TLabelframe.Label', background=UI['panel'],
                     foreground=UI['text'], font=FONT_UI_MEDIUM)
        st.configure('TNotebook', background=UI['bg'], bordercolor=UI['border'],
                     tabmargins=(0, 0, 0, 0))
        st.configure('TNotebook.Tab', background=UI['panel'], foreground=UI['muted'],
                     padding=(16, 9), font=FONT_UI)
        st.map('TNotebook.Tab', background=[('selected', UI['panel_alt']),
                                            ('active', UI['field'])],
               foreground=[('selected', UI['text']), ('active', UI['text'])])
        st.configure('TEntry', fieldbackground=UI['field'], foreground=UI['text'],
                     insertcolor=UI['text'], bordercolor=UI['border'],
                     padding=(8, 6), font=FONT_MONO)
        st.map('TEntry', bordercolor=[('focus', UI['blue'])],
               lightcolor=[('focus', UI['blue'])], darkcolor=[('focus', UI['blue'])])
        st.configure('TCombobox', fieldbackground=UI['field'], foreground=UI['text'],
                     arrowcolor=UI['muted'], bordercolor=UI['border'],
                     padding=(8, 5), font=FONT_MONO)
        st.map('TCombobox', fieldbackground=[('readonly', UI['field']),
                                             ('focus', UI['field'])],
               bordercolor=[('focus', UI['blue'])],
               foreground=[('disabled', UI['muted'])])
        st.configure('TButton', background=UI['panel_alt'], foreground=UI['text'],
                     bordercolor=UI['border'], padding=(12, 7),
                     font=FONT_UI_MEDIUM)
        st.map('TButton', background=[('pressed', UI['field']),
                                      ('active', UI['field']),
                                      ('disabled', UI['panel'])],
               foreground=[('disabled', '#526174')],
               bordercolor=[('focus', UI['blue'])])
        st.configure('Start.TButton', background='#176B35', foreground='#FFFFFF')
        st.map('Start.TButton', background=[('pressed', '#0F4D26'),
                                            ('active', '#1D8442'),
                                            ('disabled', '#14321F')])
        st.configure('Stop.TButton', background='#8E2630', foreground='#FFFFFF')
        st.map('Stop.TButton', background=[('pressed', '#641A22'),
                                           ('active', '#B3313D'),
                                           ('disabled', '#3A1518')])
        st.configure('Restart.TButton', background='#95600B', foreground='#FFFFFF')
        st.map('Restart.TButton', background=[('pressed', '#684308'),
                                              ('active', '#B8790E'),
                                              ('disabled', '#3A2A12')])
        st.configure('Test.TButton', background=UI['panel_alt'], foreground=UI['cyan'],
                     font=FONT_UI)
        st.map('Test.TButton', background=[('pressed', UI['field']),
                                           ('active', UI['field']),
                                           ('disabled', UI['panel'])])
        st.configure('Save.TButton', background='#245DA8', foreground='#FFFFFF')
        st.map('Save.TButton', background=[('pressed', '#1B467E'),
                                           ('active', '#3275CD'),
                                           ('disabled', '#1E2F40')])
        st.configure('Accent.TButton', background='#1E4F8C', foreground='#FFFFFF')
        st.map('Accent.TButton', background=[('pressed', '#163966'),
                                             ('active', '#2865AD')])
        st.configure('Status.TLabel', background=UI['panel_alt'], foreground=UI['text'],
                     font=FONT_MONO_BOLD, padding=(10, 6))
        st.configure('StatusMuted.TLabel', background=UI['panel'], foreground=UI['muted'],
                     font=FONT_MONO, padding=(10, 6))
        st.configure('StatusGood.TLabel', background='#123A25', foreground=UI['green'],
                     font=FONT_MONO_BOLD, padding=(10, 6))
        st.configure('StatusWarn.TLabel', background='#3A2C12', foreground=UI['amber'],
                     font=FONT_MONO_BOLD, padding=(10, 6))
        st.configure('StatusBad.TLabel', background='#3B171C', foreground=UI['red'],
                     font=FONT_MONO_BOLD, padding=(10, 6))
        st.configure('Acct.TLabel', background=UI['panel'], foreground=UI['cyan'],
                     font=FONT_MONO, padding=(10, 6))
        st.configure('Helper.TLabel', background=UI['panel'], foreground=UI['muted'],
                     font=('Segoe UI', 9))
        st.configure('Error.TLabel', background=UI['panel'], foreground=UI['red'],
                     font=('Segoe UI', 9))
        st.configure('SectionTitle.TLabel', background=UI['panel'], foreground=UI['text'],
                     font=FONT_UI_MEDIUM)
        st.configure('Vertical.TSeparator', background=UI['border'])
        st.configure('Horizontal.TSeparator', background=UI['border'])

    def _set_dark_titlebar(self):
        """Use the native dark title bar where Windows exposes that API."""
        if sys.platform != 'win32':
            return
        try:
            import ctypes
            hwnd = self.root.winfo_id()
            value = ctypes.c_int(1)
            for attr in (20, 19):  # DWMWA_USE_IMMERSIVE_DARK_MODE (Win10/11)
                result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, attr, ctypes.byref(value), ctypes.sizeof(value))
                if result == 0:
                    break
        except Exception:
            pass

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
            except (ValueError, TypeError):
                return None
        if kind == 'float':
            try:
                return float(s)
            except (ValueError, TypeError):
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
        def object_path(target):
            def walk(node, path):
                if node is target:
                    return path
                if isinstance(node, dict):
                    for name, child in node.items():
                        found = walk(child, path + [name])
                        if found is not None:
                            return found
                return None
            return walk(self.cfg, [])

        for obj, keys, var, kind in self._fields:
            v = self._coerce(var.get(), kind)
            if v is None:
                continue
            parent_path = object_path(obj)
            if len(keys) == 1 and parent_path:
                self._deep_set(cfg, parent_path + keys, v)
            elif len(keys) == 1 and keys[0] in REL_PARENT and obj is not cfg:
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
        # Read Tk variables before entering the worker thread.
        base = str(self._live_value(['provider', 'base_url'])).rstrip('/')
        current_env = str(self._live_value(['provider', 'api_key_env']))
        initial_key = str(self._live_value(['provider', 'api_key']))
        current_model = str(self._live_value(['provider', 'model']) or '').strip()

        def run():
            key = initial_key
            # ── auto-detect API key env var ─────────────────────────────
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
                    # Isi otomatis dropdown "Model AI".
                    # Alias manual tetap dipertahankan walau tidak muncul di
                    # GET /models (contoh tunnel; validasi dilakukan saat run).
                    current_model = str(self._live_value(['provider', 'model']) or '').strip()
                    merged = list(ids)
                    for keep in ('COMBO', 'h1', 'zr', 'tunnel', current_model):
                        if keep and keep not in merged:
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
        # Snapshot Tk values on the UI thread; network work runs in background.
        tok = self._tok_var.get().strip()
        chat = (self._live_value(['telegram', 'chat_id'])
                or self._live_value(['chat_id'])
                or str(self._deep_get(self.cfg, ['telegram', 'chat_id'], '') or ''))

        def run():
            if not tok:
                self._log('❌ Bot Token kosong — isi dulu di tab Telegram.\n')
                return
            try:
                import urllib.request
                with urllib.request.urlopen(
                        f'https://api.telegram.org/bot{tok}/getMe', timeout=8) as r:
                    data = json.loads(r.read().decode())
                if not data.get('ok'):
                    self._log(f'❌ Telegram: {data}\n')
                    return
                b = data['result']
                self._log(f"📱 Token OK — bot @{b.get('username')}.\n")
                # ── uji kirim end-to-end (bukan cuma token) ──────────────
                if not chat:
                    self._log('❌ Chat ID kosong — isi Chat ID (ID Telegram kamu) di '
                              'tab Telegram, lalu Test lagi.\n')
                    return
                body = ('chat_id={}&text={}'.format(
                    urllib.parse.quote(str(chat)),
                    urllib.parse.quote('✅ Test dari AI Trading Bot — koneksi Telegram OK!')))
                req = urllib.request.Request(
                    f'https://api.telegram.org/bot{tok}/sendMessage',
                    data=body.encode(), method='POST')
                with urllib.request.urlopen(req, timeout=10) as r2:
                    out = json.loads(r2.read().decode())
                if out.get('ok'):
                    self._log(f'✅ Pesan uji TERKIRIM ke chat {chat} — cek Telegram-mu!\n')
                else:
                    desc = out.get('description', '?')
                    self._log(f'❌ Kirim gagal (chat {chat}): {desc}\n')
                    self._log('   Chat ID salah/kosong, atau kamu belum pernah /start ke bot ini.\n')
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
                    self.var_mt5_status.set('MT5  connected')
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
        if hasattr(self, 'var_last_activity'):
            self.var_last_activity.set(msg.strip().splitlines()[-1][:110] if msg.strip() else 'Ready')
            low_msg = msg.lower()
            if 'mt5' in low_msg and any(x in low_msg for x in ('ok', 'terhubung', 'connected')):
                self.var_mt5_status.set('MT5  connected')
            elif 'mt5' in low_msg and any(x in low_msg for x in ('gagal', 'error', 'fatal')):
                self.var_mt5_status.set('MT5  error')
            if '9router' in low_msg and 'ok' in low_msg:
                self.var_router_status.set('9Router  connected')
            elif '9router' in low_msg and any(x in low_msg for x in ('gagal', 'error')):
                self.var_router_status.set('9Router  error')
            if ('telegram' in low_msg or 'token ok' in low_msg) and any(
                    x in low_msg for x in ('terkirim', 'token ok')):
                self.var_tg_status.set('Telegram  connected')
            elif ('telegram' in low_msg or 'token' in low_msg) and any(
                    x in low_msg for x in ('gagal', 'error')):
                self.var_tg_status.set('Telegram  error')
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

    # ------------------------------------------------------------------
    # Modern terminal UI
    # ------------------------------------------------------------------
    # These methods intentionally live alongside the original handlers.  They
    # only compose widgets and read/write the same variables used by the bot.
    # The runner, config collector, connection tests and all business logic
    # above remain unchanged.

    def _tooltip(self, widget, text):
        tip = {'window': None}

        def show(_event=None):
            if tip['window'] or not widget.winfo_viewable():
                return
            x = widget.winfo_rootx() + 8
            y = widget.winfo_rooty() + widget.winfo_height() + 4
            win = tk.Toplevel(widget)
            win.overrideredirect(True)
            win.configure(bg=UI['border'])
            tk.Label(win, text=text, bg=UI['border'], fg=UI['text'],
                     font=('Segoe UI', 9), padx=8, pady=5).pack()
            win.geometry(f'+{x}+{y}')
            tip['window'] = win

        def hide(_event=None):
            if tip['window']:
                tip['window'].destroy()
                tip['window'] = None

        widget.bind('<Enter>', show, add='+')
        widget.bind('<Leave>', hide, add='+')

    def _scroll_tab(self, nb, title):
        page = ttk.Frame(nb, style='Panel.TFrame')
        nb.add(page, text=title)
        viewport = ttk.Frame(page, style='Panel.TFrame')
        viewport.pack(fill='both', expand=True)
        canvas = tk.Canvas(viewport, background=UI['panel'], highlightthickness=0,
                           bd=0)
        scroll = ttk.Scrollbar(viewport, orient='vertical', command=canvas.yview)
        content = ttk.Frame(canvas, style='Panel.TFrame')
        content.columnconfigure(0, weight=1)
        window_id = canvas.create_window((0, 0), window=content, anchor='nw')
        canvas.configure(yscrollcommand=scroll.set)
        content.bind('<Configure>', lambda _e: canvas.configure(
            scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>', lambda e: canvas.itemconfigure(
            window_id, width=e.width))
        canvas.pack(side='left', fill='both', expand=True)
        scroll.pack(side='right', fill='y')

        def wheel(event):
            canvas.yview_scroll(-1 * int(event.delta / 120), 'units')

        canvas.bind('<Enter>', lambda _e: canvas.bind_all('<MouseWheel>', wheel))
        canvas.bind('<Leave>', lambda _e: canvas.unbind_all('<MouseWheel>'))
        return content

    def _section(self, parent, title, description=''):
        card = ttk.LabelFrame(parent, text=title, style='Card.TLabelframe')
        card.pack(fill='x', padx=10, pady=6, anchor='n')
        card.columnconfigure(1, weight=1)
        card.columnconfigure(2, weight=1)
        if description:
            ttk.Label(card, text=description, style='Helper.TLabel',
                      wraplength=900).grid(row=0, column=0, columnspan=3,
                                           sticky='w', padx=2, pady=(0, 8))
        return card

    def _build_ui(self):
        hdr = ttk.Frame(self.root, style='Panel.TFrame', padding=(18, 14))
        hdr.pack(fill='x', padx=12, pady=(12, 0))
        try:
            base = getattr(sys, '_MEIPASS', ROOT)
            logo_p = os.path.join(base, 'assets', 'logo.png')
            if os.path.exists(logo_p):
                self._logo_img = tk.PhotoImage(file=logo_p).subsample(7, 7)
                ttk.Label(hdr, image=self._logo_img,
                          background=UI['panel']).pack(side='left', padx=(0, 12))
        except Exception:
            pass
        brand = ttk.Frame(hdr, style='Panel.TFrame')
        brand.pack(side='left')
        ttk.Label(brand, text='AI Trading Bot', style='Header.TLabel').pack(anchor='w')
        ttk.Label(brand, text='MT5 execution · AI Vision · 9Router',
                  style='Sub.TLabel').pack(anchor='w')
        ttk.Label(hdr, text='Desktop terminal', style='StatusMuted.TLabel').pack(
            side='right', padx=(8, 0))
        self.lbl_state = ttk.Label(hdr, text='STOPPED', style='StatusMuted.TLabel')
        self.lbl_state.pack(side='right')

        toolbar = ttk.Frame(self.root, style='Panel.TFrame', padding=(14, 10))
        toolbar.pack(fill='x', padx=12, pady=(1, 0))
        self.btn_start = ttk.Button(toolbar, text='Start bot', style='Start.TButton',
                                    command=self._start_bot)
        self.btn_start.pack(side='left', padx=(0, 4))
        self.btn_stop = ttk.Button(toolbar, text='Stop bot', style='Stop.TButton',
                                   command=self._stop_bot, state='disabled')
        self.btn_stop.pack(side='left', padx=4)
        self.btn_restart = ttk.Button(toolbar, text='Restart', style='Restart.TButton',
                                      command=self._restart_bot, state='disabled')
        self.btn_restart.pack(side='left', padx=4)
        ttk.Separator(toolbar, orient='vertical').pack(side='left', fill='y', padx=12)
        self.btn_save = ttk.Button(toolbar, text='Save configuration', style='Save.TButton',
                                   command=self._save_clicked)
        self.btn_save.pack(side='left', padx=4)

        tests = ttk.Frame(toolbar, style='Panel.TFrame')
        tests.pack(side='right')
        ttk.Label(tests, text='Connection tests', style='Dim.TLabel').pack(
            side='left', padx=(0, 8))
        self.btn_test_router = ttk.Button(tests, text='9Router', style='Test.TButton',
                                          command=self._test_router)
        self.btn_test_router.pack(side='left', padx=3)
        self.btn_test_mt5 = ttk.Button(tests, text='MT5', style='Test.TButton',
                                       command=self._test_mt5)
        self.btn_test_mt5.pack(side='left', padx=3)
        self.btn_test_tg = ttk.Button(tests, text='Telegram', style='Test.TButton',
                                      command=self._test_tg)
        self.btn_test_tg.pack(side='left', padx=3)
        self._test_buttons = [self.btn_test_router, self.btn_test_mt5, self.btn_test_tg]
        self._tooltip(self.btn_test_router, 'Test endpoint 9Router dan refresh daftar model.')
        self._tooltip(self.btn_test_mt5, 'Periksa terminal, akun, dan izin trading MT5.')
        self._tooltip(self.btn_test_tg, 'Verifikasi token dan kirim pesan uji Telegram.')

        nb = ttk.Notebook(self.root)
        nb.pack(fill='both', expand=True, padx=12, pady=8)
        self.notebook = nb
        self._tab_terminal(nb)
        self._tab_connection(nb)
        self._tab_symbols(nb)
        self._tab_risk(nb)
        self._tab_perpair(nb)
        self._tab_telegram(nb)
        self._tab_trademgmt(nb)
        self._tab_advanced(nb)

        stat = ttk.Frame(self.root, style='Panel.TFrame', padding=(8, 5))
        stat.pack(fill='x', padx=12, pady=(0, 5))
        self.var_bot_status = tk.StringVar(value='Bot  stopped')
        self.var_mt5_status = tk.StringVar(value='MT5  —')
        self.var_router_status = tk.StringVar(value='9Router  —')
        self.var_tg_status = tk.StringVar(value='Telegram  —')
        self.var_last_activity = tk.StringVar(value='Ready')
        self._status_labels = {
            'bot': ttk.Label(stat, textvariable=self.var_bot_status,
                             style='StatusMuted.TLabel'),
            'mt5': ttk.Label(stat, textvariable=self.var_mt5_status,
                             style='StatusMuted.TLabel'),
            'router': ttk.Label(stat, textvariable=self.var_router_status,
                                style='StatusMuted.TLabel'),
            'telegram': ttk.Label(stat, textvariable=self.var_tg_status,
                                  style='StatusMuted.TLabel'),
        }
        for label in self._status_labels.values():
            label.pack(side='left', padx=2)
        ttk.Label(stat, textvariable=self.var_last_activity,
                  style='StatusMuted.TLabel').pack(side='right', padx=2)
        self.var_acct = ttk.Label(self.root, text='MT5  —', style='Acct.TLabel')
        self.var_acct.pack(fill='x', padx=12, pady=(0, 8))

    def _tab_terminal(self, nb):
        f = ttk.Frame(nb, style='Panel.TFrame', padding=12)
        nb.add(f, text='Terminal')
        bar = ttk.Frame(f, style='Panel.TFrame')
        bar.pack(fill='x', pady=(0, 8))
        ttk.Label(bar, text='Runtime output', style='SectionTitle.TLabel').pack(side='left')
        ttk.Button(bar, text='Clear', style='Test.TButton',
                   command=lambda: self.log.delete('1.0', 'end')).pack(side='right')
        ttk.Button(bar, text='Copy all', style='Test.TButton',
                   command=self._copy_log).pack(side='right', padx=(0, 6))
        self.log = scrolledtext.ScrolledText(
            f, bg=UI['terminal'], fg='#C8D3E0', insertbackground='#C8D3E0',
            font=FONT_MONO, wrap='word', relief='flat', highlightthickness=1,
            highlightbackground=UI['border'], highlightcolor=UI['blue'])
        self.log.pack(fill='both', expand=True)
        self.log.tag_config('ok', foreground=UI['green'])
        self.log.tag_config('err', foreground=UI['red'])
        self.log.tag_config('warn', foreground=UI['amber'])
        self.log.tag_config('info', foreground=UI['cyan'])
        self.log.insert('end', 'Terminal ready. Start the bot to monitor runtime activity.\n')
        self.log.see('end')

    def _tab_connection(self, nb):
        content = self._scroll_tab(nb, 'Connection')
        p = self.cfg.setdefault('provider', {})
        v = p.setdefault('vision', {})
        mt5 = self.cfg.setdefault('mt5', {})
        app = self.cfg.setdefault('app', {})
        card = self._section(content, 'MT5 connection',
                             'Terminal path and scan cadence used by the in-process engine.')
        self._pair_field(card, 'Terminal path', mt5, ['terminal_path'], 1, width=48)
        ttk.Button(card, text='Detect terminal and broker symbols', style='Test.TButton',
                   command=self._auto_detect).grid(row=2, column=1, sticky='w', padx=8, pady=(3, 6))
        self._pair_field(card, 'Scan interval (sec)', app, ['loop_interval_sec'], 3)

        card = self._section(content, 'AI provider',
                             'Endpoint, credentials, model and strategy used for signal generation.')
        self._pair_field(card, '9Router URL', p, ['base_url'], 1, width=40)
        self._pair_secret(card, 'API key', p, ['api_key'], 2, width=40)
        self._pair_field(card, 'API key env var', p, ['api_key_env'], 3, width=34)
        self._pair_combo(card, 'Model', p, ['model'], MODELS, 4, editable=True)
        self._pair_combo(card, 'Strategy', self.cfg.setdefault('strategy', {}), ['name'],
                         STRATEGIES, 5, editable=True)
        self._pair_field(card, 'Custom prompt file', self.cfg['strategy'],
                         ['custom_prompt_file'], 6, width=34)
        self._pair_field(card, 'Temperature', p, ['temperature'], 7)
        self._pair_field(card, 'Timeout (sec)', p, ['timeout_sec'], 8)
        self._pair_field(card, 'Max tokens', p, ['max_tokens'], 9)

        card = self._section(content, 'Vision chart',
                             'Chart PNG settings sent to the AI provider. Technical values use a monospace input.')
        self._pair_check(card, 'Enable vision', v, ['enabled'], 1)
        self._pair_field(card, 'Candles', v, ['chart_candles'], 2)
        self._pair_combo(card, 'Timeframe', v, ['chart_timeframe'],
                         ['M1', 'M5', 'M15', 'M30', 'H1', 'H4'], 3)
        self._pair_field(card, 'Chart width (px)', v, ['chart_width'], 4)
        self._pair_field(card, 'Chart height (px)', v, ['chart_height'], 5)
        self._pair_check(card, 'Overlay indicators', v, ['indicators_overlay'], 6)

    def _tab_symbols(self, nb):
        content = self._scroll_tab(nb, 'Symbols & timeframes')
        s = self.cfg.setdefault('mt5', {})
        st = self.cfg.setdefault('strategy', {})
        card = self._section(content, 'Symbol universe',
                             'Choose instruments available to the bot. Extra broker symbols can be typed comma-separated.')
        self._sym_vars = {}
        active = set(s.get('symbols', ALL_PAIRS) or [])
        for i, sym in enumerate(ALL_PAIRS):
            var = tk.BooleanVar(value=sym in active)
            self._sym_vars[sym] = var
            self._centang(card, sym, var).grid(row=1 + i // 3, column=i % 3,
                                               sticky='w', padx=8, pady=3)
        extra = [x for x in active if x not in ALL_PAIRS]
        self._extra_sym_var = tk.StringVar(value=', '.join(extra))
        ttk.Label(card, text='Additional symbols', style='Dim.TLabel').grid(
            row=3, column=0, sticky='w', padx=8, pady=(10, 3))
        ttk.Entry(card, textvariable=self._extra_sym_var, width=34).grid(
            row=3, column=1, columnspan=2, sticky='ew', padx=8, pady=(10, 3))

        card = self._section(content, 'Active scan subset',
                             'Optional runtime subset. Empty means the complete universe is scanned.')
        self._active_vars = {}
        try:
            with open(ACTIVE_PAIRS_FILE) as fh:
                act = set(json.load(fh) or [])
        except Exception:
            act = set()
        for i, sym in enumerate(ALL_PAIRS):
            var = tk.BooleanVar(value=sym in act)
            self._active_vars[sym] = var
            self._centang(card, sym, var).grid(row=1 + i // 3, column=i % 3,
                                               sticky='w', padx=8, pady=3)

        card = self._section(content, 'Analysis timeframes',
                             'Timeframes available to the strategy and per-pair confirmation settings.')
        self._tf_vars = {}
        tfs = set(st.get('timeframes', ['M5', 'M15', 'M30', 'H1', 'H4']) or [])
        for i, tf in enumerate(ALL_TFS):
            var = tk.BooleanVar(value=tf in tfs)
            self._tf_vars[tf] = var
            self._centang(card, tf, var).grid(row=1, column=i, sticky='w', padx=5, pady=3)
        self._deftf_var = tk.StringVar(value=', '.join(st.get('default_timeframes',
                                                              ['M5', 'M15', 'H1']) or []))
        ttk.Label(card, text='Default timeframes', style='Dim.TLabel').grid(
            row=2, column=0, sticky='w', padx=8, pady=(8, 3))
        ttk.Entry(card, textvariable=self._deftf_var, width=26).grid(
            row=2, column=1, sticky='ew', padx=8, pady=(8, 3))
        ttk.Label(card, text='XAUUSD override', style='SectionTitle.TLabel').grid(
            row=3, column=0, columnspan=3, sticky='w', padx=8, pady=(12, 3))
        self._xau_tf_vars = {}
        xau = set(st.get('symbol_timeframes', {}).get('XAUUSD',
                                                        ['M5', 'M15', 'M30', 'H1', 'H4']) or [])
        for i, tf in enumerate(ALL_TFS):
            var = tk.BooleanVar(value=tf in xau)
            self._xau_tf_vars[tf] = var
            self._centang(card, tf, var).grid(row=4, column=i, sticky='w', padx=5, pady=3)

        card = self._section(content, 'Data mode')
        self._pair_combo(card, 'Mode', st, ['data_mode'], ['compact', 'full'], 1, editable=False)
        self._pair_field(card, 'Tail candles', st, ['compact_tail_last_n'], 2)
        self._pair_combo(card, 'Tail timeframe', st, ['compact_tail_tf'],
                         ['M1', 'M5', 'M15', 'M30', 'H1', 'H4'], 3, editable=False)

    def _tab_risk(self, nb):
        content = self._scroll_tab(nb, 'Risk management')
        e = self.cfg.setdefault('execution', {})
        card = self._section(content, 'Position sizing',
                             'Controls confidence, risk mode and lot sizing before an order is sent.')
        rows = [('Min confidence (0–1)', 'min_conf_for_entry'),
                ('Risk per trade (%)', 'risk_percent'), ('Risk mode', 'risk_mode'),
                ('Fixed lots', 'fixed_lots'), ('Manual lot', 'manual_lot'),
                ('Lot mode', 'lot_mode'), ('Min risk / reward', 'min_risk_reward'),
                ('Max lots per trade', 'max_lots_per_trade')]
        combos = {'risk_mode': ['percent', 'fixed'], 'lot_mode': ['auto', 'manual']}
        for i, (label, key) in enumerate(rows, 1):
            if key in combos:
                self._pair_combo(card, label, e, [key], combos[key], i, editable=False)
            else:
                self._pair_field(card, label, e, [key], i)
        card = self._section(content, 'Exposure limits',
                             'Global guardrails for spread, correlation, cooldown and daily loss.')
        rows = [('Max positions / symbol', 'max_open_positions_per_symbol'),
                ('Max correlated positions', 'max_correlated_positions'),
                ('Max spread (points)', 'max_spread_points'),
                ('Max daily loss (%)', 'max_daily_loss_percent'),
                ('Cooldown (minutes)', 'cooldown_minutes')]
        for i, (label, key) in enumerate(rows, 1):
            self._pair_field(card, label, e, [key], i)

    def _tab_perpair(self, nb):
        content = self._scroll_tab(nb, 'Per-pair settings')
        e = self.cfg.setdefault('execution', {})
        rr = e.get('rr_by_symbol', {}) or {}
        sp = e.get('max_spread_overrides', {}) or {}
        pd_ = e.get('pending_max_distance_overrides', {}) or {}
        card = self._section(content, 'Risk / reward and execution overrides',
                             "Blank uses the global value. Use 'unlimited' for a pair-specific cap without a limit.")
        headers = ('Pair', 'Min RR', 'Target pips min', 'Target pips max',
                   'Spread cap', 'Pending distance')
        for c, h in enumerate(headers):
            ttk.Label(card, text=h, style='Dim.TLabel').grid(row=1, column=c,
                                                              sticky='w', padx=6, pady=(0, 5))
        self._pair_entries = {}
        for r, sym in enumerate(ALL_PAIRS, 2):
            info = rr.get(sym, {}) or {}
            ttk.Label(card, text=sym, style='SectionTitle.TLabel').grid(
                row=r, column=0, sticky='w', padx=6, pady=3)
            ents = {}
            defaults = {'min_rr': str(info.get('min_rr', '')),
                        'pips_min': str(info.get('target_pips_min', '')),
                        'pips_max': str(info.get('target_pips_max', '')),
                        'spread': str(sp.get(sym, '')),
                        'pdist': str(pd_.get(sym, ''))}
            for c, key in enumerate(['min_rr', 'pips_min', 'pips_max', 'spread', 'pdist'], 1):
                var = tk.StringVar(value=defaults[key])
                ttk.Entry(card, textvariable=var, width=16).grid(
                    row=r, column=c, sticky='ew', padx=4, pady=3)
                ents[key] = var
            self._pair_entries[sym] = ents
        ttk.Label(card, text="Spread and pending distance accept a number, blank, or 'unlimited'.",
                  style='Helper.TLabel').grid(row=len(ALL_PAIRS) + 2, column=0,
                                              columnspan=6, sticky='w', padx=6, pady=(8, 2))

    def _tab_telegram(self, nb):
        content = self._scroll_tab(nb, 'Telegram')
        t = self.cfg.setdefault('telegram', {})
        sc = t.setdefault('send_charts', {})
        card = self._section(content, 'Telegram connection',
                             'Notifications, command menu and end-to-end message testing.')
        self._pair_check(card, 'Enable Telegram', t, ['enabled'], 1)
        self._pair_secret(card, 'Bot token', t, ['bot_token'], 2, width=42)
        self._pair_field(card, 'Chat ID', t, ['chat_id'], 3)
        self._pair_field(card, 'Token env var', t, ['token_env'], 4, width=34)
        self._pair_field(card, 'Chat ID env var', t, ['chat_id_env'], 5, width=34)
        ttk.Label(card, text='Token is masked by default. The Test button sends a real message.',
                  style='Helper.TLabel').grid(row=6, column=1, columnspan=2,
                                              sticky='w', padx=8, pady=(3, 5))
        card = self._section(content, 'Chart notifications')
        self._pair_check(card, 'Send chart when a signal is found', sc, ['enabled'], 1)
        self._chart_sym_var = tk.StringVar(value=', '.join(sc.get('symbols', ['XAUUSD']) or []))
        ttk.Label(card, text='Chart symbols', style='Dim.TLabel').grid(
            row=2, column=0, sticky='w', padx=8, pady=3)
        ttk.Entry(card, textvariable=self._chart_sym_var, width=34).grid(
            row=2, column=1, sticky='ew', padx=8, pady=3)

    def _tab_trademgmt(self, nb):
        content = self._scroll_tab(nb, 'Trade management')
        tm = self.cfg.setdefault('trade_management', {})
        for key, value in {'enabled': True, 'use_bep': True, 'bep_aggressive': True,
                           'bep_trigger_points': 30, 'bep_lock_points': 5,
                           'use_trailing': True, 'trailing_start_points': 100,
                           'trailing_step_points': 20, 'evaluate_positions': True,
                           'position_eval_interval_min': 15, 'partial_tp_enabled': True,
                           'partial_tp_trigger_fraction': 0.6,
                           'partial_tp_close_fraction': 0.5}.items():
            tm.setdefault(key, value)
        # Preserve the existing cleanup of legacy server keys.
        sv = self.cfg.get('server', {})
        for k in ('partial_tp_enabled', 'partial_tp_trigger_fraction',
                  'partial_tp_close_fraction', 'evaluate_positions', 'position_eval_interval_min',
                  'use_bep', 'bep_aggressive', 'bep_trigger_points', 'bep_lock_points',
                  'use_trailing', 'trailing_start_points', 'trailing_step_points'):
            sv.pop(k, None)
        card = self._section(content, 'Trade management',
                             'Automatic protection and position evaluation after entry.')
        self._pair_check(card, 'Enable trade management', tm, ['enabled'], 1)
        self._pair_check(card, 'Use breakeven', tm, ['use_bep'], 2)
        self._pair_check(card, 'Aggressive breakeven', tm, ['bep_aggressive'], 3)
        self._pair_field(card, 'BE trigger (points)', tm, ['bep_trigger_points'], 4)
        self._pair_field(card, 'BE lock (points)', tm, ['bep_lock_points'], 5)
        self._pair_check(card, 'Use trailing stop', tm, ['use_trailing'], 6)
        self._pair_field(card, 'Trailing start (points)', tm, ['trailing_start_points'], 7)
        self._pair_field(card, 'Trailing step (points)', tm, ['trailing_step_points'], 8)
        self._pair_check(card, 'Enable partial take profit', tm, ['partial_tp_enabled'], 9)
        self._pair_field(card, 'Partial trigger fraction (0–1)', tm,
                         ['partial_tp_trigger_fraction'], 10)
        self._pair_field(card, 'Partial close fraction (0–1)', tm,
                         ['partial_tp_close_fraction'], 11)
        self._pair_check(card, 'AI position evaluation', tm, ['evaluate_positions'], 12)
        self._pair_field(card, 'Evaluation interval (minutes)', tm,
                         ['position_eval_interval_min'], 13)

    def _tab_advanced(self, nb):
        content = self._scroll_tab(nb, 'Advanced settings')
        e = self.cfg.setdefault('execution', {})
        tfil = e.setdefault('time_filter', {})
        s = self.cfg.setdefault('server', {})
        card = self._section(content, 'Execution constraints',
                             'Low-level order limits. Change these only when you understand the broker symbol settings.')
        rows = [('Magic number', 'magic_number'), ('Slippage (points)', 'slippage_points'),
                ('Pending max distance (points)', 'pending_max_distance_points'),
                ('Min SL (points)', 'min_sl_points'), ('Max SL (points)', 'max_sl_points'),
                ('Min TP (points)', 'min_tp_points'), ('Max TP (points)', 'max_tp_points')]
        for i, (label, key) in enumerate(rows, 1):
            self._pair_field(card, label, e, [key], i)
        ttk.Label(card, text='Allowed order types', style='Dim.TLabel').grid(
            row=8, column=0, sticky='w', padx=8, pady=(10, 3))
        aot = set(e.get('allowed_order_types', ['market', 'pending']) or [])
        self._aot_vars = {}
        for i, order_type in enumerate(['market', 'pending']):
            var = tk.BooleanVar(value=order_type in aot)
            self._aot_vars[order_type] = var
            self._centang(card, order_type, var).grid(row=8, column=1 + i,
                                                      sticky='w', padx=8, pady=(10, 3))

        card = self._section(content, 'Time filter',
                             'Block trading windows using JSON ranges such as [["03:00", "04:00"]].')
        self._pair_field(card, 'Timezone', tfil, ['timezone'], 1, width=28)
        br = tfil.get('block_ranges', []) or []
        self._br_var = tk.StringVar(value=json.dumps(br) if br else '')
        ttk.Label(card, text='Block ranges (JSON)', style='Dim.TLabel').grid(
            row=2, column=0, sticky='w', padx=8, pady=3)
        ttk.Entry(card, textvariable=self._br_var, width=42).grid(
            row=2, column=1, sticky='ew', padx=8, pady=3)
        self._br_error = ttk.Label(card, text='', style='Error.TLabel')
        self._br_error.grid(row=2, column=2, sticky='w', padx=(0, 8), pady=3)

        card = self._section(content, 'Optional server API')
        self._pair_field(card, 'Host', s, ['host'], 1, width=28)
        self._pair_field(card, 'Port', s, ['port'], 2)
        self._pair_field(card, 'API key env var', s, ['api_key_env'], 3, width=34)

    def _pair_field(self, parent, label, obj, keys, row, width=30, show=''):
        ttk.Label(parent, text=label, style='TLabel').grid(
            row=row, column=0, sticky='w', padx=8, pady=4)
        val = self._deep_get(obj, keys, '')
        var = tk.StringVar(value='' if val is None else str(val))
        ent = ttk.Entry(parent, textvariable=var, width=width, show=show)
        ent.grid(row=row, column=1, sticky='ew', padx=8, pady=4)
        self._fields.append((obj, keys, var, self._kind_of(val)))
        self._field_errors[id(var)] = ttk.Label(parent, text='', style='Error.TLabel')
        self._field_errors[id(var)].grid(row=row, column=2, sticky='w', padx=(0, 8), pady=4)

    def _pair_secret(self, parent, label, obj, keys, row, width=30):
        ttk.Label(parent, text=label, style='TLabel').grid(
            row=row, column=0, sticky='w', padx=8, pady=4)
        val = self._deep_get(obj, keys, '')
        var = tk.StringVar(value='' if val is None else str(val))
        ent = ttk.Entry(parent, textvariable=var, width=width, show='•')
        ent.grid(row=row, column=1, sticky='ew', padx=(8, 3), pady=4)
        if keys == ['bot_token']:
            # _collect_config and the Telegram test intentionally share this
            # live variable, just as they did in the original form.
            self._tok_var = var
            self._tok_ent = ent
        shown = {'value': False}

        def toggle():
            shown['value'] = not shown['value']
            ent.configure(show='' if shown['value'] else '•')
            show_btn.configure(text='Hide' if shown['value'] else 'Show')

        show_btn = ttk.Button(parent, text='Show', style='Test.TButton', command=toggle)
        show_btn.grid(
            row=row, column=2, sticky='e', padx=(3, 8), pady=4)
        self._fields.append((obj, keys, var, self._kind_of(val)))
        self._field_errors[id(var)] = ttk.Label(parent, text='', style='Error.TLabel')

    def _pair_combo(self, parent, label, obj, keys, values, row, editable=True):
        ttk.Label(parent, text=label, style='TLabel').grid(
            row=row, column=0, sticky='w', padx=8, pady=4)
        val = self._deep_get(obj, keys, '')
        var = tk.StringVar(value='' if val is None else str(val))
        cmb = ttk.Combobox(parent, textvariable=var, values=values,
                           state='readonly' if not editable else 'normal', width=27)
        cmb.grid(row=row, column=1, columnspan=2, sticky='ew', padx=8, pady=4)
        if not hasattr(self, '_combo_refs'):
            self._combo_refs = {}
        self._combo_refs[tuple(keys)] = cmb
        self._fields.append((obj, keys, var, 'str'))

    def _pair_check(self, parent, label, obj, keys, row):
        val = bool(self._deep_get(obj, keys, False))
        var = tk.BooleanVar(value=val)
        self._centang(parent, label, var).grid(row=row, column=1, columnspan=2,
                                               sticky='w', padx=8, pady=4)
        self._fields.append((obj, keys, var, 'bool'))

    def _centang(self, parent, text, var):
        lbl = tk.Label(parent, text='☐ ' + text, bg=UI['panel'], fg=UI['muted'],
                       font=FONT_UI, cursor='hand2', anchor='w', takefocus=1,
                       highlightthickness=1, highlightbackground=UI['panel'],
                       highlightcolor=UI['blue'])

        def update(*_):
            on = bool(var.get())
            lbl.config(text=('☑ ' if on else '☐ ') + text,
                       fg=UI['blue'] if on else UI['muted'])

        var.trace_add('write', update)
        lbl.bind('<Button-1>', lambda _e: var.set(not var.get()))
        lbl.bind('<space>', lambda _e: var.set(not var.get()))
        lbl.bind('<Return>', lambda _e: var.set(not var.get()))
        update()
        return lbl

    def _apply_status(self):
        st = self._ui_state
        alive = self.runner.is_alive()
        if st == 'starting':
            txt, col, style = 'STARTING', UI['amber'], 'StatusWarn.TLabel'
        elif st == 'stopping':
            txt, col, style = 'STOPPING', UI['amber'], 'StatusWarn.TLabel'
        elif st == 'error':
            txt, col, style = 'ERROR · check terminal', UI['red'], 'StatusBad.TLabel'
        elif st == 'running' and alive:
            txt, col, style = 'RUNNING', UI['green'], 'StatusGood.TLabel'
        elif st in ('running', 'starting') and not alive:
            txt, col, style = 'STOPPED', UI['muted'], 'StatusMuted.TLabel'
            self._ui_state = 'stopped'
            st = 'stopped'
        else:
            txt, col, style = 'STOPPED', UI['muted'], 'StatusMuted.TLabel'
        self.lbl_state.config(text=txt, foreground=col, style=style)
        self.var_bot_status.set(f'Bot  {txt.lower()}')
        self.btn_start.config(state='disabled' if alive or st in ('starting', 'stopping') else 'normal')
        self.btn_stop.config(state='normal' if alive else 'disabled')
        self.btn_restart.config(state='normal' if alive else 'disabled')

    def _validate_form(self):
        """Validate only values that can make a save unusable; errors stay near fields."""
        for label in self._field_errors.values():
            label.configure(text='')
        if hasattr(self, '_br_error'):
            self._br_error.configure(text='')
        errors = []

        def value(keys):
            for _obj, field_keys, var, _kind in self._fields:
                if field_keys == keys or field_keys == keys[1:]:
                    return str(var.get()).strip(), var
            return '', None

        url, url_var = value(['provider', 'base_url'])
        if url and not urllib.parse.urlparse(url).scheme:
            errors.append(('9Router URL must include http:// or https://.', url_var))
        interval, interval_var = value(['app', 'loop_interval_sec'])
        if interval:
            try:
                if float(interval) <= 0:
                    errors.append(('Must be greater than zero.', interval_var))
            except ValueError:
                errors.append(('Enter a number.', interval_var))
        confidence, conf_var = value(['execution', 'min_conf_for_entry'])
        if confidence:
            try:
                if not 0 <= float(confidence) <= 1:
                    errors.append(('Use a value between 0 and 1.', conf_var))
            except ValueError:
                errors.append(('Enter a number.', conf_var))
        if self._br_var.get().strip():
            try:
                json.loads(self._br_var.get().strip())
            except json.JSONDecodeError:
                self._br_error.configure(text='Invalid JSON.')
                errors.append(('Invalid JSON block range.', None))
        for message, var in errors:
            if var is not None and id(var) in self._field_errors:
                self._field_errors[id(var)].configure(text=message)
        return not errors

    def _save_config(self, validate=True):
        if validate and not self._validate_form():
            raise ValueError('Periksa field yang ditandai merah sebelum menyimpan.')
        cfg = self._collect_config()
        _save_cfg(cfg)
        self.cfg = cfg
        self._last_activity = 'Configuration saved'
        if hasattr(self, 'var_last_activity'):
            self.var_last_activity.set(self._last_activity)
        self._log('Config saved.\n')

    def _save_clicked(self):
        try:
            self._save_config()
        except Exception as exc:
            messagebox.showerror('Save failed', str(exc))
            return
        messagebox.showinfo('Saved', 'Configuration saved to config.yaml.')

    def _stop_bot(self):
        if self.runner.is_alive():
            if not messagebox.askyesno('Stop bot', 'Stop the running bot?'):
                return
            self._log('Stop bot requested...\n')
            self._status('stopping')
            self.runner.stop()
            self.root.after(2500, self._force_stop_if_stuck)
        else:
            self._log('Bot is not running.\n')

    def _restart_bot(self):
        if not self.runner.is_alive():
            self._start_bot()
            return
        if not messagebox.askyesno('Restart bot', 'Stop and start the bot again?'):
            return
        self._log('Restart requested — reloading configuration...\n')
        try:
            self._save_config()
        except Exception as exc:
            self._log(f'Config could not be saved during restart: {exc}\n')
        self._status('stopping')
        self.runner.stop()
        self._pending_restart = True
        self.root.after(2500, self._force_stop_if_stuck)
        self._watch_restart()

    def _on_close(self):
        if self.runner.is_alive():
            if not messagebox.askyesno('Exit', 'Bot is still running. Stop bot and exit?'):
                return
            self.runner.stop()
            t0 = time.time()
            while self.runner.is_alive() and time.time() - t0 < 3:
                self.root.update()
                time.sleep(0.1)
            if self.runner.is_alive():
                self.runner.detach()
        # Closing should never discard the latest edits just because a field is
        # incomplete; the explicit Save action remains strict and visible.
        try:
            self._save_config(validate=False)
        except Exception as exc:
            self._log(f'Config could not be auto-saved on exit: {exc}\n')
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
