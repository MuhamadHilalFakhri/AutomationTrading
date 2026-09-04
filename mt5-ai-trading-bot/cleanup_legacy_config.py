"""Bersihkan blok flat legacy di root config.yaml.
- Pindahkan api_key root -> provider.api_key (inline key menang di server).
- Hapus semua key flat root (duplikat nested yang benar sudah ada).
- Backup dulu ke config.yaml.bak.
"""
import yaml, shutil, os

os.chdir(os.path.dirname(os.path.abspath(__file__)))
shutil.copy('config.yaml', 'config.yaml.bak')

cfg = yaml.safe_load(open('config.yaml', encoding='utf-8'))

# key flat root yang legacy (semuanya sudah ada di section nested yang benar)
FLAT_LEGACY = ['base_url', 'api_key', 'api_key_env', 'model', 'name',
               'custom_prompt_file', 'temperature', 'timeout_sec', 'max_tokens',
               'enabled', 'chart_candles', 'chart_timeframe', 'chart_width',
               'chart_height', 'indicators_overlay', 'data_mode',
               'compact_tail_last_n', 'compact_tail_tf', 'min_conf_for_entry',
               'risk_percent', 'risk_mode', 'fixed_lots', 'manual_lot', 'lot_mode',
               'min_risk_reward', 'max_lots_per_trade',
               'max_open_positions_per_symbol', 'max_correlated_positions',
               'max_spread_points', 'max_daily_loss_percent', 'cooldown_minutes',
               'chat_id', 'token_env', 'chat_id_env', 'use_bep', 'bep_aggressive',
               'bep_trigger_points', 'bep_lock_points', 'use_trailing',
               'trailing_start_points', 'trailing_step_points',
               'partial_tp_enabled', 'partial_tp_trigger_fraction',
               'partial_tp_close_fraction', 'evaluate_positions', 'magic_number',
               'slippage_points', 'pending_max_distance_points', 'min_sl_points',
               'max_sl_points', 'min_tp_points', 'max_tp_points', 'timezone',
               'host', 'port', 'active_pairs']

moved = removed = 0
if 'api_key' in cfg and not (cfg.get('provider', {}).get('api_key') or '').strip():
    cfg.setdefault('provider', {})['api_key'] = cfg.pop('api_key')
    moved += 1
for k in FLAT_LEGACY:
    if k in cfg:
        del cfg[k]
        removed += 1

with open('config.yaml', 'w', encoding='utf-8') as f:
    yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

print(f"api_key dipindah ke provider.api_key: {moved} | key flat dihapus: {removed}")
print(f"backup: config.yaml.bak")

# validasi final
c2 = yaml.safe_load(open('config.yaml', encoding='utf-8'))
import sys
sys.path.insert(0, 'server')
from config import Config
sc = Config(c2)
print("Config server OK | magic:", sc.magic_number(), "| tm partial_tp:",
      sc.get(['trade_management', 'partial_tp_enabled']),
      "| provider_api_key set:", bool(sc.provider_api_key()),
      "| telegram token set:", bool(sc.get(['telegram', 'bot_token'])))
print("top-level keys:", sorted(c2.keys()))
