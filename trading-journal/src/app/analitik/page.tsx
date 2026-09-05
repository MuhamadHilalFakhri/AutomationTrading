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

const CHART_PROFIT_FILL = "rgba(16, 185, 129, 0.62)";
const CHART_PROFIT_STROKE = "#6ee7b7";
const CHART_LOSS_FILL = "rgba(244, 63, 94, 0.62)";
const CHART_LOSS_STROKE = "#fda4af";

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
        {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-20 rounded-xl bg-slate-800" />)}
      </div>
    </div>
  );

  const closed = trades.filter((t) => t.status === "closed" && t.profit != null);

  if (!closed.length) {
    return (
      <div>
        <PageHeader title="Analitik" subtitle="Performa strategi & statistik lanjutan" />
        <div className="glass-panel rounded-xl p-12 text-center text-sm text-slate-500">
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
        <Metric label="Net Profit" value={fmtMoney(net)} color={net >= 0 ? "text-emerald-400" : "text-red-400"} />
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
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
              <XAxis dataKey="name" tick={{ fill: "#cbd5e1", fontSize: 11 }} axisLine={{ stroke: "#475569" }} tickLine={false} />
              <YAxis tick={{ fill: "#cbd5e1", fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={(v: number) => fmtMoney(v)} />
              <Tooltip
                contentStyle={{ background: "#172033", border: "1px solid #475569", borderRadius: 8, color: "#f8fafc", fontSize: 12 }}
                labelStyle={{ color: "#e2e8f0" }}
                formatter={(value, name) => [fmtMoney(Number(value)), name === "pnl" ? "PnL" : "Trades"]}
              />
              <Bar dataKey="pnl" radius={[4, 4, 0, 0]}>
                {symbolData.map((d) => (
                  <Cell
                    key={d.name}
                    fill={d.pnl >= 0 ? CHART_PROFIT_FILL : CHART_LOSS_FILL}
                    stroke={d.pnl >= 0 ? CHART_PROFIT_STROKE : CHART_LOSS_STROKE}
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
                <Cell fill={CHART_PROFIT_FILL} stroke={CHART_PROFIT_STROKE} strokeWidth={1.5} />
                <Cell fill={CHART_LOSS_FILL} stroke={CHART_LOSS_STROKE} strokeWidth={1.5} />
              </Pie>
              <Tooltip contentStyle={{ background: "#172033", border: "1px solid #475569", color: "#f8fafc", borderRadius: 8, fontSize: 12 }} />
              <Legend wrapperStyle={{ color: "#cbd5e1", fontSize: 12 }} />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      {/* strategy table */}
      <div className="glass-panel mt-5 overflow-hidden rounded-xl">
        <div className="border-b border-slate-800 px-5 py-4">
          <h2 className="text-sm font-semibold text-slate-100">Performa per strategi</h2>
          <p className="mt-1 text-xs text-slate-500">Perbandingan hasil untuk strategi yang digunakan bot.</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[700px] text-[13px]">
            <thead className="bg-slate-950/45">
              <tr className="border-b border-slate-800 text-xs tracking-normal text-slate-500">
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
                <tr key={s.strategy} className="border-b border-slate-800/70 transition-colors hover:bg-blue-500/[0.04]">
                  <td className="py-3 pl-4 pr-2 font-mono font-medium text-slate-300">{s.strategy}</td>
                  <td className="px-2 py-3 text-right font-mono text-slate-300">{s.total}</td>
                  <td className="px-2 py-3 text-right font-mono text-emerald-400">{s.wins}</td>
                  <td className="px-2 py-3 text-right font-mono text-red-400">{s.losses}</td>
                  <td className="px-2 py-3 text-right font-mono text-slate-300">{s.winRate.toFixed(0)}%</td>
                  <td className="px-2 py-3 text-right font-mono text-slate-300">
                    {s.profitFactor === Infinity ? "∞" : s.profitFactor.toFixed(2)}
                  </td>
                    <td className={cn("py-3 pl-2 pr-4 text-right font-mono font-semibold", s.pnl >= 0 ? "text-emerald-400" : "text-red-400")}>
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
    <div className="glass-panel rounded-xl p-4">
      <p className="text-xs text-slate-500">{label}</p>
      <p className={cn("mt-1 font-mono text-xl font-semibold", color ?? "text-slate-100")}>{value}</p>
    </div>
  );
}

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="glass-panel rounded-xl p-5">
      <h2 className="mb-4 text-sm font-semibold text-slate-100">{title}</h2>
      {children}
    </div>
  );
}
