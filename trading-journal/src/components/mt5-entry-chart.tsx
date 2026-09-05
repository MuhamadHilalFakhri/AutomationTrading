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

const ENTRY_COLOR = "#6ae4ff";

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
          color: group.pnl >= 0 ? "#22c55e" : "#ef4444",
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
        color: isBuy ? "#22c55e" : "#ef4444",
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

    // Canvas needs the resolved Next font family, not a CSS var() expression.
    const interFont = getComputedStyle(container).getPropertyValue("--font-inter").trim();
    const chart = createChart(container, {
      width: container.clientWidth,
      height: container.clientHeight,
      layout: {
        background: { type: ColorType.Solid, color: "#17202e" },
        textColor: "#cdd0d6",
        fontFamily: interFont ? `${interFont}, Inter, sans-serif` : "Inter, sans-serif",
        fontSize: 12,
        attributionLogo: true,
      },
      grid: {
        vertLines: { color: "rgba(205,208,214,.12)" },
        horzLines: { color: "rgba(205,208,214,.12)" },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: "#6ae4ff", labelBackgroundColor: "#202a3e" },
        horzLine: { color: "#6ae4ff", labelBackgroundColor: "#202a3e" },
      },
      rightPriceScale: { borderColor: "rgba(205,208,214,.15)", scaleMargins: { top: 0.08, bottom: 0.12 } },
      timeScale: {
        borderColor: "rgba(205,208,214,.15)",
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
      upColor: "#22c55e",
      downColor: "#ef4444",
      borderVisible: false,
      wickUpColor: "#22c55e",
      wickDownColor: "#ef4444",
      priceLineColor: "#6ae4ff",
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
      .map((trade) => {
        const isBuy = trade.side.toUpperCase().startsWith("BUY");
        return series.createPriceLine({
          price: trade.entry as number,
          color: isBuy ? "#22c55e" : "#ef4444",
          lineWidth: 2,
          lineStyle: LineStyle.Dashed,
          axisLabelVisible: true,
          title: `${trade.side} #${trade.ticket ?? trade.id}`,
        });
      });

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
    <div className="space-y-3 font-sans text-foreground">
      <section aria-label="Kontrol chart entry MT5" className="relative z-20 rounded-xl border border-black bg-card px-3 py-3 shadow-none sm:px-4">
        <div className="grid gap-3 xl:grid-cols-[minmax(0,1fr)_auto] xl:items-center">
          <div className="flex min-w-0 flex-col gap-3 sm:flex-row sm:items-center">
            <div className="flex min-w-0 items-center gap-2.5 sm:shrink-0">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-divider bg-transparent text-muted-foreground">
                <Server className="h-[18px] w-[18px]" />
              </span>
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <h2 className="text-sm font-medium text-foreground">Eksekusi MT5</h2>
                  <Badge variant="outline" className="h-5 border-divider bg-transparent text-[10px] text-muted-foreground">
                    {error ? <WifiOff /> : <Wifi />}
                    {error ? "TERPUTUS" : "LIVE"}
                  </Badge>
                </div>
                <p className="truncate text-xs text-muted-foreground">Candle broker dan posisi dari terminal yang sama</p>
              </div>
            </div>

            <Select value={symbol} onValueChange={(value) => value && changeSymbol(value)}>
              <SelectTrigger aria-label="Pilih symbol MT5" className="h-9 w-full rounded-full border border-signal bg-transparent! text-muted-foreground shadow-none! focus-visible:border-signal focus-visible:ring-ring sm:w-[180px]">
                <CandlestickChart className="h-3.5 w-3.5 text-muted-foreground" />
                <SelectValue><span className="font-sans font-medium">{symbol}</span></SelectValue>
              </SelectTrigger>
              <SelectContent align="start" className="min-w-[180px] border border-black! bg-card! font-sans text-muted-foreground shadow-none! backdrop-blur-none! [&_[data-slot=select-scroll-up-button]]:bg-card [&_[data-slot=select-scroll-down-button]]:bg-card">
                {symbols.map((item) => (
                  <SelectItem key={item} value={item} className="rounded-full py-2 text-muted-foreground focus:bg-transparent focus:text-muted-foreground focus:ring-1 focus:ring-ring data-highlighted:ring-1 data-highlighted:ring-ring data-selected:bg-foreground data-selected:text-black not-data-[variant=destructive]:focus:**:text-inherit">
                    {item}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex min-w-0 items-center gap-2">
            <div className="scrollbar-subtle min-w-0 flex-1 overflow-x-auto" aria-label="Pilih timeframe MT5">
              <div className="flex min-w-max items-center gap-1 rounded-full border border-divider bg-background p-1">
                {TIMEFRAMES.map((item) => (
                  <Button
                    key={item.value}
                    type="button"
                    variant="ghost"
                    size="sm"
                    aria-pressed={timeframe === item.value}
                    onClick={() => changeTimeframe(item.value)}
                    className={cn(
                      "h-7 min-w-9 rounded-full bg-transparent px-2 font-sans text-xs text-muted-foreground shadow-none hover:bg-transparent hover:text-foreground hover:ring-1 hover:ring-signal focus-visible:border-signal focus-visible:ring-ring",
                      timeframe === item.value && "bg-foreground text-black hover:bg-foreground hover:text-black",
                    )}
                  >
                    {item.label}
                  </Button>
                ))}
              </div>
            </div>
            <Button type="button" variant="outline" size="icon" className="rounded-full border-signal bg-transparent text-muted-foreground shadow-none hover:bg-transparent hover:text-foreground focus-visible:border-signal focus-visible:ring-ring" aria-label="Muat ulang chart MT5" onClick={refresh}>
              <RefreshCw className={cn(loading && "animate-spin")} />
            </Button>
          </div>
        </div>
      </section>

      <section aria-label="Chart posisi MT5" className="overflow-hidden rounded-xl border border-black bg-background shadow-none">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-b border-divider bg-card px-3 py-2 text-xs sm:px-4">
          <span className="font-semibold text-foreground">{symbol}</span>
          <span className="text-muted-foreground"><span className="tabular-nums text-foreground">{visibleTradeCount}</span> entry terlihat</span>
          <span className="text-muted-foreground"><span className="tabular-nums text-foreground">{openCount}</span> posisi terbuka</span>
          <span className="ml-auto text-muted-foreground">
            {lastUpdated ? `Diperbarui ${lastUpdated.toLocaleTimeString("id-ID", { hour12: false, timeZone: "Asia/Jakarta" })} WIB` : "Menunggu data MT5"}
          </span>
        </div>

        <div className="relative h-[600px] min-h-[500px] sm:h-[660px] lg:h-[calc(100dvh-22rem)] lg:min-h-[500px]">
          {candles.length > 0 && (
            <TradeCandlestickChart key={`${symbol}-${timeframe}`} candles={candles} trades={symbolTrades} digits={digits} />
          )}

          {loading && candles.length === 0 && (
            <div className="absolute inset-0 flex items-center justify-center bg-background" role="status">
              <div className="text-center">
                <Activity className="mx-auto h-5 w-5 animate-pulse text-signal" />
                <p className="mt-3 text-sm font-medium text-foreground">Mengambil candle dari MT5</p>
                <p className="mt-1 text-xs text-muted-foreground">Menyelaraskan entry dengan waktu broker...</p>
              </div>
            </div>
          )}

          {error && candles.length === 0 && (
            <div className="absolute inset-0 flex items-center justify-center bg-background px-5" role="alert">
              <div className="max-w-md text-center">
                <WifiOff className="mx-auto h-6 w-6 text-muted-foreground" />
                <h3 className="mt-3 text-base font-semibold text-foreground">Data MT5 belum tersedia</h3>
                <p className="mt-1.5 text-sm leading-6 text-muted-foreground">{error}</p>
                <Button type="button" variant="outline" className="mt-4 rounded-full border-signal bg-transparent text-muted-foreground shadow-none hover:bg-transparent hover:text-foreground focus-visible:border-signal focus-visible:ring-ring" onClick={refresh}>
                  <RefreshCw /> Coba lagi
                </Button>
              </div>
            </div>
          )}

          {error && candles.length > 0 && (
            <div className="absolute left-3 top-3 z-10 rounded-lg border border-black bg-card px-3 py-2 text-xs text-muted-foreground shadow-none" role="status">
              Feed tertunda · {error}
            </div>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-divider bg-card px-3 py-2 text-[11px] text-muted-foreground sm:px-4">
          <span className="inline-flex items-center gap-1 text-buy"><ArrowUp className="h-3.5 w-3.5" />BUY entry</span>
          <span className="inline-flex items-center gap-1 text-sell"><ArrowDown className="h-3.5 w-3.5" />SELL entry</span>
          <span className="inline-flex items-center gap-1.5 text-positive">
            <span className="h-2 w-2 rounded-full bg-positive" />EXIT + profit
          </span>
          <span className="inline-flex items-center gap-1.5 text-negative">
            <span className="h-2 w-2 rounded-full bg-negative" />EXIT - loss
          </span>
          <span className="ml-auto">
            Chart by{" "}
            <a
              href="https://www.tradingview.com/"
              target="_blank"
              rel="noopener nofollow noreferrer"
              className="font-medium text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
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
