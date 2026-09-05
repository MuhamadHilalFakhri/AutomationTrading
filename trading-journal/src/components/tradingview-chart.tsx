"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Activity, CandlestickChart, RefreshCw, Search } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

type MarketPair = {
  symbol: string;
  label: string;
  description: string;
  group: "Metal" | "Forex" | "Crypto" | "Indeks";
};

const MARKET_PAIRS: MarketPair[] = [
  { symbol: "OANDA:XAUUSD", label: "XAU/USD", description: "Gold / US Dollar", group: "Metal" },
  { symbol: "OANDA:XAGUSD", label: "XAG/USD", description: "Silver / US Dollar", group: "Metal" },
  { symbol: "OANDA:EURUSD", label: "EUR/USD", description: "Euro / US Dollar", group: "Forex" },
  { symbol: "OANDA:GBPUSD", label: "GBP/USD", description: "British Pound / US Dollar", group: "Forex" },
  { symbol: "OANDA:USDJPY", label: "USD/JPY", description: "US Dollar / Japanese Yen", group: "Forex" },
  { symbol: "OANDA:AUDUSD", label: "AUD/USD", description: "Australian Dollar / US Dollar", group: "Forex" },
  { symbol: "OANDA:USDCAD", label: "USD/CAD", description: "US Dollar / Canadian Dollar", group: "Forex" },
  { symbol: "OANDA:USDCHF", label: "USD/CHF", description: "US Dollar / Swiss Franc", group: "Forex" },
  { symbol: "OANDA:NZDUSD", label: "NZD/USD", description: "New Zealand Dollar / US Dollar", group: "Forex" },
  { symbol: "BINANCE:BTCUSDT", label: "BTC/USDT", description: "Bitcoin / Tether", group: "Crypto" },
  { symbol: "BINANCE:ETHUSDT", label: "ETH/USDT", description: "Ethereum / Tether", group: "Crypto" },
  { symbol: "BINANCE:SOLUSDT", label: "SOL/USDT", description: "Solana / Tether", group: "Crypto" },
  { symbol: "NASDAQ:NDX", label: "NASDAQ 100", description: "Nasdaq 100 Index", group: "Indeks" },
  { symbol: "SP:SPX", label: "S&P 500", description: "S&P 500 Index", group: "Indeks" },
  { symbol: "DJ:DJI", label: "Dow Jones", description: "Dow Jones Industrial Average", group: "Indeks" },
];

const PAIR_GROUPS: MarketPair["group"][] = ["Metal", "Forex", "Crypto", "Indeks"];

const TIMEFRAMES = [
  { value: "1", label: "1m" },
  { value: "5", label: "5m" },
  { value: "15", label: "15m" },
  { value: "60", label: "1H" },
  { value: "240", label: "4H" },
  { value: "D", label: "1D" },
  { value: "W", label: "1W" },
] as const;

type WidgetStatus = "loading" | "ready" | "error";

function TradingViewEmbed({
  symbol,
  interval,
}: {
  symbol: string;
  interval: string;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [status, setStatus] = useState<WidgetStatus>("loading");
  const [retryKey, setRetryKey] = useState(0);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    let active = true;
    setStatus("loading");

    const widgetHost = document.createElement("div");
    widgetHost.className = "tradingview-widget-container__widget h-full w-full";

    const script = document.createElement("script");
    script.src = "https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js";
    script.type = "text/javascript";
    script.async = true;
    script.textContent = JSON.stringify({
      autosize: true,
      symbol,
      interval,
      timezone: "Asia/Jakarta",
      theme: "dark",
      style: "1",
      locale: "en",
      // The hosted widget supports these colors, but not custom candle/font overrides.
      backgroundColor: "#17202e",
      gridColor: "rgba(205,208,214,.12)",
      allow_symbol_change: true,
      calendar: false,
      details: false,
      hide_legend: false,
      hide_side_toolbar: false,
      hide_top_toolbar: false,
      hide_volume: false,
      hotlist: false,
      save_image: false,
      withdateranges: true,
      studies: [],
      support_host: "https://www.tradingview.com",
    });
    script.onload = () => {
      if (active) setStatus("ready");
    };
    script.onerror = () => {
      if (active) setStatus("error");
    };

    container.replaceChildren(widgetHost, script);
    const timeout = window.setTimeout(() => {
      if (active) setStatus((current) => (current === "loading" ? "error" : current));
    }, 15000);

    return () => {
      active = false;
      window.clearTimeout(timeout);
      container.replaceChildren();
    };
  }, [interval, retryKey, symbol]);

  return (
    <div className="relative h-full min-h-0 bg-background">
      <div ref={containerRef} className="tradingview-widget-container h-full w-full" />

      {status === "loading" && (
        <div className="absolute inset-0 z-10 flex items-center justify-center bg-background" role="status" aria-live="polite">
          <div className="flex flex-col items-center gap-3 text-center">
            <span className="relative flex h-10 w-10 items-center justify-center rounded-xl border border-divider bg-card">
              <CandlestickChart className="h-5 w-5 animate-pulse text-signal" />
            </span>
            <div>
              <p className="text-sm font-medium text-foreground">Memuat data pasar</p>
              <p className="mt-1 text-xs text-muted-foreground">Menghubungkan chart ke TradingView...</p>
            </div>
          </div>
        </div>
      )}

      {status === "error" && (
        <div className="absolute inset-0 z-20 flex items-center justify-center bg-background px-5" role="alert">
          <div className="max-w-md text-center">
            <span className="mx-auto flex h-11 w-11 items-center justify-center rounded-xl border border-divider bg-card">
              <Activity className="h-5 w-5 text-muted-foreground" />
            </span>
            <h2 className="mt-4 text-base font-semibold text-foreground">Chart belum dapat dimuat</h2>
            <p className="mt-1.5 text-sm leading-6 text-muted-foreground">
              Periksa koneksi internet atau pemblokir konten, lalu coba hubungkan kembali.
            </p>
            <Button type="button" variant="outline" className="mt-4 rounded-full border-signal bg-transparent text-muted-foreground shadow-none hover:bg-transparent hover:text-foreground focus-visible:border-signal focus-visible:ring-ring" onClick={() => setRetryKey((value) => value + 1)}>
              <RefreshCw />
              Muat ulang chart
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

export function TradingViewChart() {
  const [symbol, setSymbol] = useState(MARKET_PAIRS[0].symbol);
  const [interval, setIntervalValue] = useState<(typeof TIMEFRAMES)[number]["value"]>("15");
  const selectedPair = useMemo(
    () => MARKET_PAIRS.find((pair) => pair.symbol === symbol) ?? MARKET_PAIRS[0],
    [symbol],
  );
  const tradingViewSlug = symbol.replace(":", "-");

  return (
    <div className="space-y-3 font-sans text-foreground">
      <section aria-label="Kontrol chart" className="relative z-20 rounded-xl border border-black bg-card px-3 py-3 shadow-none sm:px-4">
        <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center">
          <div className="flex min-w-0 flex-col gap-3 sm:flex-row sm:items-center">
            <div className="flex min-w-0 items-center gap-2.5 sm:shrink-0">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-divider bg-transparent text-muted-foreground">
                <CandlestickChart className="h-[18px] w-[18px]" />
              </span>
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <h2 className="text-sm font-medium text-foreground">Instrumen</h2>
                  <Badge variant="outline" className="h-5 border-divider bg-transparent text-[10px] text-muted-foreground">
                    MARKET DATA
                  </Badge>
                </div>
                <p className="truncate text-xs text-muted-foreground">{selectedPair.description}</p>
              </div>
            </div>

            <Select value={symbol} onValueChange={(value) => value && setSymbol(value)}>
              <SelectTrigger aria-label="Pilih pair market" className="h-9 w-full rounded-full border border-signal bg-transparent! text-muted-foreground shadow-none! focus-visible:border-signal focus-visible:ring-ring sm:w-[210px]">
                <Search className="h-3.5 w-3.5 text-muted-foreground" />
                <SelectValue>
                  <span className="font-sans font-medium">{selectedPair.label}</span>
                </SelectValue>
              </SelectTrigger>
              <SelectContent align="start" className="w-[280px] border border-black! bg-card! font-sans text-muted-foreground shadow-none! backdrop-blur-none! [&_[data-slot=select-scroll-up-button]]:bg-card [&_[data-slot=select-scroll-down-button]]:bg-card">
                {PAIR_GROUPS.map((group) => (
                  <SelectGroup key={group}>
                    <SelectLabel>{group}</SelectLabel>
                    {MARKET_PAIRS.filter((pair) => pair.group === group).map((pair) => (
                      <SelectItem key={pair.symbol} value={pair.symbol} className="rounded-full py-2 text-muted-foreground focus:bg-transparent focus:text-muted-foreground focus:ring-1 focus:ring-ring data-highlighted:ring-1 data-highlighted:ring-ring data-selected:bg-foreground data-selected:text-black not-data-[variant=destructive]:focus:**:text-inherit">
                        <span className="w-[78px] text-xs font-medium">{pair.label}</span>
                        <span className="truncate text-xs">{pair.description}</span>
                      </SelectItem>
                    ))}
                  </SelectGroup>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="scrollbar-subtle -mx-1 overflow-x-auto px-1" aria-label="Pilih timeframe">
            <div className="flex min-w-max items-center gap-1 rounded-full border border-divider bg-background p-1">
              {TIMEFRAMES.map((timeframe) => (
                <Button
                  key={timeframe.value}
                  type="button"
                  variant="ghost"
                  size="sm"
                  aria-pressed={interval === timeframe.value}
                  onClick={() => setIntervalValue(timeframe.value)}
                  className={cn(
                    "h-7 min-w-9 rounded-full bg-transparent px-2 font-sans text-xs text-muted-foreground shadow-none hover:bg-transparent hover:text-foreground hover:ring-1 hover:ring-signal focus-visible:border-signal focus-visible:ring-ring",
                    interval === timeframe.value && "bg-foreground text-black hover:bg-foreground hover:text-black",
                  )}
                >
                  {timeframe.label}
                </Button>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section aria-label="Chart pasar real-time" className="overflow-hidden rounded-xl border border-black bg-background shadow-none">
        <div className="h-[600px] min-h-[500px] sm:h-[660px] lg:h-[calc(100dvh-18.5rem)] lg:min-h-[500px]">
          <TradingViewEmbed symbol={symbol} interval={interval} />
        </div>

        <div className="flex flex-col gap-1 border-t border-divider bg-card px-3 py-2 text-[11px] text-muted-foreground sm:flex-row sm:items-center sm:justify-between sm:px-4">
          <span>Data real-time atau tertunda mengikuti bursa dan kebijakan penyedia.</span>
          <a
            href={`https://www.tradingview.com/symbols/${tradingViewSlug}/`}
            target="_blank"
            rel="noopener nofollow noreferrer"
            className="font-medium text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            {selectedPair.label} chart by TradingView
          </a>
        </div>
      </section>
    </div>
  );
}
