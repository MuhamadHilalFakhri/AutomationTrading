"""UI smoke test: buka GUI, verifikasi tema & widget, tutup. Tanpa screenshot."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import gui_app

fails = []
ok = lambda m: print(f'  OK  {m}')
def check(cond, msg):
    if cond:
        ok(msg)
    else:
        fails.append(msg)
        print(f'  FAIL {msg}')

gui = gui_app.BotGUI()
r = gui.root
r.update_idletasks()
r.update()

# 1. tema
check(r.cget('bg') == '#0e1117', f'bg dark theme = {r.cget("bg")}')
check(r.title().startswith('AI Trading Bot'), f'title = {r.title()}')

# 2. tombol toolbar + style
check(gui.btn_start.cget('style') == 'Start.TButton', 'btn_start style Start')
check(gui.btn_stop.cget('style') == 'Stop.TButton', 'btn_stop style Stop')
check(gui.btn_restart.cget('style') == 'Restart.TButton', 'btn_restart style Restart')
check(str(gui.btn_start.cget('state')) == 'normal', 'btn_start enabled saat stopped')
check(str(gui.btn_stop.cget('state')) == 'disabled', 'btn_stop disabled saat stopped')
check(str(gui.btn_restart.cget('state')) == 'disabled', 'btn_restart disabled saat stopped')

# 3. notebook tabs
nb = None
for w in r.winfo_children():
    if isinstance(w, __import__('tkinter').ttk.Notebook):
        nb = w
        break
check(nb is not None, 'notebook ada')
if nb:
    tabs = [nb.tab(t, 'text').strip() for t in nb.tabs()]
    print(f'  tabs: {tabs}')
    check(len(tabs) >= 8, f'{len(tabs)} tabs >= 8')
check(tabs[0].startswith('🖥'), f'tab pertama Terminal = {tabs[0]}')

# 4. status label awal
check('STOPPED' in gui.lbl_state.cget('text'), f'state label = {gui.lbl_state.cget("text")}')

# 5. log console punya tag warna
for tag in ('ok', 'err', 'warn'):
    check(tag in gui.log.tag_names(), f'log tag {tag}')

# 6. simulasikan transisi state -> start (mock engine alive)
gui.runner.is_alive = lambda: True   # mock engine hidup
gui._status('running')
gui._apply_status()
r.update()
check('RUNNING' in gui.lbl_state.cget('text'), 'state RUNNING text')
check(str(gui.btn_stop.cget('state')) == 'normal', 'btn_stop enabled saat running')
check(str(gui.btn_restart.cget('state')) == 'normal', 'btn_restart enabled saat running')
check(str(gui.btn_start.cget('state')) == 'disabled', 'btn_start disabled saat running')

# 7. log berwarna (panggil _append_log dgn marker)
gui._append_log('✅ tes ok\n')
gui._append_log('❌ tes gagal\n')
r.update()

# 8. restart flow: _pending_restart flag ada
check(hasattr(gui, '_pending_restart'), '_pending_restart attr ada')
check(hasattr(gui.runner, 'detach'), 'runner.detach ada')
check(hasattr(gui.runner, '_stop_evt'), 'runner._stop_evt ada')

# 9. checkbox centang: tidak ada ttk.Checkbutton tersisa + helper _centang ada
import tkinter.ttk as _ttk
import tkinter as _tk
def _find_checkbuttons(w, out):
    for c in w.winfo_children():
        if isinstance(c, _ttk.Checkbutton):
            out.append(c)
        _find_checkbuttons(c, out)
found = []
_find_checkbuttons(r, found)
check(len(found) == 0, f'tidak ada checkbox native x tersisa ({len(found)} ditemukan)')
check(hasattr(gui, '_centang'), 'helper _centang ada')
# toggle via _centang harus mengubah var & label
v = _tk.BooleanVar(value=False)
lbl = gui._centang(r, 'TesCentang', v)
r.update()
check('☐' in lbl.cget('text'), 'label centang awal ☐')
v.set(True)
r.update()
check('☑' in lbl.cget('text') and '#2f81f7' in lbl.cget('fg'), 'label centang aktif ☑ biru')
lbl.destroy()

# 10. auto-save saat close: panggil _on_close (runner tidak hidup) -> config.yaml valid
import yaml as _yaml
gui.runner.is_alive = lambda: False   # reset mock dari test #6 (hindari dialog)
gui._on_close()   # destroy root; auto-save di dalamnya
after = open('config.yaml', encoding='utf-8').read()
c = _yaml.safe_load(after)
check(c.get('provider', {}).get('base_url') == 'http://localhost:20128/v1', 'auto-save: base_url utuh')
check(c.get('trade_management', {}).get('partial_tp_enabled') is True, 'auto-save: partial_tp utuh')
check(bool(c.get('provider', {}).get('api_key')), 'auto-save: api_key tidak hilang')
check(bool(c.get('telegram', {}).get('bot_token')), 'auto-save: bot_token tidak hilang')

try:
    r.destroy()
except Exception:
    pass

# 11. fitur auto-detect: import gateway + method ada (tak perlu GUI)
import mt5_gateway as _gw_mod
check(hasattr(_gw_mod.MT5Gateway, 'detect_terminal_path'), 'detect_terminal_path ada')
check(hasattr(_gw_mod.MT5Gateway, 'detect_broker_symbols'), 'detect_broker_symbols ada')

print()
if fails:
    print(f'UI_SMOKE=FAIL ({len(fails)})')
    sys.exit(1)
print('UI_SMOKE=OK')
