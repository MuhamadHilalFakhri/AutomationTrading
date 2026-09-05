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
          <div className="glass-inset flex items-center gap-2 rounded-[15px] px-2.5 py-2">
            <TrendingUp className="h-4 w-4 shrink-0 text-buy" />
            <div>
              <p className="text-[11px] font-medium tracking-normal text-muted-foreground">Buy</p>
              <p className="font-sans text-lg font-semibold leading-tight tracking-tight tabular-nums text-buy">{buys.length}</p>
            </div>
          </div>
          <div className="glass-inset flex items-center gap-2 rounded-[15px] px-2.5 py-2">
            <TrendingDown className="h-4 w-4 shrink-0 text-sell" />
            <div>
              <p className="text-[11px] font-medium tracking-normal text-muted-foreground">Sell</p>
              <p className="font-sans text-lg font-semibold leading-tight tracking-tight tabular-nums text-sell">{sells.length}</p>
            </div>
          </div>
          <div className="glass-inset flex items-center gap-2 rounded-[15px] px-2.5 py-2">
            <Minus className="h-4 w-4 shrink-0 text-muted-foreground" />
            <div>
              <p className="text-[11px] font-medium tracking-normal text-muted-foreground">Hold</p>
              <p className="font-sans text-lg font-semibold leading-tight tracking-tight tabular-nums text-foreground">{holds.length}</p>
            </div>
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-hidden">
          {decisions.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center text-muted-foreground">
              <BrainCircuit className="mb-2 h-7 w-7 text-signal" />
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
  const color = dec === "BUY" ? "text-buy" : dec === "SELL" ? "text-sell" : "text-muted-foreground";

  return (
    <div className="border-b border-divider pb-2 last:border-0">
      <div className="flex items-center gap-2 text-xs">
        <span className="font-mono text-[11px] text-muted-foreground">{fmtTime(ev.ts)}</span>
        <span className="font-mono font-semibold text-foreground">{ev.symbol}</span>
        <span className={cn("font-semibold", color)}>{dec}</span>
        <span className="ml-auto rounded-full bg-background px-1.5 py-0.5 text-[10px] text-muted-foreground">conf {conf}</span>
      </div>
      <p className="mt-1 line-clamp-1 pl-1 text-xs text-muted-foreground">{String(p.reason ?? "")}</p>
    </div>
  );
}
