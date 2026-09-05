"use client";

import { PageHeader } from "@/components/page-header";
import { PnlCalendar } from "@/components/pnl-calendar";

export default function KalenderPage() {
  return (
    <div>
      <PageHeader title="Kalender PnL" subtitle="Rekap profit & loss harian per bulan" />
      <div className="glass-panel rounded-xl p-4 sm:p-6">
        <PnlCalendar />
      </div>
    </div>
  );
}
