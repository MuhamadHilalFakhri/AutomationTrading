"""Chart renderer: draws an MT5 OHLCV series to a PNG for the vision model.

Keeps it dependency-light: pure matplotlib, candlestick drawing, optional
EMA(20/50) + Bollinger overlay + latest swing levels. Output PNG bytes.
"""

import io

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
import numpy as np

_BULL = '#26a69a'
_BEAR = '#ef5350'


def _ema(values, period):
    if len(values) < period:
        return None
    alpha = 2.0 / (period + 1.0)
    out = [values[0]]
    for v in values[1:]:
        out.append(out[-1] + alpha * (v - out[-1]))
    return np.asarray(out)


def _sma(values, period):
    if len(values) < period:
        return None
    return np.convolve(values, np.ones(period) / period, mode='valid')


def _rsi(closes, period=14):
    """RSI Wilder. Return array sepanjang input (NaN di awal)."""
    c = np.asarray(closes, float)
    if len(c) < period + 1:
        return None
    delta = np.diff(c)
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    avg_gain = np.array([gain[:period].mean()])
    avg_loss = np.array([loss[:period].mean()])
    for i in range(period, len(delta)):
        avg_gain = np.append(avg_gain, (avg_gain[-1] * (period - 1) + gain[i]) / period)
        avg_loss = np.append(avg_loss, (avg_loss[-1] * (period - 1) + loss[i]) / period)
    rs = avg_gain / np.where(avg_loss == 0, 1e-12, avg_loss)
    rsi = 100 - 100 / (1 + rs)
    out = np.full(len(c), np.nan)
    out[period:] = rsi
    return out


def _macd(closes, fast=12, slow=26, signal=9):
    """MACD line, signal line, histogram."""
    c = np.asarray(closes, float)
    if len(c) < slow + signal:
        return None, None, None
    def ema_arr(v, p):
        alpha = 2.0 / (p + 1.0)
        out = [v[0]]
        for x in v[1:]:
            out.append(out[-1] + alpha * (x - out[-1]))
        return np.asarray(out)
    ema_f = ema_arr(c, fast)
    ema_s = ema_arr(c, slow)
    macd_line = ema_f - ema_s
    sig = ema_arr(macd_line, signal)
    hist = macd_line - sig
    return macd_line, sig, hist


def _stochastic(h, l, c, k_period=14, d_period=3):
    """Stochastic Oscillator %K, %D."""
    h, l, c = np.asarray(h, float), np.asarray(l, float), np.asarray(c, float)
    n = len(c)
    if n < k_period + d_period:
        return None, None
    k = np.full(n, np.nan)
    for i in range(k_period - 1, n):
        hh = h[i - k_period + 1:i + 1].max()
        ll = l[i - k_period + 1:i + 1].min()
        rng = hh - ll
        k[i] = 100 * (c[i] - ll) / (rng if rng > 1e-12 else 1e-12)
    d = np.full(n, np.nan)
    valid = ~np.isnan(k)
    kv = k[valid]
    if len(kv) >= d_period:
        dv = np.convolve(kv, np.ones(d_period) / d_period, mode='valid')
        idx = np.where(valid)[0][d_period - 1:]
        d[idx] = dv
    return k, d


class ChartRenderer:
    def __init__(self, width=1400, height=800, overlay=True, session_id=None):
        self.width = width
        self.height = height
        self.overlay = overlay
        self.session_id = session_id or ""

    def render(self, symbol: str, timeframe: str, ohlcv: dict,
               levels: dict = None) -> bytes:
        """ohlcv: {'open':[], 'high':[], 'low':[], 'close':[], 'volume':[]}"""
        o = ohlcv.get('open') or []
        h = ohlcv.get('high') or []
        l = ohlcv.get('low') or []
        c = ohlcv.get('close') or []
        v = ohlcv.get('volume') or [0] * len(c)
        n = len(c)
        if n < 5:
            raise ValueError(f"Not enough bars to render {symbol} ({n})")

        o, h, l, c = np.asarray(o, float), np.asarray(h, float), \
            np.asarray(l, float), np.asarray(c, float)
        dpi = 100
        fig_w = max(8, self.width / dpi)
        fig_h = max(4, self.height / dpi)
        fig, (axp, axv, axrsi, axmacd, axstoch) = plt.subplots(
            5, 1, figsize=(fig_w, fig_h), dpi=dpi, sharex=True,
            gridspec_kw={'height_ratios': [4, 1, 1.2, 1.2, 1.0], 'hspace': 0.08})
        fig.patch.set_facecolor('#0e1117')
        for ax in (axp, axv, axrsi, axmacd, axstoch):
            ax.set_facecolor('#0e1117')
            ax.tick_params(colors='#8b949e', labelsize=7)
            for sp in ax.spines.values():
                sp.set_color('#30363d')
        axp.grid(True, color='#21262d', linewidth=0.5, alpha=0.6)
        axp.set_title(f"{symbol} {timeframe}  |  {self.session_id}",
                      color='#e6edf3', fontsize=9, loc='left')

        x = np.arange(n)
        # candles
        for i in range(n):
            color = _BULL if c[i] >= o[i] else _BEAR
            axp.plot([x[i], x[i]], [l[i], h[i]], color=color, linewidth=0.7,
                     solid_capstyle='round')
            lo, hi = min(o[i], c[i]), max(o[i], c[i])
            if hi - lo < 1e-12:
                hi = lo + max(np.ptp(c) * 0.002, 1e-12)
            axp.add_patch(mpatches.Rectangle((x[i] - 0.35, lo), 0.7, hi - lo,
                                             facecolor=color, edgecolor=color,
                                             linewidth=0.4))
        # overlays
        if self.overlay:
            ema20 = _ema(c, 20)
            if ema20 is not None:
                axp.plot(x, ema20, color='#f0b90b', linewidth=1.0,
                         label='EMA20', alpha=0.85)
            ema50 = _ema(c, 50)
            if ema50 is not None:
                axp.plot(x, ema50, color='#e14b8a', linewidth=1.0,
                         label='EMA50', alpha=0.85)
            if n >= 20:
                mid = _sma(c, 20)
                if mid is not None:
                    sd = np.array([np.std(c[i - 19:i + 1]) for i in range(19, n)])
                    off = np.arange(19, n)
                    axp.fill_between(off, mid - 2 * sd, mid + 2 * sd,
                                     color='#4c8bf5', alpha=0.10)
        # swing high/low markers (last 10 bars lookback 5)
        lvl = levels or {}
        for kind, price in (('res', lvl.get('resistance')), ('sup', lvl.get('support'))):
            if price:
                axp.axhline(price, color='#ffa657' if kind == 'res' else '#56d364',
                            linewidth=1.0, linestyle='--', alpha=0.7)

        axp.legend(loc='upper left', fontsize=6, facecolor='#161b22',
                   edgecolor='#30363d', labelcolor='#8b949e')
        axp.set_xlim(-1, n + 1)

        # volume
        vc = [_BULL if c[i] >= o[i] else _BEAR for i in range(n)]
        axv.bar(x, v, color=vc, width=0.7, alpha=0.55)
        axv.set_facecolor('#0e1117')
        axv.set_ylim(0, max(v) * 1.15 if max(v) > 0 else 1)

        # ---- RSI (14) ----
        rsi = _rsi(c, 14)
        if rsi is not None:
            axrsi.plot(x, rsi, color='#c9a1ff', linewidth=1.0, label='RSI(14)')
            axrsi.axhline(70, color='#ef5350', linewidth=0.7, linestyle='--', alpha=0.6)
            axrsi.axhline(30, color='#26a69a', linewidth=0.7, linestyle='--', alpha=0.6)
            axrsi.axhline(50, color='#8b949e', linewidth=0.5, linestyle=':', alpha=0.4)
            axrsi.set_ylim(0, 100)
            axrsi.set_ylabel('RSI', color='#8b949e', fontsize=6)
            axrsi.legend(loc='upper left', fontsize=5, facecolor='#161b22',
                         edgecolor='#30363d', labelcolor='#8b949e')

        # ---- MACD (12,26,9) ----
        macd_line, macd_sig, macd_hist = _macd(c)
        if macd_line is not None:
            axmacd.plot(x, macd_line, color='#58a6ff', linewidth=1.0, label='MACD')
            axmacd.plot(x, macd_sig, color='#f0b90b', linewidth=1.0, label='Signal')
            colors = [_BULL if h >= 0 else _BEAR for h in macd_hist]
            axmacd.bar(x, macd_hist, color=colors, width=0.7, alpha=0.5)
            axmacd.axhline(0, color='#8b949e', linewidth=0.5, linestyle=':', alpha=0.4)
            axmacd.set_ylabel('MACD', color='#8b949e', fontsize=6)
            axmacd.legend(loc='upper left', fontsize=5, facecolor='#161b22',
                          edgecolor='#30363d', labelcolor='#8b949e')

        # ---- Stochastic (14,3) ----
        st_k, st_d = _stochastic(h, l, c)
        if st_k is not None:
            axstoch.plot(x, st_k, color='#c9a1ff', linewidth=1.0, label='%K')
            axstoch.plot(x, st_d, color='#f0b90b', linewidth=1.0, label='%D')
            axstoch.axhline(80, color='#ef5350', linewidth=0.7, linestyle='--', alpha=0.6)
            axstoch.axhline(20, color='#26a69a', linewidth=0.7, linestyle='--', alpha=0.6)
            axstoch.set_ylim(0, 100)
            axstoch.set_ylabel('Stoch', color='#8b949e', fontsize=6)
            axstoch.legend(loc='upper left', fontsize=5, facecolor='#161b22',
                           edgecolor='#30363d', labelcolor='#8b949e')

        buf = io.BytesIO()
        fig.savefig(buf, format='png', facecolor=fig.get_facecolor())
        plt.close(fig)
        return buf.getvalue()
