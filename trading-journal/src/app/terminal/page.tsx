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
    <div className="flex h-[calc(100vh-3.5rem)] flex-col lg:h-[calc(100vh-3rem)]">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <PageHeader
          title="Terminal"
          subtitle="Live stream aktivitas bot — scanning, keputusan, eksekusi"
          connected={connected}
        />
      </div>

      {/* status bot */}
      {bot && !bot.online && (
        <div className="mb-3 flex items-start gap-2.5 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-2.5 text-sm">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-red-400" />
          <div>
            <p className="font-medium text-red-300">Bot tidak berjalan</p>
            <p className="text-xs text-red-300/70">
              Tidak ada aktivitas sejak {fmtAge(bot.ageSec)}.
              Pastikan bot MT5 menyala di device trading.
            </p>
          </div>
        </div>
      )}
      {bot?.online && (
        <div className="mb-3 flex items-center gap-2 text-xs text-emerald-400/80">
          <CheckCircle2 className="h-3.5 w-3.5" />
          Bot aktif — aktivitas terakhir {fmtAge(bot.ageSec)}
        </div>
      )}

      {/* filter pills */}
      <div className="-mt-4 mb-3 flex flex-wrap gap-1.5">
        {kinds.map((k) => (
          <button
            key={k}
            onClick={() => setFilter(k)}
            className={
              filter === k
                ? "rounded-full bg-zinc-800 px-3 py-1 text-xs font-medium text-zinc-100"
                : "rounded-full border border-zinc-800 px-3 py-1 text-xs text-zinc-500 hover:bg-zinc-900"
            }
          >
            {k === "all" ? "Semua" : k}
          </button>
        ))}
        <span className="ml-auto self-center text-xs text-zinc-600">{filtered.length} event</span>
      </div>

      <div className="min-h-0 flex-1 rounded-xl border border-zinc-800 bg-zinc-950 p-2">
        <Terminal events={filtered.slice(0, 300)} className="h-full" />
      </div>
    </div>
  );
}