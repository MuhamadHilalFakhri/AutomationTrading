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
      <div className="mb-5 grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div className="glass-inset rounded-xl bg-emerald-500/10 p-4 ring-emerald-400/15">
          <p className="text-xs text-emerald-200/70">Sinyal BUY</p>
          <p className="mt-1 font-mono text-xl font-semibold text-emerald-300">{buys}</p>
        </div>
        <div className="glass-inset rounded-xl bg-red-500/10 p-4 ring-red-400/15">
          <p className="text-xs text-red-200/70">Sinyal SELL</p>
          <p className="mt-1 font-mono text-xl font-semibold text-red-300">{sells}</p>
        </div>
        <div className="glass-inset rounded-xl p-4">
          <p className="text-xs text-slate-500">HOLD / No Trade</p>
          <p className="mt-1 font-mono text-xl font-semibold text-slate-300">{holds}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        {/* decisions */}
        <div className="glass-panel rounded-xl p-5">
          <h2 className="mb-4 text-sm font-semibold text-slate-100">Keputusan terakhir</h2>
          {decisions.length === 0 ? (
            <Empty text="Belum ada sinyal masuk" />
          ) : (
            <div className="flex flex-col gap-2.5">
              {decisions.slice(0, 30).map((ev) => <DecisionRow key={ev.id} ev={ev} />)}
            </div>
          )}
        </div>

        {/* executions / blocks */}
        <div className="glass-panel rounded-xl p-5">
          <h2 className="mb-4 text-sm font-semibold text-slate-100">Eksekusi & blokir</h2>
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
    <div className="border-b border-slate-800/70 pb-3 last:border-0">
      <div className="flex items-center gap-2 text-[13px]">
        <span className="font-mono text-[11px] text-slate-500">{fmtTime(ev.ts)}</span>
        <span className="font-mono font-semibold text-slate-300">{ev.symbol}</span>
        <span className={cn("font-semibold", decColor)}>{dec}</span>
        <span className="ml-auto rounded-md bg-slate-950/70 px-1.5 py-0.5 text-[10px] text-slate-500">
          conf {conf} · {strat}
        </span>
      </div>
      {reason && <p className="mt-1 pl-1 text-xs leading-5 text-slate-500">{reason}</p>}
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
    <div className="flex items-center gap-2 border-b border-slate-800/70 pb-3 text-[13px] last:border-0">
      <span className="font-mono text-[11px] text-slate-500">{fmtTime(ev.ts)}</span>
      <span className={cn("w-20 shrink-0 text-[11px] font-semibold", color)}>{label}</span>
      <span className="font-mono font-semibold text-slate-300">{ev.symbol}</span>
      <span className="min-w-0 flex-1 truncate text-slate-400">{desc}</span>
    </div>
  );
}

function Empty({ text }: { text: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-10 text-slate-500">
      <BrainCircuit className="mb-2 h-7 w-7 text-slate-600" />
      <p className="text-sm">{text}</p>
    </div>
  );
}
