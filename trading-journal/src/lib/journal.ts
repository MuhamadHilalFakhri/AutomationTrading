import { db } from "@/lib/db";

export const EVENT_KINDS = [
  "scan", "decision", "executed", "failed", "risk_block", "close", "pnl", "status", "error",
] as const;
export type EventKind = (typeof EVENT_KINDS)[number];

function nowIso() {
  return new Date().toISOString();
}

function num(v: unknown): number | null {
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function str(v: unknown): string | null {
  return typeof v === "string" ? v.slice(0, 500) : null;
}

export interface EventRow {
  id: number;
  ts: string;
  kind: string;
  symbol: string | null;
  payload: Record<string, unknown>;
}

export async function insertEvent(input: {
  kind: string;
  symbol?: string | null;
  payload: Record<string, unknown>;
}) {
  const ts = nowIso();
  const res = db.run(
    "INSERT INTO events (ts, kind, symbol, payload) VALUES (?, ?, ?, ?)",
    ts, input.kind, input.symbol ?? null, JSON.stringify(input.payload),
  );
  const id = Number(res.lastInsertRowid);

  try {
    await applyBookkeeping(input.kind, input.payload);
  } catch (e) {
    console.error("[journal] bookkeeping error:", e);
  }

  return { id, ts };
}

async function applyBookkeeping(kind: string, payload: Record<string, unknown>) {
  if (kind === "executed") {
    const ticket = typeof payload.ticket === "number" ? payload.ticket : null;
    if (!ticket) return;
    const dec = (payload.decision ?? {}) as Record<string, unknown>;
    const orderType = String(payload.order_type ?? dec.decision ?? "");
    const isPending = orderType.endsWith("_LIMIT") || orderType.endsWith("_STOP");
    db.run(
      `INSERT INTO trades (ticket, symbol, side, lots, entry, sl, tp, open_ts, status, strategy, confidence, reason, raw)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
       ON CONFLICT(ticket) DO NOTHING`,
      ticket,
      String(payload.symbol ?? ""),
      orderType,
      num(payload.lots),
      num(payload.entry),
      num(payload.sl),
      num(payload.tp),
      nowIso(),
      isPending ? "pending" : "open",
      str(dec.strategy),
      num(dec.confidence),
      str(dec.reason),
      JSON.stringify(payload),
    );
  } else if (kind === "close") {
    const results = Array.isArray(payload.results) ? payload.results : [];
    for (const r of results) {
      const row = r as Record<string, unknown>;
      if (row.ok && typeof row.ticket === "number") {
        await closeTrade(row.ticket, num(row.price), num(row.profit));
      }
    }
  } else if (kind === "trade_closed") {
    const ticket = typeof payload.ticket === "number" ? payload.ticket : null;
    if (ticket) await closeTrade(ticket, num(payload.close_price), num(payload.profit));
  }
}

export async function closeTrade(ticket: number, closePrice: number | null, profit: number | null) {
  const row = db.get<{ id: number }>(
    "SELECT id FROM trades WHERE ticket = ? AND status IN ('open','pending') LIMIT 1",
    ticket,
  );
  if (!row) return false;

  const closeTs = nowIso();
  db.run(
    "UPDATE trades SET status = 'closed', close_price = ?, profit = ?, close_ts = ? WHERE id = ?",
    closePrice, profit, closeTs, row.id,
  );

  return true;
}

export async function listEvents(opts: { limit?: number; kind?: string; sinceId?: number } = {}) {
  const { limit = 200, kind, sinceId = 0 } = opts;
  let sql = "SELECT id, ts, kind, symbol, payload FROM events WHERE id > ?";
  const params: (string | number)[] = [sinceId];
  if (kind) {
    sql += " AND kind = ?";
    params.push(kind);
  }
  sql += " ORDER BY id DESC LIMIT ?";
  params.push(limit);
  return db.all(sql, ...params).map((r) => ({
    ...r,
    payload: JSON.parse(String(r.payload)),
  })) as unknown as EventRow[];
}

export async function listTrades(opts: { status?: string; limit?: number } = {}) {
  const { status, limit = 500 } = opts;
  let sql = "SELECT id, ticket, symbol, side, lots, entry, sl, tp, open_ts, close_ts, close_price, profit, status, strategy, confidence, reason, source FROM trades";
  const params: (string | number)[] = [];
  if (status) {
    sql += " WHERE status = ?";
    params.push(status);
  }
  sql += " ORDER BY id DESC LIMIT ?";
  params.push(limit);
  return db.all(sql, ...params).map((r) => ({
    id: r.id,
    ticket: r.ticket,
    symbol: r.symbol,
    side: r.side,
    lots: r.lots,
    entry: r.entry,
    sl: r.sl,
    tp: r.tp,
    openTs: r.open_ts,
    closeTs: r.close_ts,
    closePrice: r.close_price,
    profit: r.profit,
    status: r.status,
    strategy: r.strategy,
    confidence: r.confidence,
    source: r.source ?? "bot",
    reason: r.reason,
  }));
}

export async function getDailyPnl(start: string, end: string) {
  // Agregasi langsung dari trades (source of truth) — tabel counter daily_pnl
  // rentan drift karena dobel-hitung antara jalur webhook & sync.
  return db.all(
    `SELECT date(close_ts, '+7 hours') AS date,
            SUM(profit) AS realized,
            COUNT(*) AS tradeCount,
            SUM(CASE WHEN profit >= 0 THEN 1 ELSE 0 END) AS wins,
            SUM(CASE WHEN profit < 0 THEN 1 ELSE 0 END) AS losses
     FROM trades
     WHERE status = 'closed' AND close_ts IS NOT NULL
       AND date(close_ts, '+7 hours') >= ?
       AND date(close_ts, '+7 hours') <= ?
     GROUP BY date(close_ts, '+7 hours')
     ORDER BY date`,
    start, end,
  );
}

export async function getStats() {
  const closed = db.get<{ total: number; wins: number; realized: number | null }>(
    "SELECT COUNT(*) AS total, SUM(CASE WHEN profit >= 0 THEN 1 ELSE 0 END) AS wins, SUM(profit) AS realized FROM trades WHERE status = 'closed'",
  );
  const openN = db.get<{ n: number }>("SELECT COUNT(*) AS n FROM trades WHERE status = 'open'");
  const pendN = db.get<{ n: number }>("SELECT COUNT(*) AS n FROM trades WHERE status = 'pending'");
  return {
    totalClosed: closed?.total ?? 0,
    winRate: closed?.total ? Math.round(((closed.wins ?? 0) / closed.total) * 1000) / 10 : 0,
    realizedPnl: Math.round((closed?.realized ?? 0) * 100) / 100,
    openPositions: openN?.n ?? 0,
    pendingOrders: pendN?.n ?? 0,
  };
}
