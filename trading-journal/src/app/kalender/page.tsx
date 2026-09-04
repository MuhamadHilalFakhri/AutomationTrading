"use client";

import { PageHeader } from "@/components/page-header";
import { PnlCalendar } from "@/components/pnl-calendar";

export default function KalenderPage() {
  return (
    <div>
      <PageHeader title="Kalender PnL" subtitle="Rekap profit & loss harian per bulan" />
      <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-4 sm:p-6">
        <PnlCalendar />
      </div>
    </div>
  );
}