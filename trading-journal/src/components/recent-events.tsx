"use client";

import type { JournalEvent } from "@/lib/types";
import { fmtTime } from "@/lib/types";
import { cn } from "@/lib/utils";

const KIND_STYLE: Record<string, { color: string; label: string }> = {
  scan: { color: "text-warning", label: "SCAN" },
  decision: { color: "text-signal", label: "DECISION" },
  executed: { color: "text-positive", label: "EXEC" },
  failed: { color: "text-negative", label: "FAIL" },
  risk_block: { color: "text-warning", label: "RISK" },
  close: { color: "text-muted-foreground", label: "CLOSE" },
  pnl: { color: "text-foreground", label: "PNL" },
  status: { color: "text-muted-foreground", label: "STATUS" },
  error: { color: "text-negative", label: "ERROR" },
};

export function describeEvent(ev: JournalEvent): string {
  const p = ev.payload as Record<string, unknown>;
  switch (ev.kind) {
    case "scan":
      return `mengambil data market ${ev.symbol ?? ""}...`;
    case "decision": {
      const dec = String(p.decision ?? "?");
      const conf = typeof p.confidence === "number" ? `${(p.confidence * 100).toFixed(0)}%` : "?";
      const strat = String(p.strategy ?? "");
      return `${ev.symbol} ${dec} (conf ${conf}${strat ? `, ${strat}` : ""}) — ${String(p.reason ?? "").slice(0, 110)}`;
    }
    case "executed":
      return `${ev.symbol} ${p.order_type} ${p.lots ?? "?"} lot @ ${p.entry ?? "?"} — order terkirim`;
    case "failed":
      return `${ev.symbol} order gagal: ${String(p.message ?? "").slice(0, 110)}`;
    case "risk_block":
      return `${ev.symbol} ditolak risk guard: ${String(p.reason ?? "").slice(0, 110)}`;
    case "close": {
      const results = Array.isArray(p.results) ? p.results : [];
      const parts = results.map((r) => {
        const rr = r as Record<string, unknown>;
        return `#${rr.ticket} ${rr.ok ? "ok" : "gagal"}`;
      });
      return `${ev.symbol} posisi ditutup (${parts.join(", ")})`;
    }
    case "pnl":
      return `laporan — balance ${fmtMoneySafe(p.balance)} / equity ${fmtMoneySafe(p.equity)} / floating ${fmtMoneySafe(p.profit)}`;
    case "error":
      return String(p.message ?? JSON.stringify(p)).slice(0, 140);
    default:
      return JSON.stringify(p).slice(0, 140);
  }
}

function fmtMoneySafe(v: unknown): string {
  const n = Number(v);
  return Number.isFinite(n) ? `$${n.toFixed(2)}` : "-";
}

export function RecentEvents({ events }: { events: JournalEvent[] }) {
  if (!events.length) {
    return (
      <div className="flex flex-col items-center justify-center py-10 text-muted-foreground">
        <p className="text-sm">Menunggu aktivitas bot...</p>
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-2.5">
      {events.slice(0, 40).map((ev) => {
        const style = KIND_STYLE[ev.kind] ?? { color: "text-muted-foreground", label: ev.kind.toUpperCase() };
        return (
          <div key={ev.id} className="flex items-start gap-2 border-b border-divider pb-2.5 last:border-0">
            <span className="shrink-0 font-mono text-[11px] text-muted-foreground">{fmtTime(ev.ts)}</span>
            <span className={cn("w-16 shrink-0 text-[11px] font-semibold", style.color)}>{style.label}</span>
            <span className="min-w-0 flex-1 text-[13px] leading-5 text-foreground">
              {ev.symbol && <span className="font-mono text-muted-foreground">{ev.symbol} </span>}
              {describeEvent(ev)}
            </span>
          </div>
        );
      })}
    </div>
  );
}
