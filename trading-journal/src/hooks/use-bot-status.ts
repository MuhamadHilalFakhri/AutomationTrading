"use client";

import { useCallback, useEffect, useState } from "react";

export interface BotStatus {
  online: boolean;
  lastEventTs: string | null;
  ageSec: number | null;
  thresholdSec: number;
}

/** Poll status bot (umur event terakhir) tiap pollMs. */
export function useBotStatus(pollMs = 15000) {
  const [status, setStatus] = useState<BotStatus | null>(null);
  const load = useCallback(async () => {
    try {
      const r = await fetch("/api/bot-status", { cache: "no-store" });
      if (r.ok) setStatus(await r.json());
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    let active = true;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- async fetch, setState happens after await
    load();
    const t = setInterval(() => {
      if (active) load();
    }, pollMs);
    return () => {
      active = false;
      clearInterval(t);
    };
  }, [load, pollMs]);

  return status;
}

export function fmtAge(sec: number | null): string {
  if (sec == null) return "belum ada event";
  if (sec < 60) return `${sec} detik lalu`;
  if (sec < 3600) return `${Math.floor(sec / 60)} menit lalu`;
  return `${Math.floor(sec / 3600)} jam ${Math.floor((sec % 3600) / 60)} menit lalu`;
}
