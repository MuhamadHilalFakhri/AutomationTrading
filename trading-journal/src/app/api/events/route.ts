import { NextResponse } from "next/server";
import { listEvents } from "@/lib/journal";

export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  const url = new URL(req.url);
  const limit = Number(url.searchParams.get("limit") ?? 200);
  const kind = url.searchParams.get("kind") ?? undefined;
  const sinceId = Number(url.searchParams.get("since_id") ?? 0);
  const rows = await listEvents({ limit, kind, sinceId });
  return NextResponse.json(rows.map((r) => ({
    id: r.id, ts: r.ts, kind: r.kind, symbol: r.symbol, payload: r.payload,
  })));
}
