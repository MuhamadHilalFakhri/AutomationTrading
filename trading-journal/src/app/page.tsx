"use client";

import { useEffect, useState } from "react";
import { useLiveFeed, useStats } from "@/hooks/use-live-feed";
import { PageHeader } from "@/components/page-header";
import { fmtMoney } from "@/lib/types";
import { cn } from "@/lib/utils";
import {
  Activity, TrendingUp, TrendingDown, Layers, Clock, ArrowRight,
} from "lucide-react";
import { DailyPnlChart } from "@/components/pnl-chart";
import { RecentEvents } from "@/components/recent-events";
import { AnalitikWidget } from "@/components/dashboard-widgets";
import { SinyalWidget } from "@/components/sinyal-widget";
import { Card, CardContent, CardHeader, CardTitle, CardAction } from "@/components/ui/card";

export default function DashboardPage() {
  const { events, connected } = useLiveFeed();
  const { stats } = useStats(5000);
  const [pnlDays, setPnlDays] = useState<{ date: string; realized: number }[]>([]);

  useEffect(() => {
    let active = true;
    fetch("/api/pnl/daily?range=30", { cache: "no-store" })
      .then((r) => r.json())
      .then((d) => { if (active) setPnlDays(d.days ?? []); })
      .catch(() => {});
    return () => { active = false; };
  }, []);

  return (
    <div>
      <PageHeader title="Dashboard" subtitle="Ringkasan performa bot trading" connected={connected} />

      {/* stats grid */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5 mb-4">
        <StatCard icon={<Activity className="h-4 w-4" />} label="Total Closed" value={stats?.totalClosed ?? 0} />
        <StatCard
          icon={<TrendingUp className="h-4 w-4" />}
          label="Win Rate"
          value={stats?.winRate != null ? `${stats.winRate}%` : "-"}
          valueClass={stats?.winRate != null && stats.winRate >= 50 ? "text-emerald-400" : "text-red-400"}
        />
        <StatCard
          icon={<TrendingDown className="h-4 w-4" />}
          label="Realized PnL"
          value={stats?.realizedPnl != null ? fmtMoney(stats.realizedPnl) : "-"}
          valueClass={stats?.realizedPnl != null ? (stats.realizedPnl >= 0 ? "text-emerald-400" : "text-red-400") : ""}
        />
        <StatCard
          icon={<Layers className="h-4 w-4" />}
          label="Open Positions"
          value={stats?.openPositions ?? 0}
          valueClass={stats?.openPositions ? "text-amber-400" : ""}
        />
        <StatCard
          icon={<Clock className="h-4 w-4" />}
          label="Pending Orders"
          value={stats?.pendingOrders ?? 0}
        />
      </div>

      {/* row 1: PnL chart + Sinyal AI — tinggi seragam */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3 mb-4">
        <Card className="h-[340px] gap-2 py-3 lg:col-span-2">
          <CardHeader className="px-4 pb-0">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
              PnL 30 Hari
            </CardTitle>
            <CardAction>
              <a href="/kalender" className="flex items-center gap-1 text-xs text-zinc-600 hover:text-zinc-300">
                Kalender <ArrowRight className="h-3 w-3" />
              </a>
            </CardAction>
          </CardHeader>
          <CardContent className="min-h-0 flex-1 px-4">
            <DailyPnlChart days={pnlDays} className="h-full" />
          </CardContent>
        </Card>

        <SinyalWidget events={events} className="h-[340px]" />
      </div>

      {/* row 2: Analitik + Aktivitas/Terminal — tinggi seragam */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <AnalitikWidget className="h-[360px] lg:col-span-1" />

        <Card className="h-[360px] gap-2 py-3 lg:col-span-2">
          <CardHeader className="px-4 pb-0">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
              Aktivitas Terminal
            </CardTitle>
            <CardAction>
              <a href="/terminal" className="flex items-center gap-1 text-xs text-zinc-600 hover:text-zinc-300">
                Terminal <ArrowRight className="h-3 w-3" />
              </a>
            </CardAction>
          </CardHeader>
          <CardContent className="min-h-0 flex-1 overflow-hidden px-2">
            <div className="h-full overflow-y-auto pr-1">
              <RecentEvents events={events.slice(0, 60)} />
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function StatCard({
  icon, label, value, valueClass,
}: {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  valueClass?: string;
}) {
  return (
    <Card size="sm" className="gap-1 py-3 transition-colors hover:ring-foreground/20">
      <CardContent className="px-3">
        <div className="mb-1 flex items-center gap-2 text-xs text-zinc-500">
          {icon}
          <span>{label}</span>
        </div>
        <div className={cn("font-mono text-2xl font-bold tracking-tight", valueClass ?? "")}>
          {value}
        </div>
      </CardContent>
    </Card>
  );
}
