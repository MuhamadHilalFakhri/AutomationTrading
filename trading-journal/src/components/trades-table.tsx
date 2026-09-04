"use client";

import { useEffect, useState, useCallback } from "react";
import { cn } from "@/lib/utils";
import type { Trade } from "@/lib/types";
import { fmtMoney, fmtNum, fmtTime } from "@/lib/types";
import { ArrowUpRight, ArrowDownRight, Minus } from "lucide-react";

export function TradesTable({ className }: { className?: string }) {
  const [trades, setTrades] = useState<Trade[]>([]);

  const load = useCallback(async () => {
    try {
      const r = await fetch("/api/trades?limit=100", { cache: "no-store" });
      if (r.ok) setTrades(await r.json());
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    let active = true;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- async fetch, setState happens after await
    load();
    const t = setInterval(() => { if (active) load(); }, 30000);
    return () => { active = false; clearInterval(t); };
  }, [load]);

  if (trades.length === 0) {
    return (
      <div className={cn("flex flex-col items-center justify-center py-16 text-zinc-500", className)}>
        <Minus className="h-8 w-8 mb-2 text-zinc-600" />
        <p className="text-sm">Belum ada trade</p>
      </div>
    );
  }

  const statusColor: Record<string, string> = {
    open: "text-emerald-400",
    closed: "text-zinc-400",
    pending: "text-amber-400",
    rejected: "text-red-400",
  };

  return (
    <div className={cn("overflow-x-auto", className)}>
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-zinc-800 text-zinc-500 uppercase tracking-wider">
            <th className="text-left py-2 pr-2 font-medium">Symbol</th>
            <th className="text-left py-2 px-2 font-medium">Side</th>
            <th className="text-right py-2 px-2 font-medium">Lots</th>
            <th className="text-right py-2 px-2 font-medium">Entry</th>
            <th className="text-right py-2 px-2 font-medium">SL</th>
            <th className="text-right py-2 px-2 font-medium">TP</th>
            <th className="text-right py-2 px-2 font-medium">PnL</th>
            <th className="text-left py-2 px-2 font-medium">Status</th>
            <th className="text-left py-2 px-2 font-medium">Src</th>
            <th className="text-left py-2 pl-2 font-medium">Time</th>
          </tr>
        </thead>
        <tbody>
          {trades.map((t) => {
            const profit = t.profit;
            const sideLower = t.side?.toLowerCase() ?? "";
            const isLong = sideLower.startsWith("buy");
            return (
              <tr key={t.id} className="border-b border-zinc-900/50 hover:bg-zinc-900/30">
                <td className="py-2 pr-2 font-semibold">{t.symbol}</td>
                <td className="py-2 px-2">
                  <span className={cn(
                    "flex items-center gap-1 font-medium",
                    isLong ? "text-emerald-400" : "text-red-400",
                  )}>
                    {isLong ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
                    {t.side}
                  </span>
                </td>
                <td className="py-2 px-2 text-right font-mono">{fmtNum(t.lots)}</td>
                <td className="py-2 px-2 text-right font-mono">{fmtNum(t.entry)}</td>
                <td className="py-2 px-2 text-right font-mono text-zinc-500">{fmtNum(t.sl)}</td>
                <td className="py-2 px-2 text-right font-mono text-zinc-500">{fmtNum(t.tp)}</td>
                <td className={cn(
                  "py-2 px-2 text-right font-mono font-semibold",
                  profit != null && profit > 0 ? "text-emerald-400" :
                    profit != null && profit < 0 ? "text-red-400" : "text-zinc-500",
                )}>
                  {profit != null ? `${profit >= 0 ? "+" : ""}${fmtMoney(profit)}` : "-"}
                </td>
                <td className="py-2 px-2">
                  <span className={cn(statusColor[t.status] ?? "text-zinc-500")}>{t.status}</span>
                </td>
                <td className="py-2 px-2">
                  <span className={cn(
                    "rounded border px-1 py-0.5 text-[10px] font-medium",
                    t.source === "mt5"
                      ? "border-sky-900/60 bg-sky-950/40 text-sky-400"
                      : t.source === "bot+mt5"
                        ? "border-emerald-900/60 bg-emerald-950/40 text-emerald-400"
                        : "border-zinc-800 bg-zinc-900 text-zinc-400",
                  )}>
                    {t.source === "mt5" ? "MT5" : t.source === "bot+mt5" ? "BOT+MT5" : "BOT"}
                  </span>
                </td>
                <td className="py-2 pl-2 text-zinc-500">{t.openTs ? fmtTime(t.openTs) : "-"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}