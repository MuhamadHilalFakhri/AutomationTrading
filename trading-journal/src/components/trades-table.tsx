"use client";

import { useEffect, useState, useCallback } from "react";
import { cn } from "@/lib/utils";
import type { Trade } from "@/lib/types";
import { fmtMoney, fmtNum, fmtTime } from "@/lib/types";
import { ArrowUpRight, ArrowDownRight, Minus } from "lucide-react";
import { Badge } from "@/components/ui/badge";

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
      <div className={cn("flex flex-col items-center justify-center py-16 text-slate-500", className)}>
        <Minus className="mb-2 h-8 w-8 text-slate-600" />
        <p className="text-sm">Belum ada trade</p>
      </div>
    );
  }

  const statusColor: Record<string, string> = {
    open: "border-emerald-400/20 bg-emerald-500/10 text-emerald-300",
    closed: "border-slate-700 bg-slate-800 text-slate-300",
    pending: "border-amber-400/20 bg-amber-500/10 text-amber-300",
    rejected: "border-red-400/20 bg-red-500/10 text-red-300",
  };

  return (
    <div className={cn("overflow-x-auto", className)}>
      <table className="w-full min-w-[760px] text-[13px]">
        <thead className="bg-slate-900/70">
          <tr className="border-b border-slate-800 text-xs tracking-normal text-slate-500">
            <th className="py-3 pr-2 text-left font-medium">Symbol</th>
            <th className="px-2 py-3 text-left font-medium">Side</th>
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
              <tr key={t.id} className="border-b border-slate-800/70 transition-colors hover:bg-blue-500/[0.04]">
                <td className="py-3 pr-2 font-mono font-semibold text-slate-200">{t.symbol}</td>
                <td className="py-2 px-2">
                  <span className={cn(
                    "flex items-center gap-1 font-medium",
                    isLong ? "text-emerald-400" : "text-red-400",
                  )}>
                    {isLong ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
                    {t.side}
                  </span>
                </td>
                <td className="px-2 py-3 text-right font-mono text-slate-300">{fmtNum(t.lots)}</td>
                <td className="px-2 py-3 text-right font-mono text-slate-300">{fmtNum(t.entry)}</td>
                <td className="px-2 py-3 text-right font-mono text-slate-500">{fmtNum(t.sl)}</td>
                <td className="px-2 py-3 text-right font-mono text-slate-500">{fmtNum(t.tp)}</td>
                <td className={cn(
                  "px-2 py-3 text-right font-mono font-semibold",
                  profit != null && profit > 0 ? "text-emerald-400" :
                    profit != null && profit < 0 ? "text-red-400" : "text-zinc-500",
                )}>
                  {profit != null ? `${profit >= 0 ? "+" : ""}${fmtMoney(profit)}` : "-"}
                </td>
                <td className="px-2 py-3">
                  <Badge variant="outline" className={cn("capitalize", statusColor[t.status] ?? "text-slate-400")}>{t.status}</Badge>
                </td>
                <td className="px-2 py-3">
                  <Badge variant="outline" className={cn(
                    "text-[10px] font-medium",
                    t.source === "mt5"
                      ? "border-sky-400/20 bg-sky-500/10 text-sky-300"
                      : t.source === "bot+mt5"
                        ? "border-emerald-400/20 bg-emerald-500/10 text-emerald-300"
                        : "border-slate-700 bg-slate-900 text-slate-400",
                  )}>
                    {t.source === "mt5" ? "MT5" : t.source === "bot+mt5" ? "BOT+MT5" : "BOT"}
                  </Badge>
                </td>
                <td className="py-3 pl-2 text-slate-500">{t.openTs ? fmtTime(t.openTs) : "-"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
