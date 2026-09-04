import { NextResponse } from "next/server";
import { existsSync } from "fs";
import { getSyncPaths } from "@/lib/config";
import { getAutoSyncState, startAutoSync, stopAutoSync } from "@/lib/auto-sync";
import { setSetting } from "@/lib/settings";

export const dynamic = "force-dynamic";

export async function GET() {
  const paths = getSyncPaths();
  const state = getAutoSyncState();
  return NextResponse.json({
    paths: {
      mt5SyncScript: { path: paths.mt5SyncScript, exists: existsSync(paths.mt5SyncScript) },
      python: { path: paths.python, exists: existsSync(paths.python) },
      journalUrl: { path: paths.journalUrl, exists: null },
      terminalPath: { path: paths.terminalPath, exists: existsSync(paths.terminalPath) },
    },
    autoSync: {
      enabled: state.enabled,
      interval: state.interval,
      running: state.running,
      lastRun: state.lastRun,
      lastResult: state.lastResult,
    },
  });
}

export async function POST(req: Request) {
  try {
    const body = (await req.json()) as { enabled?: boolean; interval?: number };
    if (typeof body.enabled !== "boolean") {
      return NextResponse.json({ ok: false, error: "enabled (boolean) required" }, { status: 400 });
    }

    let interval = Number(body.interval ?? 60);
    if (!Number.isFinite(interval) || interval < 15) interval = 15;
    if (interval > 3600) interval = 3600;
    interval = Math.round(interval);

    setSetting("auto_sync_seconds", body.enabled ? String(interval) : "0");

    if (body.enabled) {
      const started = startAutoSync(interval);
      if (!started) {
        return NextResponse.json({ ok: false, error: "gagal start auto-sync" }, { status: 500 });
      }
    } else {
      stopAutoSync();
    }

    return NextResponse.json({ ok: true, autoSync: getAutoSyncState() });
  } catch (e) {
    return NextResponse.json({ ok: false, error: String(e) }, { status: 500 });
  }
}
