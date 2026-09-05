"use client";

import type { JournalEvent } from "@/lib/types";
import { fmtTime } from "@/lib/types";
import { cn } from "@/lib/utils";
import { TrendingUp, TrendingDown, Minus, BrainCircuit } from "lucide-react";
import { WidgetCard } from "@/components/dashboard-widgets";

export function SinyalWidget({ events, className }: { events: JournalEvent[]; className?: string }) {
  const decisions = events.filter((e) => e.kind === "decision");
  const buys = decisions.filter((e) => String((e.payload as Record<string, unknown>).decision).toUpperCase() === "BUY");
  const sells = decisions.filter((e) => String((e.payload as Record<string, unknown>).decision).toUpperCase() === "SELL");
  const holds = decisions.filter((e) => String((e.payload as Record<string, unknown>).decision).toUpperCase() === "HOLD");

  return (
    <WidgetCard title="Sinyal AI" href="/sinyal" className={className}>
      <div className="flex h-full flex-col gap-3">
        <div className="grid grid-cols-3 gap-2.5">
          <div className="glass-inset flex items-center gap-2 rounded-lg bg-emerald-500/10 px-2.5 py-2 ring-emerald-400/15">
            <TrendingUp className="h-4 w-4 shrink-0 text-emerald-400" />
            <div>
              <p className="text-[11px] font-medium tracking-normal text-zinc-500">Buy</p>
              <p className="font-mono text-lg font-semibold leading-tight text-emerald-400">{buys.length}</p>
            </div>
          </div>
          <div className="glass-inset flex items-center gap-2 rounded-lg bg-red-500/10 px-2.5 py-2 ring-red-400/15">
            <TrendingDown className="h-4 w-4 shrink-0 text-red-400" />
            <div>
              <p className="text-[11px] font-medium tracking-normal text-zinc-500">Sell</p>
              <p className="font-mono text-lg font-semibold leading-tight text-red-400">{sells.length}</p>
            </div>
          </div>
          <div className="glass-inset flex items-center gap-2 rounded-lg px-2.5 py-2">
            <Minus className="h-4 w-4 shrink-0 text-zinc-400" />
            <div>
              <p className="text-[11px] font-medium tracking-normal text-zinc-500">Hold</p>
              <p className="font-mono text-lg font-semibold leading-tight text-zinc-300">{holds.length}</p>
            </div>
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-hidden">
          {decisions.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center text-slate-500">
              <BrainCircuit className="mb-2 h-7 w-7 text-slate-600" />
              <p className="text-sm">Belum ada sinyal AI</p>
            </div>
          ) : (
            <div className="flex h-full flex-col gap-2 overflow-y-auto pr-1">
              {decisions.slice(0, 12).map((ev) => <DecisionMini key={ev.id} ev={ev} />)}
            </div>
          )}
        </div>
      </div>
    </WidgetCard>
  );
}

function DecisionMini({ ev }: { ev: JournalEvent }) {
  const p = ev.payload as Record<string, unknown>;
  const dec = String(p.decision ?? "?").toUpperCase();
  const conf = typeof p.confidence === "number" ? `${(p.confidence * 100).toFixed(0)}%` : "-";
  const color = dec === "BUY" ? "text-emerald-400" : dec === "SELL" ? "text-red-400" : "text-zinc-400";

  return (
    <div className="border-b border-slate-800/70 pb-2 last:border-0">
      <div className="flex items-center gap-2 text-xs">
        <span className="font-mono text-[11px] text-slate-500">{fmtTime(ev.ts)}</span>
        <span className="font-mono font-semibold text-slate-300">{ev.symbol}</span>
        <span className={cn("font-semibold", color)}>{dec}</span>
        <span className="ml-auto rounded-md bg-slate-900 px-1.5 py-0.5 text-[10px] text-slate-500">conf {conf}</span>
      </div>
      <p className="mt-1 line-clamp-1 pl-1 text-xs text-slate-500">{String(p.reason ?? "")}</p>
    </div>
  );
}
