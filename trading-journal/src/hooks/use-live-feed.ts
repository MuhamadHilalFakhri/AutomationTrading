"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import type { JournalEvent, Stats } from "@/lib/types";

interface LiveState {
  events: JournalEvent[];
  connected: boolean;
  lastEvent: JournalEvent | null;
}

export function useLiveFeed() {
  const [state, setState] = useState<LiveState>({
    events: [],
    connected: false,
    lastEvent: null,
  });
  const esRef = useRef<EventSource | null>(null);

  const connect = useCallback(() => {
    if (esRef.current) esRef.current.close();
    const es = new EventSource("/api/stream");
    esRef.current = es;

    es.onopen = () => setState((s) => ({ ...s, connected: true }));
    es.onerror = () => setState((s) => ({ ...s, connected: false }));
    es.onmessage = (msg) => {
      try {
        const ev = JSON.parse(msg.data) as JournalEvent;
        setState((s) => {
          // dedupe by id (catch-up may resend)
          if (s.events.some((e) => e.id === ev.id)) return s;
          const events = [ev, ...s.events].slice(0, 500);
          return { events, connected: true, lastEvent: ev };
        });
      } catch {
        // ignore malformed
      }
    };
  }, []);

  useEffect(() => {
    connect();
    return () => esRef.current?.close();
  }, [connect]);

  return state;
}

export function useStats(refreshMs = 15000) {
  const [stats, setStats] = useState<Stats | null>(null);
  const load = useCallback(async () => {
    try {
      const r = await fetch("/api/stats", { cache: "no-store" });
      if (r.ok) setStats(await r.json());
    } catch { /* ignore */ }
  }, []);
  useEffect(() => {
    let active = true;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- async fetch, setState happens after await
    load();
    const t = setInterval(() => { if (active) load(); }, refreshMs);
    return () => { active = false; clearInterval(t); };
  }, [load, refreshMs]);
  return { stats, reload: load };
}
