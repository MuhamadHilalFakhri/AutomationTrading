"""AI agent: builds market context, renders optional chart, calls 9Router,
parses the decision JSON. ArunikaLink-style JSON contract."""

import base64
import io
import json
import os
import re
import time
import urllib.request

import numpy as np

from config import Config
from ai.prompts import build_system_prompt, build_market_context, DECISION_KEYS


class AIAgent:
    def __init__(self, cfg: Config, chart_renderer=None):
        self.cfg = cfg
        self.chart_renderer = chart_renderer  # optional callable(symbol, tf) -> PNG bytes
        self.base_url = cfg.provider_base_url().rstrip('/')
        self.api_key = cfg.provider_api_key()
        self.model = cfg.provider_model()
        self.timeout = min(cfg.provider_timeout(), 60)  # cap 60s: jangan biarkan 1 symbol memblokir loop >2 menit
        self.temperature = cfg.get(['provider', 'temperature'], 0.1)
        self.max_tokens = cfg.get(['provider', 'max_tokens'], 4096)
        self.vision_enabled = cfg.get(['provider', 'vision', 'enabled'], False)
        self.session_id = ""

    # ----------------------------------------------------------------
    def _post(self, payload: dict, retries: int = 2) -> dict:
        url = f"{self.base_url}/chat/completions"
        data = json.dumps(payload).encode('utf-8')
        last_err = None
        for attempt in range(1, retries + 1):
            req = urllib.request.Request(
                url, data=data,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                })
            t0 = time.time()
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    raw = resp.read().decode('utf-8')
                break
            except Exception as e:
                last_err = e
                dt = time.time() - t0
                print(f"[ai] attempt {attempt}/{retries} failed after {dt:.0f}s: {e}")
                if attempt < retries:
                    time.sleep(3 * attempt)
        else:
            raise RuntimeError(f"9Router unreachable after {retries} attempts: {last_err}")
        dt = time.time() - t0
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            # beberapa gateway menambah sentinel streaming "data: [DONE]"
            # setelah JSON utuh (zr dsb.) — ambil JSON pertama saja
            try:
                obj, _idx = json.JSONDecoder().raw_decode(raw.lstrip())
            except (json.JSONDecodeError, ValueError) as e:
                raise RuntimeError(f"Non-JSON response from 9Router ({dt:.1f}s): {raw[:200]}") from e
        self.session_id = obj.get('id', '')
        self.last_latency = dt
        return obj

    # ----------------------------------------------------------------
    def decide(self, symbol: str, timeframes: list[str], ohlcv: dict,
               open_positions: list[dict] = None, extra: dict = None,
               png_bytes: bytes = None) -> dict:
        """Ask the AI for a single decision on `symbol`.
        ohlcv: {tf: {'open':[], 'high':[], 'low':[], 'close':[], 'volume':[]}}
        png_bytes: optional pre-rendered chart PNG (avoids MT5 access inside
        worker threads). Falls back to chart_renderer() closure if omitted.
        Returns normalized decision dict (see DECISION_KEYS)."""
        cfg = self.cfg
        messages = []

        schema = ('{"decision":"BUY|SELL|HOLD|BUY_LIMIT|SELL_LIMIT|BUY_STOP|SELL_STOP",'
                  '"entry":<float>,"sl":<float>,"tp":<float>,'
                  '"pending_price":<float|0>,"confidence":0..1,"reason":"..."}')
        system = build_system_prompt(cfg.strategy_name(), schema)
        messages.append({"role": "system", "content": system})

        context = build_market_context(symbol, timeframes, ohlcv, cfg, extra)
        user_text = ("Analisis chart di bawah dan beri keputusan trading.\n"
                     "Keluarkan HANYA JSON sesuai format yang diminta. Jangan tulis teks lain.\n\n"
                     + context)

        use_vision = self.vision_enabled and (png_bytes is not None or self.chart_renderer is not None)
        if use_vision:
            try:
                if png_bytes is None and self.chart_renderer is not None:
                    png_bytes = self.chart_renderer(symbol, cfg.chart_timeframe(),
                                                    cfg.chart_candles())
                if png_bytes:
                    b64 = base64.b64encode(png_bytes).decode('ascii')
                    user_content = [
                        {"type": "text", "text": user_text},
                        {"type": "image_url", "image_url": {
                            "url": f"data:image/png;base64,{b64}"}},
                    ]
                else:
                    user_content = user_text
            except Exception as e:  # vision renderer failure -> fall back to text-only
                print(f"[ai] vision render failed for {symbol}, text-only: {e}")
                user_content = user_text
        else:
            user_content = user_text

        messages.append({"role": "user", "content": user_content})
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": False,
        }
        obj = self._post(payload)
        try:
            content = obj['choices'][0]['message']['content']
        except (KeyError, IndexError) as e:
            raise RuntimeError(f"Unexpected 9Router payload: {str(obj)[:300]}")

        return self._parse_decision(content, symbol)

    # ----------------------------------------------------------------
    def _parse_decision(self, content: str, symbol: str) -> dict:
        """Extract JSON from the model output (strip markdown fences if any),
        coerce types, apply guardrails that don't need market data."""
        text = content.strip()
        # strip ```json fences if present
        fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
        if fence:
            text = fence.group(1).strip()
        # find first { ... } balanced block
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end > start:
            text = text[start:end + 1]

        try:
            d = json.loads(text)
        except json.JSONDecodeError as e:
            # attempt: cut trailing garbage after last valid object
            raise ValueError(f"AI returned non-JSON for {symbol}: {e} | raw: {content[:200]}")

        if not isinstance(d, dict):
            raise ValueError(f"AI JSON not an object for {symbol}: {d}")

        decision = str(d.get('decision', 'HOLD')).upper().strip()
        if decision not in DECISION_KEYS['decision_enum']:
            raise ValueError(f"Unknown decision '{decision}' from AI for {symbol}")

        def tof(key):
            try:
                v = d.get(key, 0)
                return float(v) if v is not None else 0.0
            except (TypeError, ValueError):
                return 0.0

        out = {
            "symbol": symbol,
            "decision": decision,
            "entry": tof('entry'),
            "sl": tof('sl'),
            "tp": tof('tp'),
            "pending_price": tof('pending_price'),
            "confidence": min(max(tof('confidence'), 0.0), 1.0),
            "strategy": str(d.get('strategy', ''))[:30],
            "reason": str(d.get('reason', ''))[:500],
            "raw": content[:800],
        }
        return out
