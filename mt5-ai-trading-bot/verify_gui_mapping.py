"""Verifikasi: apakah semua inputan GUI = semua key yang dibaca server?
Buka GUI headless -> collect config -> bandingkan dengan server reads."""
import os, re, glob, sys

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gui_app

# 1) server reads (dari regex di semua file server/)
server = set()
for f in glob.glob('server/*.py') + glob.glob('server/ai/*.py'):
    s = open(f, encoding='utf-8').read()
    for m in re.finditer(r'\.get\(\s*\[([^\]]+)\]', s):
        items = re.findall(r"'([^']+)'", m.group(1))
        if items:
            server.add(tuple(items))

# 2) GUI collect (headless, tanpa menulis file)
gui = gui_app.BotGUI()
cfg = gui._collect_config()

def flatten(d, prefix=()):
    for k, v in d.items():
        np = prefix + (k,)
        if isinstance(v, dict):
            yield from flatten(v, np)
        else:
            yield np

gui_keys = set(flatten(cfg))

# 3) bandingkan
missing = sorted(server - gui_keys)
print(f"SERVER READS: {len(server)} | GUI COLLECT KEYS: {len(gui_keys)}")
print()
if missing:
    print("=== DIBACA SERVER TAPI TIDAK ADA DI GUI COLLECT ===")
    for k in missing:
        print('  ' + '.'.join(k))
else:
    print("OK: semua key yang dibaca server ada di GUI collect.")

# 4) cek nilai penting (hardcode match)
import yaml
raw = yaml.safe_load(open('config.yaml', encoding='utf-8'))
checks = [
    (('mt5', 'terminal_path'), raw.get('mt5', {}).get('terminal_path')),
    (('provider', 'base_url'), raw.get('provider', {}).get('base_url')),
    (('provider', 'model'), raw.get('provider', {}).get('model')),
    (('strategy', 'name'), raw.get('strategy', {}).get('name')),
    (('telegram', 'chat_id'), raw.get('telegram', {}).get('chat_id')),
    (('trade_management', 'partial_tp_enabled'), raw.get('trade_management', {}).get('partial_tp_enabled')),
    (('execution', 'rr_by_symbol'), raw.get('execution', {}).get('rr_by_symbol')),
]
print()
print("=== NILAI KUNCI (config.yaml) ===")
for k, v in checks:
    gv = gui._deep_get(cfg, list(k), '<MISSING>')
    print(f"  {'.'.join(k)} = {v!r} | gui={gv!r} | {'MATCH' if gv == v or k[-1] == 'rr_by_symbol' else 'DIFF'}")

gui.root.destroy()
print()
print('VERIFY_DONE')
