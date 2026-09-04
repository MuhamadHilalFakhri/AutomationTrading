import { NextResponse } from "next/server";
import { applySync, type SyncPayload } from "@/lib/sync";

export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  let body: SyncPayload;
  try {
    body = (await req.json()) as SyncPayload;
  } catch {
    return NextResponse.json({ ok: false, error: "invalid json" }, { status: 400 });
  }

  try {
    const result = await applySync(body);
    return NextResponse.json(result);
  } catch (e) {
    return NextResponse.json(
      { ok: false, error: String(e) },
      { status: 500 },
    );
  }
}
