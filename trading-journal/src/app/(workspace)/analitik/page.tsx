"use client";

import { useEffect, useState } from "react";
import { PageHeader } from "@/components/page-header";
import type { Trade } from "@/lib/types";
import { fmtMoney } from "@/lib/types";
import { cn } from "@/lib/utils";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip,
  CartesianGrid, Cell, PieChart, Pie, Legend,
} from "recharts";
import { Skeleton } from "@/components/ui/skeleton";

interface StrategyStat {
  strategy: string;
  total: number;
  wins: number;
  losses: number;
  pnl: number;
  winRate: number;
  profitFactor: number;
  avgWin: number;
  avgLoss: number;
}


export default function AnalitikPage() {
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

  if (loading) return (
    <div>
      <PageHeader title="Analitik" subtitle="Performa strategi, symbol, dan metrik lanjutan" />
      <div className="grid gap-3 md:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-20 rounded-[15px] bg-card" />)}
      </div>
    </div>
  );

  const closed = trades.filter((t) => t.status === "closed" && t.profit != null);

  if (!closed.length) {
    return (
      <div>
        <PageHeader title="Analitik" subtitle="Performa strategi & statistik lanjutan" />
        <div className="glass-panel rounded-[15px] p-12 text-center text-sm text-muted-foreground">
          Belum ada trade closed untuk dianalisis
        </div>
      </div>
    );
  }

  const wins = closed.filter((t) => t.profit! >= 0);
  const losses = closed.filter((t) => t.profit! < 0);
  const grossWin = wins.reduce((s, t) => s + t.profit!, 0);
  const grossLoss = Math.abs(losses.reduce((s, t) => s + t.profit!, 0));
  const net = grossWin - grossLoss;
  const winRate = (wins.length / closed.length) * 100;
  const profitFactor = grossLoss > 0 ? grossWin / grossLoss : grossWin > 0 ? Infinity : 0;
  const avgRR = losses.length > 0 ? (grossWin / (wins.length || 1)) / (grossLoss / (losses.length || 1)) : 0;

  // by strategy
  const byStrategy = new Map<string, StrategyStat>();
  for (const t of closed) {
    const key = t.strategy || "unknown";
    const s = byStrategy.get(key) ?? { strategy: key, total: 0, wins: 0, losses: 0, pnl: 0, winRate: 0, profitFactor: 0, avgWin: 0, avgLoss: 0 };
    s.total++;
    s.pnl += t.profit!;
    if (t.profit! >= 0) s.wins++;
    else s.losses++;
    byStrategy.set(key, s);
  }
  const strategyStats = [...byStrategy.values()].map((s) => ({
    ...s,
    winRate: s.total ? (s.wins / s.total) * 100 : 0,
    profitFactor: s.losses ? (s.pnl >= 0 ? s.wins / s.losses : 0) : s.wins ? Infinity : 0,
    avgWin: s.wins ? grossWin / s.wins : 0,
    avgLoss: s.losses ? grossLoss / s.losses : 0,
  })).sort((a, b) => b.pnl - a.pnl);

  // by symbol
  const bySymbol = new Map<string, { total: number; pnl: number }>();
  for (const t of closed) {
    const cur = bySymbol.get(t.symbol) ?? { total: 0, pnl: 0 };
    cur.total++;
    cur.pnl += t.profit!;
    bySymbol.set(t.symbol, cur);
  }
  const symbolData = [...bySymbol.entries()].map(([name, v]) => ({
    name,
    pnl: Math.round(v.pnl * 100) / 100,
    trades: v.total,
  }));

  const sideData = [
    { name: "Buy", value: closed.filter((t) => (t.side ?? "").toLowerCase().startsWith("buy")).length },
    { name: "Sell", value: closed.filter((t) => (t.side ?? "").toLowerCase().startsWith("sell")).length },
  ].filter((d) => d.value > 0);

  return (
    <div>
      <PageHeader title="Analitik" subtitle="Performa strategi, symbol, dan metrik lanjutan" />

      {/* headline metrics */}
      <div className="mb-5 grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <Metric label="Net Profit" value={fmtMoney(net)} color={net >= 0 ? "text-positive" : "text-negative"} />
        <Metric label="Win Rate" value={`${winRate.toFixed(1)}%`} />
        <Metric label="Profit Factor" value={profitFactor === Infinity ? "∞" : profitFactor.toFixed(2)} />
        <Metric label="Avg RR" value={avgRR.toFixed(2)} />
        <Metric label="Total Closed" value={String(closed.length)} />
        <Metric label="Avg Win / Avg Loss" value={`${fmtMoney(avgRR > 0 ? grossWin / (wins.length || 1) : 0)} / ${fmtMoney(grossLoss / (losses.length || 1))}`} />
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        {/* pnl by symbol */}
        <ChartCard title="PnL per Symbol">
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={symbolData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--divider)" vertical={false} />
              <XAxis dataKey="name" tick={{ fill: "var(--muted-foreground)", fontSize: 11 }} axisLine={{ stroke: "var(--border)" }} tickLine={false} />
              <YAxis tick={{ fill: "var(--muted-foreground)", fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={(v: number) => fmtMoney(v)} />
              <Tooltip
                contentStyle={{ background: "var(--background)", border: "1px solid var(--border)", borderRadius: 15, color: "var(--foreground)", fontSize: 12, boxShadow: "none" }}
                labelStyle={{ color: "var(--muted-foreground)" }}
                itemStyle={{ color: "var(--signal)" }}
                cursor={{ fill: "var(--divider)" }}
                formatter={(value, name) => [fmtMoney(Number(value)), name === "pnl" ? "PnL" : "Trades"]}
              />
              <Bar dataKey="pnl" radius={[4, 4, 0, 0]}>
                {symbolData.map((d) => (
                  <Cell
                    key={d.name}
                    fill="var(--signal)"
                    stroke="var(--border)"
                    strokeWidth={1.5}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* buy/sell distribution */}
        <ChartCard title="Distribusi Buy vs Sell">
          <ResponsiveContainer width="100%" height={240}>
            <PieChart>
              <Pie data={sideData} dataKey="value" nameKey="name" innerRadius={50} outerRadius={80} paddingAngle={3}>
                {sideData.map((side) => (
                  <Cell key={side.name} fill={side.name === "Buy" ? "var(--buy)" : "var(--sell)"} stroke="var(--border)" strokeWidth={1.5} />
                ))}
              </Pie>
              <Tooltip contentStyle={{ background: "var(--background)", border: "1px solid var(--border)", color: "var(--foreground)", borderRadius: 15, fontSize: 12, boxShadow: "none" }} itemStyle={{ color: "var(--foreground)" }} />
              <Legend wrapperStyle={{ color: "var(--muted-foreground)", fontSize: 12 }} />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      {/* strategy table */}
      <div className="glass-panel mt-5 overflow-hidden rounded-[15px]">
        <div className="border-b border-divider px-5 py-4">
          <h2 className="text-sm font-semibold text-foreground">Performa per strategi</h2>
          <p className="mt-1 text-xs text-muted-foreground">Perbandingan hasil untuk strategi yang digunakan bot.</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[700px] text-[13px]">
            <thead className="bg-background">
              <tr className="border-b border-divider text-xs tracking-normal text-muted-foreground">
                <th className="py-2 pl-4 pr-2 text-left font-medium">Strategi</th>
                <th className="px-2 py-2 text-right font-medium">Trades</th>
                <th className="px-2 py-2 text-right font-medium">Win</th>
                <th className="px-2 py-2 text-right font-medium">Loss</th>
                <th className="px-2 py-2 text-right font-medium">Win Rate</th>
                <th className="px-2 py-2 text-right font-medium">Profit Factor</th>
                <th className="py-2 pl-2 pr-4 text-right font-medium">Net PnL</th>
              </tr>
            </thead>
            <tbody>
              {strategyStats.map((s) => (
                <tr key={s.strategy} className="border-b border-divider transition-colors hover:bg-background">
                  <td className="py-3 pl-4 pr-2 font-mono font-medium text-foreground">{s.strategy}</td>
                  <td className="px-2 py-3 text-right font-mono text-foreground">{s.total}</td>
                  <td className="px-2 py-3 text-right font-mono text-positive">{s.wins}</td>
                  <td className="px-2 py-3 text-right font-mono text-negative">{s.losses}</td>
                  <td className="px-2 py-3 text-right font-mono text-foreground">{s.winRate.toFixed(0)}%</td>
                  <td className="px-2 py-3 text-right font-mono text-foreground">
                    {s.profitFactor === Infinity ? "∞" : s.profitFactor.toFixed(2)}
                  </td>
                    <td className={cn("py-3 pl-2 pr-4 text-right font-mono font-semibold", s.pnl >= 0 ? "text-positive" : "text-negative")}>
                    {fmtMoney(s.pnl)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function Metric({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="glass-panel rounded-[15px] p-4">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className={cn("mt-1 font-sans text-xl font-semibold tracking-tight tabular-nums", color ?? "text-foreground")}>{value}</p>
    </div>
  );
}

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="glass-panel rounded-[15px] p-5">
      <h2 className="mb-4 text-sm font-semibold text-foreground">{title}</h2>
      {children}
    </div>
  );
}
