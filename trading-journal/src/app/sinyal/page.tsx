"use client";

import { useLiveFeed } from "@/hooks/use-live-feed";
import { PageHeader } from "@/components/page-header";
import type { JournalEvent } from "@/lib/types";
import { fmtTime } from "@/lib/types";
import { cn } from "@/lib/utils";
import { BrainCircuit } from "lucide-react";

export default function SinyalPage() {
  const { events, connected } = useLiveFeed();

  const decisions = events.filter((e) => e.kind === "decision");
  const execs = events.filter((e) => e.kind === "executed" || e.kind === "failed" || e.kind === "risk_block");

  const buys = decisions.filter((e) => String((e.payload as Record<string, unknown>).decision).toUpperCase() === "BUY").length;
  const sells = decisions.filter((e) => String((e.payload as Record<string, unknown>).decision).toUpperCase() === "SELL").length;
  const holds = decisions.filter((e) => String((e.payload as Record<string, unknown>).decision).toUpperCase() === "HOLD").length;

  return (
    <div>
      <PageHeader
        title="Sinyal AI"
        subtitle="Semua keputusan yang diambil AI — BUY, SELL, HOLD beserta alasannya"
        connected={connected}
      />

      {/* summary */}
      <div className="mb-4 grid grid-cols-3 gap-3">
        <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-3">
          <p className="text-xs text-zinc-500">Sinyal BUY</p>
          <p className="font-mono text-lg font-bold text-emerald-400">{buys}</p>
        </div>
        <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-3">
          <p className="text-xs text-zinc-500">Sinyal SELL</p>
          <p className="font-mono text-lg font-bold text-red-400">{sells}</p>
        </div>
        <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-3">
          <p className="text-xs text-zinc-500">HOLD / No Trade</p>
          <p className="font-mono text-lg font-bold text-zinc-400">{holds}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* decisions */}
        <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-4">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-zinc-400">Keputusan Terakhir</h2>
          {decisions.length === 0 ? (
            <Empty text="Belum ada sinyal masuk" />
          ) : (
            <div className="flex flex-col gap-2.5">
              {decisions.slice(0, 30).map((ev) => <DecisionRow key={ev.id} ev={ev} />)}
            </div>
          )}
        </div>

        {/* executions / blocks */}
        <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-4">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-zinc-400">Eksekusi & Blokir</h2>
          {execs.length === 0 ? (
            <Empty text="Belum ada eksekusi" />
          ) : (
            <div className="flex flex-col gap-2.5">
              {execs.slice(0, 30).map((ev) => <ExecRow key={ev.id} ev={ev} />)}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function DecisionRow({ ev }: { ev: JournalEvent }) {
  const p = ev.payload as Record<string, unknown>;
  const dec = String(p.decision ?? "?").toUpperCase();
  const conf = typeof p.confidence === "number" ? `${(p.confidence * 100).toFixed(0)}%` : "-";
  const strat = String(p.strategy ?? "-");
  const reason = String(p.reason ?? "");

  const decColor = dec === "BUY" ? "text-emerald-400" : dec === "SELL" ? "text-red-400" : "text-zinc-400";

  return (
    <div className="border-b border-zinc-900/60 pb-2 last:border-0">
      <div className="flex items-center gap-2 text-xs">
        <span className="font-mono text-[10px] text-zinc-600">{fmtTime(ev.ts)}</span>
        <span className="font-mono font-semibold text-zinc-300">{ev.symbol}</span>
        <span className={cn("font-bold", decColor)}>{dec}</span>
        <span className="ml-auto rounded bg-zinc-900 px-1.5 py-0.5 text-[10px] text-zinc-500">
          conf {conf} · {strat}
        </span>
      </div>
      {reason && <p className="mt-1 pl-1 text-[11px] leading-snug text-zinc-500">{reason}</p>}
    </div>
  );
}

function ExecRow({ ev }: { ev: JournalEvent }) {
  const p = ev.payload as Record<string, unknown>;
  const isExec = ev.kind === "executed";
  const label = isExec ? "EXECUTED" : ev.kind === "failed" ? "FAILED" : "RISK BLOCK";
  const color = isExec ? "text-emerald-400" : "text-red-400";
  const desc = isExec
    ? `${p.order_type} ${p.lots ?? "?"} lot @ ${p.entry ?? "?"}`
    : String(p.message ?? p.reason ?? "");

  return (
    <div className="flex items-center gap-2 border-b border-zinc-900/60 pb-2 text-xs last:border-0">
      <span className="font-mono text-[10px] text-zinc-600">{fmtTime(ev.ts)}</span>
      <span className={cn("w-20 shrink-0 text-[10px] font-bold", color)}>{label}</span>
      <span className="font-mono font-semibold text-zinc-300">{ev.symbol}</span>
      <span className="min-w-0 flex-1 truncate text-zinc-400">{desc}</span>
    </div>
  );
}

function Empty({ text }: { text: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-10 text-zinc-600">
      <BrainCircuit className="mb-2 h-7 w-7 text-zinc-700" />
      <p className="text-sm">{text}</p>
    </div>
  );
}
