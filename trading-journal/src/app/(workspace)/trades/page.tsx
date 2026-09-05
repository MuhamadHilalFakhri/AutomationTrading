"use client";

import { useEffect, useState } from "react";
import { PageHeader } from "@/components/page-header";
import type { Trade } from "@/lib/types";
import { fmtMoney, fmtNum, fmtDateTime } from "@/lib/types";
import { cn } from "@/lib/utils";
import { ArrowUpRight, ArrowDownRight, CalendarDays, Minus, X } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";

type StatusFilter = "all" | "open" | "closed" | "pending" | "rejected";

function localDateKey(date: Date) {
  return [date.getFullYear(), String(date.getMonth() + 1).padStart(2, "0"), String(date.getDate()).padStart(2, "0")].join("-");
}

function wibDateKey(iso: string) {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "Asia/Jakarta",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date(iso));
  const value = (type: Intl.DateTimeFormatPartTypes) => parts.find((part) => part.type === type)?.value ?? "";
  return `${value("year")}-${value("month")}-${value("day")}`;
}

function dateLabel(date: Date | undefined, placeholder: string) {
  return date
    ? date.toLocaleDateString("id-ID", { day: "2-digit", month: "short", year: "numeric" })
    : placeholder;
}

function DateFilter({
  label,
  value,
  onSelect,
  disabled,
}: {
  label: string;
  value: Date | undefined;
  onSelect: (date: Date | undefined) => void;
  disabled?: { before: Date };
}) {
  return (
    <Popover>
      <PopoverTrigger
        type="button"
        aria-label={label}
        className={cn("inline-flex h-9 min-w-[148px] items-center justify-start gap-2 rounded-full border border-border px-3 text-left text-[13px] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring", value ? "bg-foreground text-black" : "bg-background text-muted-foreground hover:text-foreground")}
      >
        <CalendarDays className={cn("h-4 w-4 shrink-0", !value && "text-signal")} />
        <span>{dateLabel(value, label)}</span>
      </PopoverTrigger>
      <PopoverContent align="start" className="solid-popover rounded-[15px] border-border bg-card p-0 shadow-none">
        <Calendar mode="single" selected={value} onSelect={onSelect} disabled={disabled} />
      </PopoverContent>
    </Popover>
  );
}

export default function TradesPage() {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [status, setStatus] = useState<StatusFilter>("all");
  const [symbol, setSymbol] = useState("all");
  const [dateFrom, setDateFrom] = useState<Date>();
  const [dateTo, setDateTo] = useState<Date>();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    fetch("/api/trades?limit=500", { cache: "no-store" })
      .then((r) => r.json())
      .then((d) => { if (active) { setTrades(d); setLoading(false); } })
      .catch(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  const symbols = Array.from(new Set(trades.map((t) => t.symbol))).sort();

  const filtered = trades.filter(
    (t) => {
      if (status !== "all" && t.status !== status) return false;
      if (symbol !== "all" && t.symbol !== symbol) return false;
      const tradeDate = t.openTs ? wibDateKey(t.openTs) : null;
      if (dateFrom && (!tradeDate || tradeDate < localDateKey(dateFrom))) return false;
      if (dateTo && (!tradeDate || tradeDate > localDateKey(dateTo))) return false;
      return true;
    },
  );

  const closed = filtered.filter((t) => t.status === "closed");
  const wins = closed.filter((t) => (t.profit ?? 0) >= 0).length;
  const totalPnl = closed.reduce((s, t) => s + (t.profit ?? 0), 0);
  const winRate = closed.length ? Math.round((wins / closed.length) * 1000) / 10 : 0;

  const statusColor: Record<string, string> = {
    open: "border-border bg-background text-positive",
    closed: "border-border bg-background text-muted-foreground",
    pending: "border-border bg-background text-warning",
    rejected: "border-border bg-background text-negative",
  };

  return (
    <div>
      <PageHeader title="Trades" subtitle="Riwayat semua posisi yang dibuka bot" />

      {/* filters */}
      <div className="glass-panel mb-5 rounded-[15px] p-3 sm:p-4">
        <div className="flex flex-col gap-3">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex flex-wrap gap-1.5" role="group" aria-label="Filter status trade">
              {(["all", "open", "closed", "pending", "rejected"] as StatusFilter[]).map((s) => (
                <button
                  key={s}
                  onClick={() => setStatus(s)}
                  type="button"
                  aria-pressed={status === s}
                  className={cn(
                    "min-h-9 rounded-full border border-border px-3 text-[13px] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                    status === s
                      ? "bg-foreground font-medium text-black"
                      : "text-muted-foreground hover:bg-background hover:text-foreground",
                  )}
                >
                  {s === "all" ? "Semua" : s}
                </button>
              ))}
            </div>
            <label className="flex items-center gap-2 text-sm text-muted-foreground">
              <span className="sr-only">Filter symbol</span>
              <select
                value={symbol}
                onChange={(e) => setSymbol(e.target.value)}
                className={cn("h-9 min-w-36 rounded-full border border-border px-3 text-[13px] outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring", symbol !== "all" ? "bg-foreground text-black" : "bg-background text-foreground")}
              >
                <option value="all">Semua symbol</option>
                {symbols.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </label>
          </div>

          <div className="flex flex-col gap-3 border-t border-divider pt-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-medium text-foreground">Rentang tanggal</p>
              <p className="text-xs text-muted-foreground">Berdasarkan waktu pembukaan posisi · WIB</p>
            </div>
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
              <DateFilter label="Tanggal mulai" value={dateFrom} onSelect={(date) => { setDateFrom(date); if (date && dateTo && date > dateTo) setDateTo(undefined); }} />
              <span className="hidden text-xs text-muted-foreground sm:inline">sampai</span>
              <DateFilter label="Tanggal akhir" value={dateTo} onSelect={setDateTo} disabled={dateFrom ? { before: dateFrom } : undefined} />
              {(dateFrom || dateTo) && (
                <Button type="button" variant="ghost" size="sm" onClick={() => { setDateFrom(undefined); setDateTo(undefined); }} className="h-9 justify-start rounded-full px-2.5 text-muted-foreground shadow-none hover:bg-background hover:text-foreground focus-visible:ring-ring sm:justify-center" aria-label="Hapus filter tanggal">
                  <X className="h-3.5 w-3.5" />
                  <span className="sm:hidden">Hapus tanggal</span>
                </Button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* filtered summary */}
      <div className="mb-5 grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div className="glass-panel rounded-[15px] p-4">
          <p className="text-xs text-muted-foreground">Total PnL (filter)</p>
          <p className={cn("mt-1 font-sans text-xl font-semibold tracking-tight tabular-nums", totalPnl >= 0 ? "text-positive" : "text-negative")}>
            {fmtMoney(totalPnl)}
          </p>
        </div>
        <div className="glass-panel rounded-[15px] p-4">
          <p className="text-xs text-muted-foreground">Win rate (filter)</p>
          <p className={cn("mt-1 font-sans text-xl font-semibold tracking-tight tabular-nums", closed.length > 0 ? (winRate >= 50 ? "text-positive" : "text-negative") : "text-foreground")}>{winRate}%</p>
        </div>
        <div className="glass-panel rounded-[15px] p-4">
          <p className="text-xs text-muted-foreground">Jumlah trade</p>
          <p className="mt-1 font-sans text-xl font-semibold tracking-tight tabular-nums text-foreground">{filtered.length}</p>
        </div>
      </div>

      {/* table */}
      <div className="solid-data overflow-hidden rounded-[15px] border border-border">
        {loading ? (
          <div className="space-y-3 p-5">
            <Skeleton className="h-9 w-full bg-card" />
            <Skeleton className="h-9 w-full bg-card" />
            <Skeleton className="h-9 w-full bg-card" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-12 text-muted-foreground">
            <Minus className="mb-2 h-8 w-8 text-muted-foreground" />
            <p className="text-sm">Tidak ada trade sesuai filter</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[860px] text-[13px]">
              <thead className="bg-background">
                <tr className="border-b border-divider text-xs tracking-normal text-muted-foreground">
                  <th className="py-2 pl-4 pr-2 text-left font-medium">Symbol</th>
                  <th className="px-2 py-2 text-left font-medium">Side</th>
                  <th className="px-2 py-2 text-right font-medium">Lots</th>
                  <th className="px-2 py-2 text-right font-medium">Entry</th>
                  <th className="px-2 py-2 text-right font-medium">Close</th>
                  <th className="px-2 py-2 text-right font-medium">PnL</th>
                  <th className="px-2 py-2 text-left font-medium">Status</th>
                  <th className="px-2 py-2 text-left font-medium">Strategi</th>
                  <th className="py-2 pl-2 pr-4 text-left font-medium">Waktu</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((t) => {
                  const profit = t.profit;
                  const sideLower = t.side?.toLowerCase() ?? "";
                  const isLong = sideLower.startsWith("buy");
                  return (
                    <tr key={t.id} className="border-b border-divider transition-colors hover:bg-background">
                      <td className="py-3 pl-4 pr-2 font-mono font-semibold text-foreground">{t.symbol}</td>
                      <td className="px-2 py-2">
                        <span className={cn("flex items-center gap-1 font-medium", isLong ? "text-buy" : "text-sell")}>
                          {isLong ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
                          {t.side}
                        </span>
                      </td>
                      <td className="px-2 py-3 text-right font-mono text-foreground">{fmtNum(t.lots)}</td>
                      <td className="px-2 py-3 text-right font-mono text-foreground">{fmtNum(t.entry)}</td>
                      <td className="px-2 py-3 text-right font-mono text-muted-foreground">{fmtNum(t.closePrice)}</td>
                      <td className={cn(
                        "px-2 py-3 text-right font-mono font-semibold",
                        profit != null && profit > 0 ? "text-positive" : profit != null && profit < 0 ? "text-negative" : "text-muted-foreground",
                      )}>
                        {profit != null ? `${profit >= 0 ? "+" : ""}${fmtMoney(profit)}` : "-"}
                      </td>
                      <td className="px-2 py-3">
                        <Badge variant="outline" className={cn("rounded-full capitalize", statusColor[t.status] ?? "text-muted-foreground")}>{t.status}</Badge>
                      </td>
                      <td className="px-2 py-3 text-muted-foreground">{t.strategy ?? "-"}</td>
                      <td className="py-3 pl-2 pr-4 font-mono text-muted-foreground">{t.openTs ? fmtDateTime(t.openTs) : "-"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
