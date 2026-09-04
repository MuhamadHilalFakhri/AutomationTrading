"use client";

import { useEffect, useState } from "react";
import { PageHeader } from "@/components/page-header";
import type { Trade } from "@/lib/types";
import { fmtMoney, fmtNum, fmtDateTime } from "@/lib/types";
import { cn } from "@/lib/utils";
import { ArrowUpRight, ArrowDownRight, Minus } from "lucide-react";

type StatusFilter = "all" | "open" | "closed" | "pending" | "rejected";

export default function TradesPage() {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [status, setStatus] = useState<StatusFilter>("all");
  const [symbol, setSymbol] = useState("all");
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
    (t) =>
      (status === "all" || t.status === status) &&
      (symbol === "all" || t.symbol === symbol),
  );

  const closed = filtered.filter((t) => t.status === "closed");
  const wins = closed.filter((t) => (t.profit ?? 0) >= 0).length;
  const totalPnl = closed.reduce((s, t) => s + (t.profit ?? 0), 0);
  const winRate = closed.length ? Math.round((wins / closed.length) * 1000) / 10 : 0;

  const statusColor: Record<string, string> = {
    open: "text-emerald-400",
    closed: "text-zinc-400",
    pending: "text-amber-400",
    rejected: "text-red-400",
  };

  return (
    <div>
      <PageHeader title="Trades" subtitle="Riwayat semua posisi yang dibuka bot" />

      {/* filters */}
      <div className="mb-4 flex flex-wrap items-center gap-2">
        {(["all", "open", "closed", "pending", "rejected"] as StatusFilter[]).map((s) => (
          <button
            key={s}
            onClick={() => setStatus(s)}
            className={cn(
              "rounded-full px-3 py-1 text-xs",
              status === s
                ? "bg-zinc-800 font-medium text-zinc-100"
                : "border border-zinc-800 text-zinc-500 hover:bg-zinc-900",
            )}
          >
            {s === "all" ? "Semua" : s}
          </button>
        ))}
        <select
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          className="ml-auto rounded-md border border-zinc-800 bg-zinc-950 px-2 py-1.5 text-xs text-zinc-300 outline-none focus:border-zinc-600"
        >
          <option value="all">Semua symbol</option>
          {symbols.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>

      {/* filtered summary */}
      <div className="mb-4 grid grid-cols-3 gap-3">
        <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-3">
          <p className="text-xs text-zinc-500">Total PnL (filter)</p>
          <p className={cn("font-mono text-lg font-bold", totalPnl >= 0 ? "text-emerald-400" : "text-red-400")}>
            {fmtMoney(totalPnl)}
          </p>
        </div>
        <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-3">
          <p className="text-xs text-zinc-500">Win Rate (filter)</p>
          <p className="font-mono text-lg font-bold">{winRate}%</p>
        </div>
        <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-3">
          <p className="text-xs text-zinc-500">Jumlah Trade</p>
          <p className="font-mono text-lg font-bold">{filtered.length}</p>
        </div>
      </div>

      {/* table */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-950">
        {loading ? (
          <div className="p-10 text-center text-sm text-zinc-600">Memuat...</div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-10 text-zinc-500">
            <Minus className="mb-2 h-8 w-8 text-zinc-700" />
            <p className="text-sm">Tidak ada trade sesuai filter</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-zinc-800 text-zinc-500 uppercase tracking-wider">
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
                    <tr key={t.id} className="border-b border-zinc-900/50 hover:bg-zinc-900/30">
                      <td className="py-2 pl-4 pr-2 font-semibold">{t.symbol}</td>
                      <td className="px-2 py-2">
                        <span className={cn("flex items-center gap-1 font-medium", isLong ? "text-emerald-400" : "text-red-400")}>
                          {isLong ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
                          {t.side}
                        </span>
                      </td>
                      <td className="px-2 py-2 text-right font-mono">{fmtNum(t.lots)}</td>
                      <td className="px-2 py-2 text-right font-mono">{fmtNum(t.entry)}</td>
                      <td className="px-2 py-2 text-right font-mono text-zinc-500">{fmtNum(t.closePrice)}</td>
                      <td className={cn(
                        "px-2 py-2 text-right font-mono font-semibold",
                        profit != null && profit > 0 ? "text-emerald-400" : profit != null && profit < 0 ? "text-red-400" : "text-zinc-500",
                      )}>
                        {profit != null ? `${profit >= 0 ? "+" : ""}${fmtMoney(profit)}` : "-"}
                      </td>
                      <td className="px-2 py-2">
                        <span className={cn(statusColor[t.status] ?? "text-zinc-500")}>{t.status}</span>
                      </td>
                      <td className="px-2 py-2 text-zinc-400">{t.strategy ?? "-"}</td>
                      <td className="py-2 pl-2 pr-4 text-zinc-500">{t.openTs ? fmtDateTime(t.openTs) : "-"}</td>
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
