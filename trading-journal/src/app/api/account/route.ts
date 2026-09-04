import { NextResponse } from "next/server";
import { db } from "@/lib/db";

export const dynamic = "force-dynamic";

export async function GET() {
  const snap = db.get<{
    ts: string;
    balance: number;
    equity: number;
    currency: string;
    server: string;
    payload: string;
  }>(
    "SELECT ts, balance, equity, currency, server, payload FROM account_snapshots ORDER BY id DESC LIMIT 1",
  );
  if (!snap) {
    return NextResponse.json({ ok: false, error: "no snapshot yet — run mt5_sync.py" }, { status: 404 });
  }
  return NextResponse.json({
    ok: true,
    ts: snap.ts,
    balance: snap.balance,
    equity: snap.equity,
    currency: snap.currency ?? "USD",
    server: snap.server,
  });
}
