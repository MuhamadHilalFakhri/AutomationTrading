import { NextResponse } from "next/server";
import { listTrades } from "@/lib/journal";

export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  const url = new URL(req.url);
  const status = url.searchParams.get("status") ?? undefined;
  const limit = Number(url.searchParams.get("limit") ?? 500);
  const rows = await listTrades({ status, limit });
  return NextResponse.json(rows.map((r) => ({
    id: r.id, ticket: r.ticket, symbol: r.symbol, side: r.side, lots: r.lots,
    entry: r.entry, sl: r.sl, tp: r.tp, openTs: r.openTs, closeTs: r.closeTs,
    closePrice: r.closePrice, profit: r.profit, status: r.status,
    strategy: r.strategy, confidence: r.confidence, reason: r.reason,
    source: r.source ?? "bot",
  })));
}
