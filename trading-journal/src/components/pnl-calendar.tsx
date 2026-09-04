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
      <div className="flex items-center gap-2 mb-3">
        <button onClick={prevMonth} className="rounded-md border border-zinc-700 p-1 hover:bg-zinc-800">
          <ChevronLeft className="h-4 w-4" />
        </button>
        <span className="font-semibold text-sm">{name}</span>
        <button onClick={nextMonth} className="rounded-md border border-zinc-700 p-1 hover:bg-zinc-800">
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>

      <div className="grid grid-cols-3 gap-2 mb-3 text-center text-xs">
        <div className="rounded-md bg-zinc-900/50 p-1.5">
          <div className={cn("font-bold", monthPnl >= 0 ? "text-emerald-400" : "text-red-400")}>{fmtMoney(monthPnl)}</div>
          <div className="text-zinc-500">Monthly PnL</div>
        </div>
        <div className="rounded-md bg-zinc-900/50 p-1.5">
          <div className="font-bold">{monthTrades}</div>
          <div className="text-zinc-500">Trades</div>
        </div>
        <div className="rounded-md bg-zinc-900/50 p-1.5">
          <div className="font-bold">{monthTrades ? Math.round((monthWins / monthTrades) * 100) + "%" : "0%"}</div>
          <div className="text-zinc-500">Win Rate</div>
        </div>
      </div>

      <div className="grid grid-cols-7 gap-1 text-xs">
        {dayHeaders.map((d) => (
          <div key={d} className="text-center font-medium text-zinc-500 py-0.5">{d}</div>
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
                "flex flex-col items-center justify-center rounded-md border p-1 aspect-[5/4]",
                isToday ? "border-sky-500/50" : "border-transparent",
                info && pnl > 0 ? "bg-emerald-900/20" : info && pnl < 0 ? "bg-red-900/20" : "bg-zinc-900/10",
              )}
            >
              <span className={cn("font-medium", isToday ? "text-sky-400" : "text-zinc-400")}>{d}</span>
              {info ? (
                <>
                  <span className={cn("text-[10px] leading-none", pnl >= 0 ? "text-emerald-400" : "text-red-400")}>
                    {pnl >= 0 ? "+" : ""}${Math.abs(pnl).toFixed(0)}
                  </span>
                  <span className="text-[9px] text-zinc-600 leading-none">{info.tradeCount}t</span>
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