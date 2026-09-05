"use client";

import { useEffect, useRef } from "react";
import type { JournalEvent } from "@/lib/types";
import { fmtTime } from "@/lib/types";
import { cn } from "@/lib/utils";

const KIND_STYLE: Record<string, { color: string; label: string }> = {
  scan: { color: "text-amber-500", label: "SCAN" },
  decision: { color: "text-sky-400", label: "DECISION" },
  executed: { color: "text-emerald-400", label: "EXEC" },
  failed: { color: "text-red-400", label: "FAIL" },
  risk_block: { color: "text-red-400", label: "RISK" },
  close: { color: "text-amber-400", label: "CLOSE" },
  pnl: { color: "text-emerald-400", label: "PNL" },
  status: { color: "text-slate-400", label: "STATUS" },
  error: { color: "text-red-400", label: "ERROR" },
};

function describeEvent(ev: JournalEvent): string {
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

export function Terminal({ events, className }: { events: JournalEvent[]; className?: string }) {
  const boxRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    boxRef.current?.scrollTo({ top: 0 });
  }, [events]);

  return (
    <div
      ref={boxRef}
      className={cn(
        "solid-data scrollbar-subtle h-full overflow-y-auto rounded-lg p-4 font-mono text-xs leading-relaxed",
        className,
      )}
    >
      {events.length === 0 ? (
        <p className="text-slate-500">Menunggu aktivitas bot...</p>
      ) : (
        <div className="flex flex-col-reverse gap-0.5">
          {events.map((ev) => {
            const style = KIND_STYLE[ev.kind] ?? { color: "text-zinc-400", label: ev.kind.toUpperCase() };
            return (
              <div key={ev.id} className="flex gap-2 border-b border-slate-900/80 py-1">
                <span className="shrink-0 text-slate-500">{fmtTime(ev.ts)}</span>
                <span className={cn("w-20 shrink-0 font-semibold", style.color)}>{style.label}</span>
                <span className="min-w-0 break-words text-zinc-300">{describeEvent(ev)}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
