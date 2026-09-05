"use client";

import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip,
  CartesianGrid,
} from "recharts";
import { fmtMoney } from "@/lib/types";
import { cn } from "@/lib/utils";

export interface PnlPoint {
  date: string;
  realized: number;
}

export function DailyPnlChart({ days, className }: { days: PnlPoint[]; className?: string }) {
  if (!days.length) {
    return (
      <div className={cn("flex w-full items-center justify-center text-sm text-slate-500", className ?? "h-56")}>
        Belum ada data PnL
      </div>
    );
  }

  // cumulative balance curve via reduce (no render-phase mutation)
  const data = days.reduce<{ date: string; day: number; balance: number }[]>((acc, d) => {
    const prev = acc.length ? acc[acc.length - 1].balance : 0;
    acc.push({
      date: d.date.slice(5),
      day: d.realized,
      balance: Math.round((prev + d.realized) * 100) / 100,
    });
    return acc;
  }, []);

  return (
    <div className={cn("w-full", className ?? "h-56")}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 5, right: 5, bottom: 0, left: 0 }}>
          <defs>
            <linearGradient id="pnlFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#60a5fa" stopOpacity={0.24} />
              <stop offset="100%" stopColor="#60a5fa" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#26354d" vertical={false} />
          <XAxis
            dataKey="date"
            tick={{ fill: "#94a3b8", fontSize: 11 }}
            axisLine={{ stroke: "#334155" }}
            tickLine={false}
            minTickGap={20}
          />
          <YAxis
            tick={{ fill: "#94a3b8", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            width={52}
            tickFormatter={(v: number) => fmtMoney(v)}
          />
          <Tooltip
            contentStyle={{
              background: "#172033",
              border: "1px solid #334155",
              borderRadius: 8,
              fontSize: 12,
            }}
            labelStyle={{ color: "#cbd5e1" }}
            formatter={(value, name) => [fmtMoney(Number(value)), name === "day" ? "PnL harian" : "Balance kumulatif"]}
          />
          <Area
            type="monotone"
            dataKey="balance"
            stroke="#60a5fa"
            strokeWidth={2}
            fill="url(#pnlFill)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
