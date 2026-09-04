"""Config loader with dotted-path get()."""

import os

import yaml


class Config:
    def __init__(self, path: str = None):
        path = path or os.environ.get("MT5AI_CONFIG", "config.yaml")
        if not os.path.isabs(path):
            path = os.path.abspath(path)
        self.path = path
        with open(path, 'r', encoding='utf-8') as f:
            self.data = yaml.safe_load(f) or {}
        # base dir: folder yang memuat config (project root); frozen-safe
        self._base_dir = os.path.dirname(path)

    def reload(self) -> bool:
        """Baca ulang config.yaml dari disk (dipanggil engine tiap tick supaya
        perubahan dari GUI 'Simpan' langsung apply tanpa restart bot).
        Kalau file sedang ditulis/rusak -> pertahankan data lama."""
        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                d = yaml.safe_load(f)
            if isinstance(d, dict) and d:
                self.data = d
                return True
        except Exception:
            pass
        return False

    def get(self, path: list, default=None):
        node = self.data
        for key in path:
            if not isinstance(node, dict) or key not in node:
                return default
            node = node[key]
        return node

    # ---- provider ----
    def provider_base_url(self) -> str:
        return self.get(['provider', 'base_url'], 'http://localhost:20128/v1')

    def provider_api_key(self) -> str:
        # inline key menang (GUI menyimpannya di config.yaml), fallback ke env var
        inline = str(self.get(['provider', 'api_key'], '') or '').strip()
        if inline:
            return inline
        env = self.get(['provider', 'api_key_env'],
                       'HERMES_CUSTOM_LOCALHOST_20128_API_KEY')
        return os.environ.get(env, '')

    def provider_model(self) -> str:
        return self.get(['provider', 'model'], 'COMBO')

    def provider_timeout(self) -> int:
        return int(self.get(['provider', 'timeout_sec'], 120))

    def chart_timeframe(self) -> str:
        return self.get(['provider', 'vision', 'chart_timeframe'], 'M5')

    def chart_candles(self) -> int:
        return int(self.get(['provider', 'vision', 'chart_candles'], 120))

    # ---- strategy ----
    def strategy_name(self) -> str:
        return self.get(['strategy', 'name'], 'scalping')

    def strategy_timeframes(self) -> list:
        return self.get(['strategy', 'timeframes'], ['M1', 'M5'])

    def custom_prompt_file(self) -> str:
        return self.get(['strategy', 'custom_prompt_file'], 'custom.txt')

    # ---- execution ----
    def magic_number(self) -> int:
        return int(self.get(['execution', 'magic_number'], 20250903))

    def risk_percent(self) -> float:
        return float(self.get(['execution', 'risk_percent'], 0.01))

    def risk_mode(self) -> str:
        return self.get(['execution', 'risk_mode'], 'percent')

    def fixed_lots(self) -> float:
        return float(self.get(['execution', 'fixed_lots'], 0.01))

    def min_conf(self) -> float:
        return float(self.get(['execution', 'min_conf_for_entry'], 0.55))

    def max_spread(self) -> float:
        return float(self.get(['execution', 'max_spread_points'], 50))

    def max_spread_for(self, symbol: str) -> float:
        """Per-symbol override; None/0 = unlimited (bebas spread)."""
        o = self.get(['execution', 'max_spread_overrides'], {}) or {}
        if symbol in o:
            v = o[symbol]
            if v in (None, 0, 'unlimited'):
                return None  # unlimited
            return float(v)
        return self.max_spread()

    def pending_max_distance_for(self, symbol: str) -> float:
        """Per-symbol override jarak pending order."""
        o = self.get(['execution', 'pending_max_distance_overrides'], {}) or {}
        if symbol in o:
            v = o[symbol]
            if v in (None, 0, 'unlimited'):
                return float('inf')
            return float(v)
        return float(self.get(['execution', 'pending_max_distance_points'], 5000))

    def cooldown_minutes(self) -> float:
        return float(self.get(['execution', 'cooldown_minutes'], 3))

    def slippage(self) -> int:
        return int(self.get(['execution', 'slippage_points'], 20))

    def max_positions_per_symbol(self) -> int:
        return int(self.get(['execution', 'max_open_positions_per_symbol'], 1))

    def rr_for(self, symbol: str) -> dict:
        """Ambil RR & target pips per symbol (adaptif, bukan rata-rata)."""
        o = self.get(['execution', 'rr_by_symbol'], {}) or {}
        if symbol in o:
            return o[symbol]
        # default untuk pair tidak tercantum
        return {"min_rr": 1.5, "target_pips_min": 30, "target_pips_max": 100}

    def max_daily_loss_percent(self) -> float:
        return float(self.get(['execution', 'max_daily_loss_percent'], 5.0))

    def allowed_order_types(self) -> list:
        return self.get(['execution', 'allowed_order_types'],
                        ['market', 'pending'])

    # ---- trade management ----
    def tm_enabled(self) -> bool:
        return bool(self.get(['trade_management', 'enabled'], True))

    def tm_use_bep(self) -> bool:
        return bool(self.get(['trade_management', 'use_bep'], True))

    def tm_bep_trigger(self) -> float:
        return float(self.get(['trade_management', 'bep_trigger_points'], 50))

    def tm_bep_lock(self) -> float:
        return float(self.get(['trade_management', 'bep_lock_points'], 5))

    def tm_use_trailing(self) -> bool:
        return bool(self.get(['trade_management', 'use_trailing'], True))

    def tm_trailing_start(self) -> float:
        return float(self.get(['trade_management', 'trailing_start_points'], 120))

    def tm_trailing_step(self) -> float:
        return float(self.get(['trade_management', 'trailing_step_points'], 25))

    def tm_evaluate_positions(self) -> bool:
        return bool(self.get(['trade_management', 'evaluate_positions'], True))

    def tm_position_eval_interval_min(self) -> float:
        return float(self.get(['trade_management', 'position_eval_interval_min'], 15))

    # ---- active pairs (dipilih via Telegram /pilihpair) ----
    _ACTIVE_PAIRS_FILE = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        '.active_pairs.json')

    def _state_path(self, name: str) -> str:
        """State file di folder yang sama dengan config.yaml (frozen-safe)."""
        return os.path.join(self._base_dir, name)

    def active_pairs(self) -> list:
        """Pair aktif yang di-scan. Kosong = semua symbol di mt5.symbols."""
        # state file menang (hasil toggle Telegram), fallback ke config.yaml
        try:
            import json
            with open(self._state_path('.active_pairs.json')) as f:
                return json.load(f)
        except Exception:
            return list(self.get(['telegram', 'active_pairs'], []) or [])

    def set_active_pairs(self, pairs: list) -> None:
        """Simpan pilihan pair aktif (persist, tahan restart)."""
        import json
        with open(self._state_path('.active_pairs.json'), 'w') as f:
            json.dump(list(pairs), f)

    # ---- lot mode (auto | manual), toggle via Telegram /lot ----
    def _lot_file(self) -> str:
        return self._state_path('.lot_mode.json')

    def lot_mode(self) -> str:
        """Mode lot: 'auto' (risk-based sesuai market) atau 'manual' (lot tetap)."""
        try:
            with open(self._lot_file()) as f:
                m = json.load(f).get('mode', '')
            if m in ('auto', 'manual'):
                return m
        except Exception:
            pass
        return str(self.get(['execution', 'lot_mode'], 'auto'))

    def manual_lot(self) -> float:
        """Lot tetap saat mode manual (dari state file atau config)."""
        try:
            with open(self._lot_file()) as f:
                v = float(json.load(f).get('lot', 0))
            if v > 0:
                return v
        except Exception:
            pass
        return float(self.get(['execution', 'manual_lot'], 0.01))

    def set_lot(self, mode: str, lot: float = None) -> None:
        """Simpan lot mode (persist, tahan restart)."""
        import json
        data = {'mode': mode}
        if lot is not None:
            data['lot'] = float(lot)
        else:
            try:
                with open(self._lot_file()) as f:
                    prev = json.load(f)
                if 'lot' in prev:
                    data['lot'] = prev['lot']
            except Exception:
                pass
        with open(self._lot_file(), 'w') as f:
            json.dump(data, f)
