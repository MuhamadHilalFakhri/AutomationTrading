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
        className="glass-inset inline-flex h-9 min-w-[148px] items-center justify-start gap-2 rounded-lg border-white/10 px-3 text-left text-[13px] text-slate-200 transition-colors hover:bg-white/[0.07] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400/70"
      >
        <CalendarDays className="h-4 w-4 shrink-0 text-blue-300" />
        <span className={cn(!value && "text-slate-500")}>{dateLabel(value, label)}</span>
      </PopoverTrigger>
      <PopoverContent align="start" className="solid-popover p-0">
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
    open: "border-emerald-400/20 bg-emerald-500/10 text-emerald-300",
    closed: "border-slate-700 bg-slate-800 text-slate-300",
    pending: "border-amber-400/20 bg-amber-500/10 text-amber-300",
    rejected: "border-red-400/20 bg-red-500/10 text-red-300",
  };

  return (
    <div>
      <PageHeader title="Trades" subtitle="Riwayat semua posisi yang dibuka bot" />

      {/* filters */}
      <div className="glass-panel mb-5 rounded-xl p-3 sm:p-4">
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
                    "min-h-9 rounded-lg px-3 text-[13px] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400/70",
                    status === s
                      ? "bg-blue-500/15 font-medium text-blue-200 ring-1 ring-inset ring-blue-400/25"
                      : "text-slate-400 hover:bg-slate-800 hover:text-slate-100",
                  )}
                >
                  {s === "all" ? "Semua" : s}
                </button>
              ))}
            </div>
            <label className="flex items-center gap-2 text-sm text-slate-400">
              <span className="sr-only">Filter symbol</span>
              <select
                value={symbol}
                onChange={(e) => setSymbol(e.target.value)}
                className="glass-inset h-9 min-w-36 rounded-lg border-white/10 px-3 text-[13px] text-slate-200 outline-none transition-colors focus:border-blue-400 focus:ring-2 focus:ring-blue-400/20"
              >
                <option value="all">Semua symbol</option>
                {symbols.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </label>
          </div>

          <div className="flex flex-col gap-3 border-t border-white/[0.07] pt-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-medium text-slate-200">Rentang tanggal</p>
              <p className="text-xs text-slate-500">Berdasarkan waktu pembukaan posisi · WIB</p>
            </div>
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
              <DateFilter label="Tanggal mulai" value={dateFrom} onSelect={(date) => { setDateFrom(date); if (date && dateTo && date > dateTo) setDateTo(undefined); }} />
              <span className="hidden text-xs text-slate-500 sm:inline">sampai</span>
              <DateFilter label="Tanggal akhir" value={dateTo} onSelect={setDateTo} disabled={dateFrom ? { before: dateFrom } : undefined} />
              {(dateFrom || dateTo) && (
                <Button type="button" variant="ghost" size="sm" onClick={() => { setDateFrom(undefined); setDateTo(undefined); }} className="h-9 justify-start px-2.5 text-slate-400 hover:text-slate-100 sm:justify-center" aria-label="Hapus filter tanggal">
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
        <div className="glass-panel rounded-xl p-4">
          <p className="text-xs text-slate-500">Total PnL (filter)</p>
          <p className={cn("mt-1 font-mono text-xl font-semibold", totalPnl >= 0 ? "text-emerald-300" : "text-red-300")}>
            {fmtMoney(totalPnl)}
          </p>
        </div>
        <div className="glass-panel rounded-xl p-4">
          <p className="text-xs text-slate-500">Win rate (filter)</p>
          <p className="mt-1 font-mono text-xl font-semibold text-slate-100">{winRate}%</p>
        </div>
        <div className="glass-panel rounded-xl p-4">
          <p className="text-xs text-slate-500">Jumlah trade</p>
          <p className="mt-1 font-mono text-xl font-semibold text-slate-100">{filtered.length}</p>
        </div>
      </div>

      {/* table */}
      <div className="solid-data overflow-hidden rounded-xl border">
        {loading ? (
          <div className="space-y-3 p-5">
            <Skeleton className="h-9 w-full bg-slate-800" />
            <Skeleton className="h-9 w-full bg-slate-800" />
            <Skeleton className="h-9 w-full bg-slate-800" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-12 text-slate-500">
            <Minus className="mb-2 h-8 w-8 text-slate-600" />
            <p className="text-sm">Tidak ada trade sesuai filter</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[860px] text-[13px]">
              <thead className="bg-slate-950/50">
                <tr className="border-b border-slate-800 text-xs tracking-normal text-slate-500">
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
                    <tr key={t.id} className="border-b border-slate-800/70 transition-colors hover:bg-blue-500/[0.04]">
                      <td className="py-3 pl-4 pr-2 font-mono font-semibold text-slate-200">{t.symbol}</td>
                      <td className="px-2 py-2">
                        <span className={cn("flex items-center gap-1 font-medium", isLong ? "text-emerald-400" : "text-red-400")}>
                          {isLong ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
                          {t.side}
                        </span>
                      </td>
                      <td className="px-2 py-3 text-right font-mono text-slate-300">{fmtNum(t.lots)}</td>
                      <td className="px-2 py-3 text-right font-mono text-slate-300">{fmtNum(t.entry)}</td>
                      <td className="px-2 py-3 text-right font-mono text-slate-500">{fmtNum(t.closePrice)}</td>
                      <td className={cn(
                        "px-2 py-3 text-right font-mono font-semibold",
                        profit != null && profit > 0 ? "text-emerald-400" : profit != null && profit < 0 ? "text-red-400" : "text-zinc-500",
                      )}>
                        {profit != null ? `${profit >= 0 ? "+" : ""}${fmtMoney(profit)}` : "-"}
                      </td>
                      <td className="px-2 py-3">
                        <Badge variant="outline" className={cn("capitalize", statusColor[t.status] ?? "text-slate-400")}>{t.status}</Badge>
                      </td>
                      <td className="px-2 py-3 text-slate-400">{t.strategy ?? "-"}</td>
                      <td className="py-3 pl-2 pr-4 text-slate-500">{t.openTs ? fmtDateTime(t.openTs) : "-"}</td>
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
