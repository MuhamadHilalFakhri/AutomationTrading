import { NextResponse } from "next/server";
import { getDailyPnl } from "@/lib/journal";
import { wibNow, wibDate } from "@/lib/wib";

export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  const url = new URL(req.url);
  const today = wibNow();
  const end = url.searchParams.get("end") ?? today;
  const range = url.searchParams.get("range");
  const start = range
    ? wibDate(new Date(Date.now() - Number(range) * 86400_000))
    : url.searchParams.get("start") ??
      wibDate(new Date(Date.now() - 45 * 86400_000));
  const days = await getDailyPnl(start, end);
  return NextResponse.json({ start, end, days });
}
