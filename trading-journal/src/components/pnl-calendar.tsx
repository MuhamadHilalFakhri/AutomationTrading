"use client";

import { useState, useEffect } from "react";
import { cn } from "@/lib/utils";
import type { DailyPnl } from "@/lib/types";
import { fmtMoney } from "@/lib/types";
import { wibNow } from "@/lib/wib";
import { ChevronLeft, ChevronRight } from "lucide-react";

export function PnlCalendar() {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth());
  const [dataMap, setDataMap] = useState<Record<string, DailyPnl>>({});

  const monthStart = `${year}-${String(month + 1).padStart(2, "0")}-01`;
  const monthEnd = new Date(year, month + 1, 0).toISOString().slice(0, 10);

  useEffect(() => {
    let active = true;
    fetch(`/api/pnl/daily?start=${monthStart}&end=${monthEnd}`, { cache: "no-store" })
      .then((r) => r.json())
      .then((data) => {
        if (!active) return;
        const map: Record<string, DailyPnl> = {};
        for (const d of (data.days ?? []) as DailyPnl[]) map[d.date] = d;
        setDataMap(map);
      })
      .catch(() => {});
    return () => { active = false; };
  }, [monthStart, monthEnd]);

  const first = new Date(year, month, 1);
  const last = new Date(year, month + 1, 0);
  const today = wibNow();
  const daysInMonth = last.getDate();
  const startDow = (first.getDay() + 6) % 7; // Mon=0
  const dayHeaders = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"];

  const prevMonth = () => { if (month === 0) { setYear(year - 1); setMonth(11); } else setMonth(month - 1); };
  const nextMonth = () => { if (month === 11) { setYear(year + 1); setMonth(0); } else setMonth(month + 1); };

  let monthPnl = 0, monthTrades = 0, monthWins = 0;
  for (const d of Object.values(dataMap)) {
    monthPnl += d.realized;
    monthTrades += d.tradeCount;
    monthWins += d.wins;
  }

  const name = first.toLocaleDateString("id-ID", { month: "long", year: "numeric" });

  return (
    <div>
      <div className="mb-4 flex items-center justify-between gap-2">
        <button type="button" onClick={prevMonth} className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-slate-700 text-slate-400 transition-colors hover:bg-slate-800 hover:text-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400/70" aria-label="Bulan sebelumnya">
          <ChevronLeft className="h-4 w-4" />
        </button>
        <span className="text-sm font-semibold capitalize text-slate-100">{name}</span>
        <button type="button" onClick={nextMonth} className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-slate-700 text-slate-400 transition-colors hover:bg-slate-800 hover:text-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400/70" aria-label="Bulan berikutnya">
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>

      <div className="mb-4 grid grid-cols-3 gap-2 text-center text-xs">
        <div className="glass-inset rounded-lg p-2.5">
          <div className={cn("font-mono font-semibold", monthPnl >= 0 ? "text-emerald-300" : "text-red-300")}>{fmtMoney(monthPnl)}</div>
          <div className="mt-1 text-slate-500">Monthly PnL</div>
        </div>
        <div className="glass-inset rounded-lg p-2.5">
          <div className="font-mono font-semibold text-slate-100">{monthTrades}</div>
          <div className="mt-1 text-slate-500">Trades</div>
        </div>
        <div className="glass-inset rounded-lg p-2.5">
          <div className="font-mono font-semibold text-slate-100">{monthTrades ? Math.round((monthWins / monthTrades) * 100) + "%" : "0%"}</div>
          <div className="mt-1 text-slate-500">Win Rate</div>
        </div>
      </div>

      <div className="grid grid-cols-7 gap-1.5 text-xs">
        {dayHeaders.map((d) => (
          <div key={d} className="py-1 text-center text-[11px] font-medium text-slate-500">{d}</div>
        ))}
        {Array.from({ length: startDow }).map((_, i) => (
          <div key={`empty-${i}`} />
        ))}
        {Array.from({ length: daysInMonth }).map((_, i) => {
          const d = i + 1;
          const dateStr = `${year}-${String(month + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
          const info = dataMap[dateStr];
          const isToday = dateStr === today;
          const pnl = info?.realized ?? 0;
          return (
            <div
              key={d}
              className={cn(
                "flex aspect-[5/4] flex-col items-center justify-center rounded-lg border p-1",
                isToday ? "border-blue-400/60" : "border-slate-800/60",
                info && pnl > 0 ? "bg-emerald-500/10" : info && pnl < 0 ? "bg-red-500/10" : "bg-slate-950/35",
              )}
            >
              <span className={cn("font-medium", isToday ? "text-blue-300" : "text-slate-400")}>{d}</span>
              {info ? (
                <>
                  <span className={cn("text-[10px] leading-none", pnl >= 0 ? "text-emerald-300" : "text-red-300")}>
                    {pnl >= 0 ? "+" : ""}${Math.abs(pnl).toFixed(0)}
                  </span>
                  <span className="text-[10px] text-slate-500 leading-none">{info.tradeCount}t</span>
                </>
              ) : (
                <span className="text-[9px] leading-none">&nbsp;</span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
