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
      <div className={cn("flex w-full items-center justify-center border border-black bg-card font-sans text-sm text-muted-foreground shadow-none", className ?? "h-56")}>
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
    <div className={cn("w-full border border-black bg-card font-sans shadow-none", className ?? "h-56")}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 5, right: 5, bottom: 0, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(205,208,214,.12)" vertical={false} />
          <XAxis
            dataKey="date"
            tick={{ fill: "#cdd0d6", fontSize: 11, fontFamily: "var(--font-inter), Inter, sans-serif" }}
            axisLine={{ stroke: "var(--divider, rgba(205,208,214,.15))" }}
            tickLine={false}
            minTickGap={20}
          />
          <YAxis
            tick={{ fill: "#cdd0d6", fontSize: 11, fontFamily: "var(--font-inter), Inter, sans-serif" }}
            axisLine={false}
            tickLine={false}
            width={52}
            tickFormatter={(v: number) => fmtMoney(v)}
          />
          <Tooltip
            contentStyle={{
              background: "#202a3e",
              border: "1px solid #000000",
              color: "#ffffff",
              boxShadow: "none",
              borderRadius: 8,
              fontSize: 12,
            }}
            labelStyle={{ color: "#cdd0d6" }}
            itemStyle={{ color: "#ffffff" }}
            cursor={{ stroke: "#6ae4ff" }}
            formatter={(value, name) => [fmtMoney(Number(value)), name === "day" ? "PnL harian" : "Balance kumulatif"]}
          />
          <Area
            type="monotone"
            dataKey="balance"
            stroke="#6ae4ff"
            strokeWidth={2}
            fill="transparent"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
