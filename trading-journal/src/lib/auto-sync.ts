import { runMt5Sync } from "@/lib/sync-runner";
import { getSyncPaths } from "@/lib/config";
import { getSetting } from "@/lib/settings";

declare global {
  var __tjAutoSync: {
    timer: ReturnType<typeof setInterval> | null;
    running: boolean;
    lastRun: string | null;
    lastResult: string | null;
  } | undefined;
}

function state() {
  if (!globalThis.__tjAutoSync) {
    globalThis.__tjAutoSync = { timer: null, running: false, lastRun: null, lastResult: null };
  }
  return globalThis.__tjAutoSync;
}

/** Interval efektif: DB setting > env AUTO_SYNC_SECONDS > 0 (mati) */
export function effectiveInterval(): number {
  const fromDb = getSetting("auto_sync_seconds", "");
  if (fromDb !== "") return Number(fromDb) || 0;
  return getSyncPaths().autoSyncSeconds;
}

export function getAutoSyncState() {
  const s = state();
  const interval = effectiveInterval();
  return {
    enabled: s.timer != null,
    interval,
    running: s.running,
    lastRun: s.lastRun,
    lastResult: s.lastResult,
  };
}

function tick() {
  const s = state();
  if (s.running) return;
  s.running = true;
  runMt5Sync(90)
    .then((r) => {
      s.lastRun = new Date().toISOString();
      s.lastResult = r.ok
        ? `ok — deals:${r.processedDeals ?? 0} new:${r.newTrades ?? 0} closed:${r.closedTrades ?? 0}`
        : `error: ${r.error ?? "unknown"}`;
    })
    .catch((e) => {
      s.lastRun = new Date().toISOString();
      s.lastResult = "error: " + String(e);
    })
    .finally(() => {
      s.running = false;
    });
}

export function startAutoSync(seconds?: number): boolean {
  const s = state();
  stopAutoSync();
  const interval = seconds ?? effectiveInterval();
  if (!interval || interval < 15) return false;
  s.timer = setInterval(tick, interval * 1000);
  void tick(); // jalankan sekali langsung
  return true;
}

export function stopAutoSync() {
  const s = state();
  if (s.timer) {
    clearInterval(s.timer);
    s.timer = null;
  }
}

/** Dipanggil saat server start (instrumentation.ts) */
export function initAutoSync() {
  const interval = effectiveInterval();
  if (interval >= 15) startAutoSync(interval);
}
