"use client";

import { useLiveFeed } from "@/hooks/use-live-feed";
import { useBotStatus, fmtAge } from "@/hooks/use-bot-status";
import { PageHeader } from "@/components/page-header";
import { Terminal } from "@/components/terminal";
import { useState } from "react";
import { AlertTriangle, CheckCircle2 } from "lucide-react";

export default function TerminalPage() {
  const { events, connected } = useLiveFeed();
  const bot = useBotStatus(15000);
  const [filter, setFilter] = useState<string>("all");

  const kinds = ["all", "scan", "decision", "executed", "close", "pnl", "risk_block", "failed", "error"];
  const filtered =
    filter === "all"
      ? events
      : events.filter((e) => e.kind === filter);

  return (
    <div className="flex min-h-[calc(100vh-7rem)] flex-col">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <PageHeader
          title="Terminal"
          subtitle="Live stream aktivitas bot — scanning, keputusan, eksekusi"
          connected={connected}
        />
      </div>

      {/* status bot */}
      {bot && !bot.online && (
        <div role="alert" className="glass-inset mb-4 flex items-start gap-3 rounded-xl bg-red-500/10 px-4 py-3 text-sm ring-red-400/20">
          <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-red-300" />
          <div>
            <p className="font-medium text-red-200">Bot tidak berjalan</p>
            <p className="mt-0.5 text-[13px] leading-5 text-red-200/70">
              Tidak ada aktivitas sejak {fmtAge(bot.ageSec)}.
              Pastikan bot MT5 menyala di device trading.
            </p>
          </div>
        </div>
      )}
      {bot?.online && (
        <div className="mb-4 flex items-center gap-2 text-[13px] text-emerald-300/85">
          <CheckCircle2 className="h-4 w-4" />
          Bot aktif — aktivitas terakhir {fmtAge(bot.ageSec)}
        </div>
      )}

      {/* filter pills */}
      <div className="glass-panel mb-4 flex flex-wrap items-center gap-1.5 rounded-xl p-2">
        {kinds.map((k) => (
          <button
            key={k}
            onClick={() => setFilter(k)}
            type="button"
            aria-pressed={filter === k}
            className={
              filter === k
                ? "min-h-8 rounded-lg bg-blue-500/15 px-3 text-[13px] font-medium text-blue-200 ring-1 ring-inset ring-blue-400/25 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400/70"
                : "min-h-8 rounded-lg px-3 text-[13px] text-slate-400 transition-colors hover:bg-slate-800 hover:text-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400/70"
            }
          >
            {k === "all" ? "Semua" : k}
          </button>
        ))}
        <span className="ml-auto self-center px-2 text-xs text-slate-500">{filtered.length} event</span>
      </div>

      <div className="solid-data min-h-0 flex-1 overflow-hidden rounded-xl border p-2">
        <Terminal events={filtered.slice(0, 300)} className="h-full" />
      </div>
    </div>
  );
}
