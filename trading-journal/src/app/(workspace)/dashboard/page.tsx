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
      <div className="mb-5 grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
        <StatCard icon={<Activity className="h-4 w-4" />} label="Total Closed" value={stats?.totalClosed ?? 0} />
        <StatCard
          icon={<TrendingUp className="h-4 w-4" />}
          label="Win Rate"
          value={stats?.winRate != null ? `${stats.winRate}%` : "-"}
          valueClass={stats?.winRate != null ? (stats.winRate >= 50 ? "text-positive" : "text-negative") : ""}
        />
        <StatCard
          icon={stats?.realizedPnl != null && stats.realizedPnl < 0 ? <TrendingDown className="h-4 w-4" /> : <TrendingUp className="h-4 w-4" />}
          label="Realized PnL"
          value={stats?.realizedPnl != null ? fmtMoney(stats.realizedPnl) : "-"}
          valueClass={stats?.realizedPnl != null ? (stats.realizedPnl >= 0 ? "text-positive" : "text-negative") : ""}
        />
        <StatCard
          icon={<Layers className="h-4 w-4" />}
          label="Open Positions"
          value={stats?.openPositions ?? 0}
          valueClass={stats?.openPositions ? "text-warning" : ""}
        />
        <StatCard
          icon={<Clock className="h-4 w-4" />}
          label="Pending Orders"
          value={stats?.pendingOrders ?? 0}
        />
      </div>

      {/* row 1: PnL chart + Sinyal AI — tinggi seragam */}
      <div className="mb-5 grid grid-cols-1 gap-5 lg:grid-cols-3">
        <Card className="h-[350px] gap-2 rounded-[15px] border border-border bg-card py-4 shadow-none ring-0 lg:col-span-2">
          <CardHeader className="px-5 pb-1">
            <CardTitle className="text-sm font-semibold text-foreground">
              PnL 30 Hari
            </CardTitle>
            <CardAction>
              <a href="/kalender" className="flex items-center gap-1.5 rounded-full text-xs font-medium text-muted-foreground transition-colors hover:text-signal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                Kalender <ArrowRight className="h-3 w-3" />
              </a>
            </CardAction>
          </CardHeader>
          <CardContent className="min-h-0 flex-1 px-5">
            <DailyPnlChart days={pnlDays} className="h-full" />
          </CardContent>
        </Card>

        <SinyalWidget events={events} className="h-[340px]" />
      </div>

      {/* row 2: Analitik + Aktivitas/Terminal — tinggi seragam */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <AnalitikWidget className="h-[360px] lg:col-span-1" />

        <Card className="h-[360px] gap-2 rounded-[15px] border border-border bg-card py-4 shadow-none ring-0 lg:col-span-2">
          <CardHeader className="px-5 pb-1">
            <CardTitle className="text-sm font-semibold text-foreground">
              Aktivitas Terminal
            </CardTitle>
            <CardAction>
              <a href="/terminal" className="flex items-center gap-1.5 rounded-full text-xs font-medium text-muted-foreground transition-colors hover:text-signal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                Terminal <ArrowRight className="h-3 w-3" />
              </a>
            </CardAction>
          </CardHeader>
          <CardContent className="min-h-0 flex-1 overflow-hidden px-3 sm:px-5">
            <div className="scrollbar-subtle h-full overflow-y-auto pr-1">
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
    <Card size="sm" className="gap-1 rounded-[15px] border border-border bg-card py-4 shadow-none ring-0 transition-colors hover:border-signal">
      <CardContent className="px-4">
        <div className="mb-2 flex items-center gap-2 text-xs text-muted-foreground">
          <span className={cn(valueClass || "text-signal")}>{icon}</span>
          <span>{label}</span>
        </div>
        <div className={cn("font-sans text-[23px] font-semibold tracking-tight tabular-nums", valueClass || "text-foreground")}>
          {value}
        </div>
      </CardContent>
    </Card>
  );
}
