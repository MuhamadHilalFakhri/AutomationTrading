import { NextResponse } from "next/server";
import { db } from "@/lib/db";

export const dynamic = "force-dynamic";

/** Bot scan tiap ~60s (selalu produce event scan). Dianggap offline jika tidak ada event > 3 menit. */
const OFFLINE_AFTER_SEC = 180;

export async function GET() {
  const row = db.get<{ last_ts: string | null }>(
    "SELECT MAX(ts) AS last_ts FROM events",
  );
  const lastTs = row?.last_ts ?? null;
  const ageSec = lastTs
    ? Math.round((Date.now() - new Date(lastTs).getTime()) / 1000)
    : null;
  const online = ageSec != null && ageSec >= 0 && ageSec <= OFFLINE_AFTER_SEC;

  return NextResponse.json({
    online,
    lastEventTs: lastTs,
    ageSec,
    thresholdSec: OFFLINE_AFTER_SEC,
  });
}
