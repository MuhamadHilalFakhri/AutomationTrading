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
        <div role="alert" className="glass-inset mb-4 flex items-start gap-3 rounded-[15px] px-4 py-3 text-sm">
          <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-warning" />
          <div>
            <p className="font-medium text-foreground">Bot tidak berjalan</p>
            <p className="mt-0.5 text-[13px] leading-5 text-muted-foreground">
              Tidak ada aktivitas sejak {fmtAge(bot.ageSec)}.
              Pastikan bot MT5 menyala di device trading.
            </p>
          </div>
        </div>
      )}
      {bot?.online && (
        <div className="mb-4 flex items-center gap-2 text-[13px] text-positive">
          <CheckCircle2 className="h-4 w-4" />
          Bot aktif — aktivitas terakhir {fmtAge(bot.ageSec)}
        </div>
      )}

      {/* filter pills */}
      <div className="glass-panel mb-4 flex flex-wrap items-center gap-1.5 rounded-[15px] p-2">
        {kinds.map((k) => (
          <button
            key={k}
            onClick={() => setFilter(k)}
            type="button"
            aria-pressed={filter === k}
            className={
              filter === k
                ? "min-h-8 rounded-full border border-border bg-foreground px-3 text-[13px] font-medium text-black focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                : "min-h-8 rounded-full border border-border px-3 text-[13px] text-muted-foreground transition-colors hover:bg-background hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            }
          >
            {k === "all" ? "Semua" : k}
          </button>
        ))}
        <span className="ml-auto self-center px-2 text-xs text-muted-foreground">{filtered.length} event</span>
      </div>

      <div className="solid-data min-h-0 flex-1 overflow-hidden rounded-[15px] border border-border p-2">
        <Terminal events={filtered.slice(0, 300)} className="h-full" />
      </div>
    </div>
  );
}
