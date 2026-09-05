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
      <div className={cn("flex flex-col items-center justify-center py-16 text-muted-foreground", className)}>
        <Minus className="mb-2 h-8 w-8 text-muted-foreground" />
        <p className="text-sm">Belum ada trade</p>
      </div>
    );
  }

  const statusColor: Record<string, string> = {
    open: "border-border bg-background text-positive",
    closed: "border-border bg-background text-muted-foreground",
    pending: "border-border bg-background text-warning",
    rejected: "border-border bg-background text-negative",
  };

  return (
    <div className={cn("overflow-x-auto", className)}>
      <table className="w-full min-w-[760px] text-[13px]">
        <thead className="bg-background">
          <tr className="border-b border-divider text-xs tracking-normal text-muted-foreground">
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
              <tr key={t.id} className="border-b border-divider transition-colors hover:bg-background">
                <td className="py-3 pr-2 font-mono font-semibold text-foreground">{t.symbol}</td>
                <td className="py-2 px-2">
                  <span className={cn(
                    "flex items-center gap-1 font-medium",
                    isLong ? "text-buy" : "text-sell",
                  )}>
                    {isLong ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
                    {t.side}
                  </span>
                </td>
                <td className="px-2 py-3 text-right font-mono text-foreground">{fmtNum(t.lots)}</td>
                <td className="px-2 py-3 text-right font-mono text-foreground">{fmtNum(t.entry)}</td>
                <td className="px-2 py-3 text-right font-mono text-muted-foreground">{fmtNum(t.sl)}</td>
                <td className="px-2 py-3 text-right font-mono text-muted-foreground">{fmtNum(t.tp)}</td>
                <td className={cn(
                  "px-2 py-3 text-right font-mono font-semibold",
                  profit != null && profit > 0 ? "text-positive" :
                    profit != null && profit < 0 ? "text-negative" : "text-muted-foreground",
                )}>
                  {profit != null ? `${profit >= 0 ? "+" : ""}${fmtMoney(profit)}` : "-"}
                </td>
                <td className="px-2 py-3">
                  <Badge variant="outline" className={cn("rounded-full capitalize", statusColor[t.status] ?? "text-muted-foreground")}>{t.status}</Badge>
                </td>
                <td className="px-2 py-3">
                  <Badge variant="outline" className={cn(
                    "rounded-full text-[10px] font-medium",
                    t.source === "mt5"
                      ? "border-border bg-background text-signal"
                      : t.source === "bot+mt5"
                        ? "border-border bg-background text-positive"
                        : "border-border bg-background text-muted-foreground",
                  )}>
                    {t.source === "mt5" ? "MT5" : t.source === "bot+mt5" ? "BOT+MT5" : "BOT"}
                  </Badge>
                </td>
                <td className="py-3 pl-2 font-mono text-muted-foreground">{t.openTs ? fmtTime(t.openTs) : "-"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
