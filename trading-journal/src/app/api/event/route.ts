import { NextResponse } from "next/server";
import { insertEvent } from "@/lib/journal";

export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const kind = typeof body.kind === "string" ? body.kind : "unknown";
    const symbol = typeof body.symbol === "string" ? body.symbol : null;
    const payload = (body.payload && typeof body.payload === "object") ? body.payload : {};
    const row = await insertEvent({ kind, symbol, payload });
    return NextResponse.json({ ok: true, id: row?.id, ts: row?.ts });
  } catch (e) {
    console.error("[journal] POST /api/event error:", e);
    return NextResponse.json({ ok: false, error: String(e) }, { status: 500 });
  }
}
