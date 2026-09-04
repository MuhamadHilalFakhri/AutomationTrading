"""Prompt builders — adaptive multi-strategy (SMC/ICT/S&D/trend/breakout/scalping).

Decision JSON contract (single object, no extra text):
  {"decision": "BUY|SELL|HOLD|BUY_LIMIT|SELL_LIMIT|BUY_STOP|SELL_STOP",
   "entry": <float>, "sl": <float>, "tp": <float>,
   "pending_price": <float|0>, "confidence": 0..1,
   "strategy": "<nama strategi>", "reason": "..."}
"""

import os

DECISION_KEYS = {
    "decision_enum": ["BUY", "SELL", "HOLD", "BUY_LIMIT", "SELL_LIMIT",
                      "BUY_STOP", "SELL_STOP", "CLOSE"],
}

# Adaptive strategy: AI memilih pendekatan terbaik untuk kondisi market saat ini
ADAPTIVE_STRATEGY = """\
ANDA ADALAH TRADER ADAPTIVE YANG MENGUASAI BANYAK METODE. Analisis struktur market,
lalu pilih SATU strategi yang PALING cocok dengan kondisi market SAAT INI.
Jangan terpaku satu gaya — sesuaikan dengan apa yang sedang terjadi.

STRATEGI YANG TERSEDIA (pilih sesuai kondisi):

1) SMC (Smart Money Concepts):
   - Order Block: area akumulasi sebelum impulse. Entry saat retest OB.
   - FVG (Fair Value Gap): gap imbalance 3-candle, entry saat harga kembali mengisi.
   - Breaker Block: OB yang sudah break, jadi support/resistance baru.
   - Liquidity Sweep: ambil likuiditas di atas high/bawah low dulu, baru reversal.
   - BOS/CHoCH (Break of Structure / Change of Character): konfirmasi arah.

2) ICT (Inner Circle Trader):
   - Displacement (candle besar + volume) sebagai tanda perpindahan uang.
   - MSS (Market Structure Shift) setelah liquidity grab.
   - Killzone (London/NY open): entry di jam likuiditas tinggi.
   - Premium/Discount zone dari range (Fibonacci).
   - Power of 3: Accumulation - Manipulation - Distribution.

3) Supply & Demand:
   - Zone supply (atas) / demand (bawah) yang masih fresh (belum dites balik).
   - Entry di tepi zone, SL di luar zone.
   - Cari zone yang baru terbentuk (fresh), bukan yang sudah diuji berkali-kali.

4) Trend Following:
   - Ikut arah trend H1/H4 (TF besar). Entry saat retrace/EMA pullback.
   - Gunakan EMA20/EMA50 sebagai support/resistance dinamis.
   - Jangan melawan trend dominan.

5) Breakout:
   - Range/consolidation sempit lalu volume + momentum pecahkan.
   - Entry saat break + retest, atau pakai STOP order di atas/bawah level.
   - Waspada false break — tunggu konfirmasi candle close.

6) Scalping:
   - Momentum M1/M5, target cepat. Cocok saat market trending pendek / volatil.

PILIH STRATEGI BERDASARKAN:
- Trending jelas + ada OB/FVG → SMC/ICT/Trend Following.
- Market di range + zone jelas → Supply/Demand atau Breakout.
- Volatilitas tinggi + momentum → Scalping.
- Jika tidak ada setup jelas → HOLD.

GUNAKAN INDIKATOR UNTUK KONFIRMASI EKSEKUSI:
- RSI(14): overbought >70 (hindari BUY), oversold <30 (hindari SELL).
  Divergence RSI vs harga = sinyal reversal kuat.
- MACD(12,26,9): hist >0 & line > signal = momentum bullish; crossover = konfirmasi arah.
- Stochastic(14,3): %K cross %D dari <20 = buy signal; dari >80 = sell signal.
- EMA20 vs EMA50: EMA20>EMA50 = trend naik. Harga di atas keduanya = bullish bias.
- Konfirmasi entry = struktur market (SMC/ICT) + indikator searah.
  Jika struktur bullish tapi RSI overbought + Stoch overbought → tunggu pullback (HOLD/pending limit).
  Jika struktur dan momentum bertentangan → turunkan confidence atau HOLD.

TARGET PROFIT (PENTING — SESUAIKAN DENGAN PAIR & MARKET, JANGAN DISAMARATAKAN):
- Setiap pair punya volatilitas (ATR) berbeda. XAUUSD & NAS100.r bisa bergerak
  100-500 pips; EURUSD/GBPUSD/USDJPY/AUDUSD 35-150 pips.
- Data konteks memberi tahu target_pips_min & target_pips_max UNTUK PAIR INI.
  Gunakan angka itu sebagai panduan TP (jangan terlalu kecil/terlalu besar dari itu).
- RR minimal 1:1.5 TETAPI pair volatile (XAUUSD/NAS100.r) usahakan 1:2+.
- Sesuaikan TP dengan volatilitas & level berikutnya (resistance/supply),
  jangan dipaksakan jika jarak tidak realistis untuk timeframe tsb.
"""

# Legacy strategy styles (tetap ada untuk backward-compat)
STRATEGY_STYLE = {
    "adaptive": ADAPTIVE_STRATEGY,
    "scalping": (
        "Strategi: SCALPING volatilitas M1/M5 dengan konfirmasi M15 bila tersedia.\n"
        "Cari momentum candle terkini dan level harga terdekat. Target 50-70 pips.\n"
        "Hindari spread lebar (berita). Prioritas: akurasi > frekuensi.\n"
        "Minimal risk:reward 1:1.5, usahakan 1:2."
    ),
    "snd": (
        "Strategi: SUPPLY & DEMAND + trend multi-timeframe.\n"
        "Cari confluence: TF besar untuk bias, TF kecil untuk trigger entry.\n"
        "Hindari entry di tengah range. Fokus R:R >= 1.2."
    ),
    "trend": (
        "Strategi: TREND FOLLOWING, ikut arah trend H1/H4 (atau TF terbesar yang tersedia).\n"
        "Entry saat retrace kecil pada M1/M5. JANGAN melawan trend utama.\n"
        "Jika arah tidak jelas -> HOLD."
    ),
    "custom": (
        "Gunakan prompt custom pengguna di bawah ini sebagai instruksi utama.\n"
        "INSTRUKSI CUSTOM PENGGUNA:\n{custom}"
    ),
}

CONTRACT_RULES = """\
Aturan keluaran:
- decision: BUY / SELL / HOLD (market order) atau BUY_LIMIT / SELL_LIMIT / BUY_STOP / SELL_STOP (pending order).
- entry/sl/tp = HARGA absolut (bukan offset/jarak).
- pending_price = harga pending order. WAJIB diisi jika decision pending; 0 jika market.
- confidence 0..1 (0.0 = sangat ragu, 1.0 = sangat yakin).
- strategy: nama strategi yang kamu pilih (mis. "SMC", "ICT", "Supply/Demand", "Trend", "Breakout", "Scalping").
- reason: JELASKAN DALAM BAHASA INDONESIA. Sebutkan alasan entry, struktur market, level kunci, dan kenapa pilih strategi ini. Maksimal 250 karakter, ASCII aman.
- SELALU isi entry, sl, tp walaupun konservatif.
- RISK:REWARD WAJIB minimal 1:1.5, ideal 1:2 atau lebih. Jika tidak bisa dapat RR 1:1.5, jangan entry (HOLD).
- Perhitungkan spread dan volatilitas saat menentukan sl/tp.
- Gunakan pending order (LIMIT/STOP) jika entry terbaik BUKAN di harga saat ini.
- Jangan tulis apa pun di luar JSON. Tidak ada komentar, tidak ada blok kode.
"""


def load_custom_prompt(path: str) -> str:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except OSError:
        return ""


def build_system_prompt(strategy: str, schema_hint: str = "",
                        custom_prompt: str = "") -> str:
    style = STRATEGY_STYLE.get(strategy, STRATEGY_STYLE['adaptive'])
    if '{custom}' in style:
        style = style.replace('{custom}', custom_prompt or '(kosong)')
    fallback = ('{"decision":"...","entry":<float>,"sl":<float>,"tp":<float>,'
                '"pending_price":<float|0>,"confidence":0..1,'
                '"strategy":"...","reason":"..."}')
    return (f"Anda adalah asisten trading yang disiplin dan konservatif.\n\n"
            f"{style}\n\n"
            f"KELUARAN WAJIB HANYA SATU OBJEK JSON VALID dengan kunci:\n"
            f"{schema_hint or fallback}\n\n"
            f"{CONTRACT_RULES}")


def build_market_context(symbol: str, timeframes: list, ohlcv: dict,
                         cfg=None, extra: dict = None) -> str:
    """Compact OHLC text per timeframe for the AI prompt."""
    extra = extra or {}
    lines = [f"SYMBOL: {symbol}",
             f"WAKTU: {extra.get('server_time', '')}",
             f"AKUN: balance={extra.get('balance', 0)}, equity={extra.get('equity', 0)}, "
             f"currency={extra.get('currency', 'USD')}, type={extra.get('account_type', '')}"]
    if extra.get('spread_points') is not None:
        lines.append(f"SPREAD sekarang: {extra['spread_points']} points")
    if extra.get('atr_points') is not None:
        lines.append(f"ATR (volatilitas) sekarang: {extra['atr_points']:.1f} points")
    # --- RR & TARGET PIPS ADAPTIF PER PAIR ---
    if cfg:
        rr_cfg = cfg.rr_for(symbol)
        lines.append(f"TARGET PIPS untuk {symbol}: min={rr_cfg.get('target_pips_min', 30)}, "
                     f"max={rr_cfg.get('target_pips_max', 100)}")
        lines.append(f"RR MINIMAL untuk {symbol}: {rr_cfg.get('min_rr', 1.5)}")
    ind = extra.get('indicators') or {}
    if ind:
        lines.append("INDIKATOR MOMENTUM (nilai terkini, untuk konfirmasi entry):")
        parts = []
        if 'ema20' in ind:
            parts.append(f"EMA20={ind['ema20']:.5f}")
        if 'ema50' in ind:
            parts.append(f"EMA50={ind['ema50']:.5f}")
        if 'rsi14' in ind:
            parts.append(f"RSI14={ind['rsi14']:.1f}")
        if 'macd' in ind:
            parts.append(f"MACD={ind['macd']:.6f} signal={ind['macd_signal']:.6f} hist={ind['macd_hist']:.6f}")
        if 'stoch_k' in ind:
            parts.append(f"Stoch %K={ind['stoch_k']:.1f} %D={ind['stoch_d']:.1f}")
        if parts:
            lines.append("  " + " | ".join(parts))
            lines.append("  RSI >70 overbought / <30 oversold. MACD hist >0 bullish. Stoch >80 overbought / <20 oversold. EMA20>EMA50 bullish.")
    if extra.get('open_positions'):
        lines.append("POSISI TERBUKA (sym side lots entry sl tp profit):")
        for p in extra['open_positions']:
            lines.append(
                f"  {p.get('symbol')} {p.get('type')} {p.get('volume')} "
                f"entry={p.get('price_open')} sl={p.get('sl')} tp={p.get('tp')} "
                f"profit={p.get('profit')}")
    else:
        lines.append("POSISI TERBUKA: tidak ada")

    tail_tf = cfg.get(['strategy', 'compact_tail_tf'], 'M5') if cfg else 'M5'
    n_default = cfg.get(['strategy', 'compact_tail_last_n'], 30) if cfg else 30

    for tf in timeframes:
        d = ohlcv.get(tf)
        if not d or not d.get('close'):
            continue
        closes = d['close']
        n = max(n_default, 60) if tf == tail_tf else n_default
        n = min(n, len(closes))
        tail_start = len(closes) - n
        lines.append(f"\n--- DATA {tf} (OHLCV, terbaru di baris terakhir) ---")
        for i in range(tail_start, len(closes)):
            t = d.get('time', [])
            ts = t[i] if i < len(t) else str(i)
            lines.append(
                f"{ts} | O:{d['open'][i]:.5f} H:{d['high'][i]:.5f} "
                f"L:{d['low'][i]:.5f} C:{d['close'][i]:.5f} V:{d['volume'][i]:.0f}")
    return "\n".join(lines)
