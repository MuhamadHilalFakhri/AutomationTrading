import { NextResponse } from "next/server";
import { runMt5Sync } from "@/lib/sync-runner";

export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  let days = 90;
  try {
    const body = (await req.json()) as { days?: number };
    if (body.days) days = Math.min(Math.max(Number(body.days), 1), 3650);
  } catch {
    // no body -> default
  }

  const result = await runMt5Sync(days);
  if (result.ok) {
    return NextResponse.json({
      ok: true,
      processedDeals: result.processedDeals,
      newTrades: result.newTrades,
      closedTrades: result.closedTrades,
    });
  }
  return NextResponse.json(
    { ok: false, error: result.error, detail: result.raw },
    { status: 502 },
  );
}
