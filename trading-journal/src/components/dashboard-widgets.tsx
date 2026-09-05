"use client";

import { useEffect, useState } from "react";
import type { Trade } from "@/lib/types";
import { fmtMoney } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardAction } from "@/components/ui/card";
import { TrendingUp, TrendingDown, Target, BarChart3, ArrowRight } from "lucide-react";

export function WidgetCard({
  title, href, hrefLabel, children, className, bodyClassName,
}: {
  title: string;
  href?: string;
  hrefLabel?: string;
  children: React.ReactNode;
  className?: string;
  bodyClassName?: string;
}) {
  return (
    <Card className={cn("min-h-0 gap-2 py-4", className)}>
      <CardHeader className="border-b border-slate-800/70 px-5 pb-3 [.border-b]:pb-3">
        <CardTitle className="text-sm font-semibold text-slate-100">
          {title}
        </CardTitle>
        {href && (
          <CardAction>
            <a href={href} className="flex items-center gap-1.5 text-xs font-medium text-slate-500 transition-colors hover:text-blue-300">
              {hrefLabel ?? "Lihat"} <ArrowRight className="h-3 w-3" />
            </a>
          </CardAction>
        )}
      </CardHeader>
      <CardContent className={cn("flex-1 px-5", bodyClassName)}>{children}</CardContent>
    </Card>
  );
}

function WidgetMetric({ label, value, color, icon }: { label: string; value: string; color?: string; icon?: React.ReactNode }) {
  return (
    <div className="glass-inset flex items-center gap-2.5 rounded-lg px-3 py-2.5">
      {icon && <span className="text-blue-300/75">{icon}</span>}
      <div className="min-w-0">
        <p className="text-xs font-medium tracking-normal text-slate-500">{label}</p>
        <p className={cn("truncate font-mono text-base font-semibold leading-tight", color ?? "text-slate-100")}>{value}</p>
      </div>
    </div>
  );
}

export function AnalitikWidget({ className }: { className?: string }) {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    fetch("/api/trades?limit=1000", { cache: "no-store" })
      .then((r) => r.json())
      .then((d) => { if (active) { setTrades(d); setLoading(false); } })
      .catch(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  const closed = trades.filter((t) => t.status === "closed" && t.profit != null);
  const wins = closed.filter((t) => t.profit! >= 0);
  const losses = closed.filter((t) => t.profit! < 0);
  const net = closed.reduce((s, t) => s + t.profit!, 0);
  const winRate = closed.length ? (wins.length / closed.length) * 100 : 0;
  const grossWin = wins.reduce((s, t) => s + t.profit!, 0);
  const grossLoss = Math.abs(losses.reduce((s, t) => s + t.profit!, 0));
  const pf = grossLoss > 0 ? grossWin / grossLoss : grossWin > 0 ? Infinity : 0;

  const bySymbol = new Map<string, { total: number; pnl: number }>();
  for (const t of closed) {
    const cur = bySymbol.get(t.symbol) ?? { total: 0, pnl: 0 };
    cur.total++;
    cur.pnl += t.profit!;
    bySymbol.set(t.symbol, cur);
  }
  const top = [...bySymbol.entries()].sort((a, b) => b[1].pnl - a[1].pnl)[0];

  if (loading) {
    return (
      <WidgetCard title="Analitik" href="/analitik" className={className}>
        <div className="flex h-full items-center justify-center text-sm text-slate-500">Memuat analitik...</div>
      </WidgetCard>
    );
  }

  return (
    <WidgetCard title="Analitik" href="/analitik" className={className}>
      {closed.length === 0 ? (
        <div className="flex h-full items-center justify-center text-sm text-slate-500">Belum ada trade closed</div>
      ) : (
        <div className="flex flex-col gap-2.5">
          <div className="grid grid-cols-2 gap-2.5">
            <WidgetMetric icon={<BarChart3 className="h-4 w-4" />} label="Net Profit" value={fmtMoney(net)} color={net >= 0 ? "text-emerald-400" : "text-red-400"} />
            <WidgetMetric icon={<Target className="h-4 w-4" />} label="Win Rate" value={`${winRate.toFixed(1)}%`} />
            <WidgetMetric icon={<TrendingUp className="h-4 w-4" />} label="Profit Factor" value={pf === Infinity ? "∞" : pf.toFixed(2)} />
            <WidgetMetric icon={<TrendingDown className="h-4 w-4" />} label="Total Closed" value={String(closed.length)} />
          </div>
          {top && (
            <div className="glass-inset flex items-center justify-between gap-3 rounded-lg px-3 py-2.5 text-xs">
              <span className="text-slate-500">Top symbol</span>
              <span className="font-mono font-semibold text-slate-200">{top[0]}</span>
              <span className="flex items-center gap-2">
                <Badge variant="outline" className="font-mono text-[10px]">{top[1].total} trade</Badge>
                <span className={cn("font-mono font-semibold", top[1].pnl >= 0 ? "text-emerald-400" : "text-red-400")}>
                  {fmtMoney(top[1].pnl)}
                </span>
              </span>
            </div>
          )}
        </div>
      )}
    </WidgetCard>
  );
}
