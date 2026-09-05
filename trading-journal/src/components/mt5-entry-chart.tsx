"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  CandlestickSeries,
  ColorType,
  CrosshairMode,
  LineStyle,
  createChart,
  createSeriesMarkers,
  type CandlestickData,
  type IChartApi,
  type IPriceLine,
  type ISeriesApi,
  type ISeriesMarkersPluginApi,
  type SeriesMarker,
  type Time,
  type UTCTimestamp,
} from "lightweight-charts";
import { Activity, ArrowDown, ArrowUp, CandlestickChart, RefreshCw, Server, Wifi, WifiOff } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { Trade } from "@/lib/types";
import { cn } from "@/lib/utils";

interface Mt5Candle {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  tickVolume: number;
}

interface CandleResponse {
  ok: boolean;
  symbol?: string;
  timeframe?: string;
  digits?: number;
  candles?: Mt5Candle[];
  error?: string;
}

const TIMEFRAMES = [
  { value: "1", label: "1m" },
  { value: "5", label: "5m" },
  { value: "15", label: "15m" },
  { value: "60", label: "1H" },
  { value: "240", label: "4H" },
  { value: "D", label: "1D" },
  { value: "W", label: "1W" },
] as const;

type ChartTimeframe = (typeof TIMEFRAMES)[number]["value"];

const ENTRY_BUY_COLOR = "#38bdf8";
const ENTRY_SELL_COLOR = "#ff453a";

function money(value: number) {
  const sign = value > 0 ? "+" : "";
  return `${sign}$${value.toFixed(2)}`;
}

function closestCandleTime(candles: Mt5Candle[], iso: string | null): UTCTimestamp | null {
  if (!iso || candles.length === 0) return null;
  const target = new Date(iso).getTime() / 1000;
  if (!Number.isFinite(target)) return null;

  const first = candles[0].time;
  const last = candles[candles.length - 1].time;
  const typicalGap = candles.length > 1 ? Math.max(candles[1].time - first, 60) : 60;
  if (target < first - typicalGap || target > last + typicalGap) return null;

  let low = 0;
  let high = candles.length - 1;
  while (low <= high) {
    const middle = Math.floor((low + high) / 2);
    if (candles[middle].time < target) low = middle + 1;
    else high = middle - 1;
  }

  const before = candles[Math.max(high, 0)];
  const after = candles[Math.min(low, candles.length - 1)];
  return (Math.abs(before.time - target) <= Math.abs(after.time - target) ? before.time : after.time) as UTCTimestamp;
}

type MarkerGroup = {
  id: string;
  time: UTCTimestamp;
  kind: "entry" | "exit";
  side: "BUY" | "SELL" | "EXIT";
  count: number;
  weightedPrice: number;
  weight: number;
  pnl: number;
};

function buildTradeMarkers(candles: Mt5Candle[], trades: Trade[]): SeriesMarker<Time>[] {
  const groups = new Map<string, MarkerGroup>();

  const add = (
    trade: Trade,
    kind: MarkerGroup["kind"],
    iso: string | null,
    price: number | null,
  ) => {
    if (price == null || !Number.isFinite(price)) return;
    const time = closestCandleTime(candles, iso);
    if (time == null) return;
    const side = kind === "exit" ? "EXIT" : trade.side.toUpperCase().startsWith("BUY") ? "BUY" : "SELL";
    const key = `${time}-${kind}-${side}`;
    const weight = trade.lots && trade.lots > 0 ? trade.lots : 1;
    const current = groups.get(key) ?? {
      id: key,
      time,
      kind,
      side,
      count: 0,
      weightedPrice: 0,
      weight: 0,
      pnl: 0,
    };
    current.count += 1;
    current.weightedPrice += price * weight;
    current.weight += weight;
    current.pnl += trade.profit ?? 0;
    groups.set(key, current);
  };

  for (const trade of trades) {
    add(trade, "entry", trade.openTs, trade.entry);
    if (trade.status === "closed") add(trade, "exit", trade.closeTs, trade.closePrice);
  }

  return [...groups.values()]
    .sort((a, b) => Number(a.time) - Number(b.time) || (a.kind === "entry" ? -1 : 1))
    .map((group) => {
      const price = group.weightedPrice / Math.max(group.weight, 1);
      const count = group.count > 1 ? ` ×${group.count}` : "";
      if (group.kind === "exit") {
        return {
          id: group.id,
          time: group.time,
          price,
          position: "atPriceMiddle" as const,
          shape: "circle" as const,
          color: group.pnl >= 0 ? "#34d399" : "#fb7185",
          text: `EXIT${count} ${money(group.pnl)}`,
          size: 1,
        };
      }

      const isBuy = group.side === "BUY";
      return {
        id: group.id,
        time: group.time,
        price,
        position: isBuy ? ("atPriceBottom" as const) : ("atPriceTop" as const),
        shape: isBuy ? ("arrowUp" as const) : ("arrowDown" as const),
        color: isBuy ? ENTRY_BUY_COLOR : ENTRY_SELL_COLOR,
        text: `${group.side}${count} @ ${price.toFixed(2)}`,
        size: 1.4,
      };
    });
}

function TradeCandlestickChart({
  candles,
  trades,
  digits,
}: {
  candles: Mt5Candle[];
  trades: Trade[];
  digits: number;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const markersRef = useRef<ISeriesMarkersPluginApi<Time> | null>(null);
  const priceLinesRef = useRef<IPriceLine[]>([]);
  const fittedRef = useRef(false);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const chart = createChart(container, {
      width: container.clientWidth,
      height: container.clientHeight,
      layout: {
        background: { type: ColorType.Solid, color: "#070b12" },
        textColor: "#94a3b8",
        fontFamily: "var(--font-jetbrains-mono), ui-monospace, monospace",
        fontSize: 12,
        attributionLogo: true,
      },
      grid: {
        vertLines: { color: "rgba(148, 163, 184, 0.055)" },
        horzLines: { color: "rgba(148, 163, 184, 0.055)" },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: "rgba(96, 165, 250, 0.45)", labelBackgroundColor: "#1d4ed8" },
        horzLine: { color: "rgba(96, 165, 250, 0.45)", labelBackgroundColor: "#1d4ed8" },
      },
      rightPriceScale: { borderColor: "rgba(148, 163, 184, 0.15)", scaleMargins: { top: 0.08, bottom: 0.12 } },
      timeScale: {
        borderColor: "rgba(148, 163, 184, 0.15)",
        timeVisible: true,
        secondsVisible: false,
        rightOffset: 8,
        barSpacing: 8,
      },
      localization: {
        locale: "id-ID",
        timeFormatter: (time: Time) => {
          if (typeof time !== "number") return String(time);
          return new Date(time * 1000).toLocaleString("id-ID", {
            timeZone: "Asia/Jakarta",
            day: "2-digit",
            month: "short",
            hour: "2-digit",
            minute: "2-digit",
            hour12: false,
          });
        },
      },
    });

    const series = chart.addSeries(CandlestickSeries, {
      upColor: "#059669",
      downColor: "#be123c",
      borderVisible: false,
      wickUpColor: "#10b981",
      wickDownColor: "#e11d48",
      priceLineColor: "#60a5fa",
      priceFormat: { type: "price", precision: digits, minMove: 10 ** -digits },
    });
    const markers = createSeriesMarkers(series, []);

    chartRef.current = chart;
    seriesRef.current = series;
    markersRef.current = markers;

    const observer = new ResizeObserver(([entry]) => {
      chart.applyOptions({
        width: Math.floor(entry.contentRect.width),
        height: Math.floor(entry.contentRect.height),
      });
    });
    observer.observe(container);

    return () => {
      observer.disconnect();
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
      markersRef.current = null;
      priceLinesRef.current = [];
    };
  }, [digits]);

  useEffect(() => {
    const chart = chartRef.current;
    const series = seriesRef.current;
    const markers = markersRef.current;
    if (!chart || !series || !markers || candles.length === 0) return;

    const chartData: CandlestickData<Time>[] = candles.map((candle) => ({
      time: candle.time as UTCTimestamp,
      open: candle.open,
      high: candle.high,
      low: candle.low,
      close: candle.close,
    }));
    series.setData(chartData);
    markers.setMarkers(buildTradeMarkers(candles, trades));

    for (const line of priceLinesRef.current) series.removePriceLine(line);
    priceLinesRef.current = trades
      .filter((trade) => trade.status === "open" && trade.entry != null)
      .slice(0, 12)
      .map((trade) => series.createPriceLine({
        price: trade.entry as number,
        color: trade.side.toUpperCase().startsWith("BUY") ? ENTRY_BUY_COLOR : ENTRY_SELL_COLOR,
        lineWidth: 2,
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: true,
        title: `${trade.side} #${trade.ticket ?? trade.id}`,
      }));

    if (!fittedRef.current) {
      chart.timeScale().fitContent();
      fittedRef.current = true;
    }
  }, [candles, trades]);

  return <div ref={containerRef} className="h-full w-full" aria-label="Candlestick MT5 dengan marker entry dan exit" />;
}

export function Mt5EntryChart() {
  const [symbol, setSymbol] = useState("XAUUSD");
  const [timeframe, setTimeframe] = useState<ChartTimeframe>("15");
  const [candles, setCandles] = useState<Mt5Candle[]>([]);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [digits, setDigits] = useState(2);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const symbols = useMemo(() => {
    const unique = [...new Set(trades.map((trade) => trade.symbol).filter(Boolean))].sort();
    return unique.length ? unique : [symbol];
  }, [symbol, trades]);
  const symbolTrades = useMemo(
    () => trades.filter((trade) => trade.symbol === symbol),
    [symbol, trades],
  );
  const visibleTradeCount = useMemo(
    () => symbolTrades.filter((trade) => closestCandleTime(candles, trade.openTs) != null).length,
    [candles, symbolTrades],
  );
  const openCount = symbolTrades.filter((trade) => trade.status === "open").length;

  const loadTrades = useCallback(async () => {
    const response = await fetch("/api/trades?limit=2000", { cache: "no-store" });
    if (!response.ok) throw new Error("Riwayat trade tidak dapat dimuat");
    const rows = (await response.json()) as Trade[];
    setTrades(rows);
    if (rows.length && !rows.some((trade) => trade.symbol === symbol)) setSymbol(rows[0].symbol);
  }, [symbol]);

  useEffect(() => {
    let active = true;
    const run = async () => {
      try {
        await loadTrades();
      } catch (cause) {
        if (active) setError(cause instanceof Error ? cause.message : "Riwayat trade tidak dapat dimuat");
      }
    };
    void run();
    const timer = window.setInterval(run, 10000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [loadTrades]);

  useEffect(() => {
    let active = true;
    let pending = false;

    const run = async () => {
      if (pending) return;
      pending = true;
      try {
        const response = await fetch(
          `/api/market/candles?symbol=${encodeURIComponent(symbol)}&timeframe=${timeframe}&count=1000`,
          { cache: "no-store" },
        );
        const data = (await response.json()) as CandleResponse;
        if (!response.ok || !data.ok || !data.candles) throw new Error(data.error ?? "Candle MT5 tidak dapat dimuat");
        if (!active) return;
        setCandles(data.candles);
        setDigits(data.digits ?? 2);
        setLastUpdated(new Date());
        setError(null);
      } catch (cause) {
        if (active) setError(cause instanceof Error ? cause.message : "Candle MT5 tidak dapat dimuat");
      } finally {
        if (active) setLoading(false);
        pending = false;
      }
    };

    void run();
    const timer = window.setInterval(run, 5000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [refreshKey, symbol, timeframe]);

  const changeSymbol = (value: string) => {
    if (!value || value === symbol) return;
    setCandles([]);
    setError(null);
    setLoading(true);
    setSymbol(value);
  };

  const changeTimeframe = (value: ChartTimeframe) => {
    if (value === timeframe) return;
    setCandles([]);
    setError(null);
    setLoading(true);
    setTimeframe(value);
  };

  const refresh = () => {
    if (candles.length === 0) setLoading(true);
    setRefreshKey((value) => value + 1);
  };

  return (
    <div className="space-y-3">
      <section aria-label="Kontrol chart entry MT5" className="glass-panel relative z-20 rounded-xl px-3 py-3 sm:px-4">
        <div className="grid gap-3 xl:grid-cols-[minmax(0,1fr)_auto] xl:items-center">
          <div className="flex min-w-0 flex-col gap-3 sm:flex-row sm:items-center">
            <div className="flex min-w-0 items-center gap-2.5 sm:shrink-0">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-blue-400/15 bg-blue-500/10 text-blue-300">
                <Server className="h-[18px] w-[18px]" />
              </span>
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <h2 className="text-sm font-medium text-slate-100">Eksekusi MT5</h2>
                  <Badge variant="outline" className={cn(
                    "h-5 text-[10px]",
                    error ? "border-red-400/15 bg-red-500/10 text-red-300" : "border-emerald-400/15 bg-emerald-500/10 text-emerald-300",
                  )}>
                    {error ? <WifiOff /> : <Wifi />}
                    {error ? "TERPUTUS" : "LIVE"}
                  </Badge>
                </div>
                <p className="truncate text-xs text-slate-500">Candle broker dan posisi dari terminal yang sama</p>
              </div>
            </div>

            <Select value={symbol} onValueChange={(value) => value && changeSymbol(value)}>
              <SelectTrigger aria-label="Pilih symbol MT5" className="h-9 w-full border-slate-700/70 bg-slate-950/80 text-slate-200 sm:w-[180px]">
                <CandlestickChart className="h-3.5 w-3.5 text-slate-500" />
                <SelectValue><span className="font-mono font-medium">{symbol}</span></SelectValue>
              </SelectTrigger>
              <SelectContent align="start" className="solid-popover min-w-[180px]">
                {symbols.map((item) => (
                  <SelectItem key={item} value={item} className="py-2 font-mono text-slate-200 focus:bg-slate-800">
                    {item}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex min-w-0 items-center gap-2">
            <div className="scrollbar-subtle min-w-0 flex-1 overflow-x-auto" aria-label="Pilih timeframe MT5">
              <div className="flex min-w-max items-center gap-1 rounded-lg border border-white/[0.06] bg-slate-950/80 p-1">
                {TIMEFRAMES.map((item) => (
                  <Button
                    key={item.value}
                    type="button"
                    variant="ghost"
                    size="sm"
                    aria-pressed={timeframe === item.value}
                    onClick={() => changeTimeframe(item.value)}
                    className={cn(
                      "h-7 min-w-9 px-2 font-mono text-xs text-slate-500 hover:bg-slate-800 hover:text-slate-200",
                      timeframe === item.value && "bg-blue-500/15 text-blue-300 ring-1 ring-inset ring-blue-400/20 hover:bg-blue-500/20 hover:text-blue-200",
                    )}
                  >
                    {item.label}
                  </Button>
                ))}
              </div>
            </div>
            <Button type="button" variant="outline" size="icon" aria-label="Muat ulang chart MT5" onClick={refresh}>
              <RefreshCw className={cn(loading && "animate-spin")} />
            </Button>
          </div>
        </div>
      </section>

      <section aria-label="Chart posisi MT5" className="solid-data overflow-hidden rounded-xl border">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-b border-white/[0.07] bg-slate-950/90 px-3 py-2 text-xs sm:px-4">
          <span className="font-mono font-semibold text-slate-200">{symbol}</span>
          <span className="text-slate-500"><span className="font-mono text-slate-300">{visibleTradeCount}</span> entry terlihat</span>
          <span className="text-slate-500"><span className="font-mono text-amber-300">{openCount}</span> posisi terbuka</span>
          <span className="ml-auto text-slate-600">
            {lastUpdated ? `Diperbarui ${lastUpdated.toLocaleTimeString("id-ID", { hour12: false, timeZone: "Asia/Jakarta" })} WIB` : "Menunggu data MT5"}
          </span>
        </div>

        <div className="relative h-[600px] min-h-[500px] sm:h-[660px] lg:h-[calc(100dvh-22rem)] lg:min-h-[500px]">
          {candles.length > 0 && (
            <TradeCandlestickChart key={`${symbol}-${timeframe}`} candles={candles} trades={symbolTrades} digits={digits} />
          )}

          {loading && candles.length === 0 && (
            <div className="absolute inset-0 flex items-center justify-center bg-[#070b12]" role="status">
              <div className="text-center">
                <Activity className="mx-auto h-5 w-5 animate-pulse text-blue-400" />
                <p className="mt-3 text-sm font-medium text-slate-200">Mengambil candle dari MT5</p>
                <p className="mt-1 text-xs text-slate-500">Menyelaraskan entry dengan waktu broker...</p>
              </div>
            </div>
          )}

          {error && candles.length === 0 && (
            <div className="absolute inset-0 flex items-center justify-center bg-[#070b12] px-5" role="alert">
              <div className="max-w-md text-center">
                <WifiOff className="mx-auto h-6 w-6 text-red-300" />
                <h3 className="mt-3 text-base font-semibold text-slate-100">Data MT5 belum tersedia</h3>
                <p className="mt-1.5 text-sm leading-6 text-slate-400">{error}</p>
                <Button type="button" variant="outline" className="mt-4" onClick={refresh}>
                  <RefreshCw /> Coba lagi
                </Button>
              </div>
            </div>
          )}

          {error && candles.length > 0 && (
            <div className="absolute left-3 top-3 z-10 rounded-lg border border-amber-400/15 bg-slate-950/95 px-3 py-2 text-xs text-amber-200 shadow-lg" role="status">
              Feed tertunda · {error}
            </div>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-white/[0.07] bg-slate-950/90 px-3 py-2 text-[11px] text-slate-500 sm:px-4">
          <span className="inline-flex items-center gap-1 text-sky-300"><ArrowUp className="h-3.5 w-3.5" />BUY entry</span>
          <span className="inline-flex items-center gap-1 text-[#ff6b63]"><ArrowDown className="h-3.5 w-3.5" />SELL entry</span>
          <span className="inline-flex items-center gap-1.5 text-slate-500">
            <span className="h-2 w-2 rounded-full bg-emerald-400" />
            <span className="-ml-2 h-2 w-2 translate-x-1.5 rounded-full bg-rose-400" />
            EXIT profit/loss
          </span>
          <span className="ml-auto">
            Chart by{" "}
            <a
              href="https://www.tradingview.com/"
              target="_blank"
              rel="noopener nofollow noreferrer"
              className="font-medium text-blue-400 transition-colors hover:text-blue-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400/70"
            >
              TradingView Lightweight Charts™
            </a>
            {" "}· Data OHLC dari MT5
          </span>
        </div>
      </section>
    </div>
  );
}
