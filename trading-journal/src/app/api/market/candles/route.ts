import { NextResponse } from "next/server";
import { getMt5Rates, MT5_TIMEFRAMES, type Mt5Timeframe } from "@/lib/mt5-rates";

export const dynamic = "force-dynamic";

const SYMBOL_PATTERN = /^[A-Za-z0-9._-]{1,32}$/;

export async function GET(request: Request) {
  const params = new URL(request.url).searchParams;
  const symbol = (params.get("symbol") ?? "XAUUSD").trim().toUpperCase();
  const requestedTimeframe = params.get("timeframe") ?? "15";
  const requestedCount = Number(params.get("count") ?? 1000);

  if (!SYMBOL_PATTERN.test(symbol)) {
    return NextResponse.json({ ok: false, error: "Symbol tidak valid" }, { status: 400 });
  }
  if (!MT5_TIMEFRAMES.includes(requestedTimeframe as Mt5Timeframe)) {
    return NextResponse.json({ ok: false, error: "Timeframe tidak didukung" }, { status: 400 });
  }

  const count = Number.isFinite(requestedCount)
    ? Math.min(Math.max(Math.trunc(requestedCount), 100), 3000)
    : 1000;
  const result = await getMt5Rates(symbol, requestedTimeframe as Mt5Timeframe, count);

  return NextResponse.json(result, {
    status: result.ok ? 200 : 502,
    headers: { "Cache-Control": "no-store" },
  });
}
