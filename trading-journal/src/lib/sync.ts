import { db } from "@/lib/db";
import { wibNow } from "@/lib/wib";

export interface Mt5Deal {
  ticket: number;          // deal ticket
  position_id: number;     // position ticket ( == bot trade ticket)
  order: number;
  symbol: string;
  type: number;            // 0 buy / 1 sell (deal direction)
  entry: number;           // 0 in / 1 out / 2 in-out / 3 out-by
  volume: number;
  price: number;
  profit: number;
  commission: number;
  swap: number;
  fee: number;
  time: number;            // epoch seconds UTC
  comment: string;
  magic: number;
}

export interface Mt5Position {
  ticket: number;
  symbol: string;
  type: number;            // 0 buy / 1 sell
  volume: number;
  price_open: number;
  sl: number;
  tp: number;
  profit: number;
  swap: number;
  time: number;            // epoch seconds UTC
  comment: string;
  magic: number;
}

export interface Mt5Account {
  login: number;
  server: string;
  currency: string;
  balance: number;
  equity: number;
  margin_free: number;
}

export interface SyncPayload {
  account?: Mt5Account;
  positions?: Mt5Position[];
  deals?: Mt5Deal[];
  days?: number;
}

export interface SyncResult {
  ok: boolean;
  processedDeals: number;
  newTrades: number;
  closedTrades: number;
  reopenedTrades: number;
  updatedOpen: number;
  skippedNonBotDeals: number;
  snapshot: boolean;
  errors: string[];
}

const SIDE_BY_MT5_TYPE: Record<number, string> = { 0: "BUY", 1: "SELL" };
const CLOSE_TS_TOLERANCE_MS = 1500;

function isoFromEpoch(sec: number): string {
  return new Date(sec * 1000).toISOString();
}

function str(v: unknown): string | null {
  return typeof v === "string" && v.length ? v : null;
}

function num(v: unknown): number | null {
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

// daily_pnl tidak lagi ditulis manual — getDailyPnl agregasi langsung dari trades.
// Penulis counter lama dihapus karena rentan drift (dobel-hitung antara jalur
// webhook & sync, plus koreksi profit pada partial-close multi deal).

export async function applySync(payload: SyncPayload): Promise<SyncResult> {
  const errors: string[] = [];
  const result: SyncResult = {
    ok: true, processedDeals: 0, newTrades: 0, closedTrades: 0,
    reopenedTrades: 0, updatedOpen: 0, skippedNonBotDeals: 0, snapshot: false,
    errors,
  };

  const account = payload.account;
  const positions = Array.isArray(payload.positions) ? payload.positions : [];
  const deals = Array.isArray(payload.deals) ? payload.deals : [];
  void num(payload.days); // window info only (client-side), not needed server-side

  // ---------- 1) account snapshot ----------
  if (account && Number.isFinite(account.balance)) {
    try {
      db.run(
        "INSERT INTO account_snapshots (ts, balance, equity, currency, server, payload) VALUES (?, ?, ?, ?, ?, ?)",
        wibNow() + "T" + new Date().toISOString().slice(11, 19) + "Z",
        account.balance,
        account.equity,
        str(account.currency) ?? "USD",
        str(account.server) ?? null,
        JSON.stringify(account),
      );
      result.snapshot = true;
    } catch (e) {
      errors.push("snapshot: " + String(e));
    }
  }

  // ---------- 2) reconcile open positions ----------
  const openByTicket = new Map<number, Mt5Position>();
  for (const p of positions) {
    if (typeof p.ticket === "number") openByTicket.set(p.ticket, p);
  }

  // ---------- 3) reconcile deals ----------
  // deals = actual fills; entry=1 (out) = close legs, entry=0 (in) = open legs
  const closesByPosition = new Map<number, Mt5Deal[]>();
  const opensByPosition = new Map<number, Mt5Deal[]>();
  for (const d of deals) {
    if (typeof d?.ticket !== "number" || typeof d?.position_id !== "number") continue;
    if (d.entry === 1 || d.entry === 2 || d.entry === DEAL_OUT_BY) {
      (closesByPosition.get(d.position_id) ?? closesByPosition.set(d.position_id, []).get(d.position_id)!).push(d);
    } else if (d.entry === 0) {
      (opensByPosition.get(d.position_id) ?? opensByPosition.set(d.position_id, []).get(d.position_id)!).push(d);
    }
  }

  for (const [posId, closeDeals] of closesByPosition) {
    result.processedDeals += closeDeals.length;
    for (const d of closeDeals.sort((a, b) => a.time - b.time)) {
      const existing = db.get<{ id: number; status: string; profit: number | null; close_ts: string | null; source: string; open_ts: string | null }>(
        "SELECT id, status, profit, close_ts, source, open_ts FROM trades WHERE ticket = ?",
        posId,
      );

      if (!existing) {
        // ---- trade closed but never journaled (manual trade / missed event) ----
        const open = (opensByPosition.get(posId) ?? []).sort((a, b) => a.time - b.time)[0];
        const openTs = open ? isoFromEpoch(open.time) : null;
        const side = open ? (SIDE_BY_MT5_TYPE[open.type] ?? "BUY") : (SIDE_BY_MT5_TYPE[d.type] ?? "BUY");
        const profit = (d.profit ?? 0) + (d.commission ?? 0) + (d.swap ?? 0) + (d.fee ?? 0);
        db.run(
          `INSERT INTO trades (ticket, symbol, side, lots, entry, sl, tp, open_ts, close_ts, close_price, profit, status, strategy, confidence, reason, raw, source, balance)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'closed', ?, ?, ?, ?, 'mt5', ?)
           ON CONFLICT(ticket) DO NOTHING`,
          posId,
          d.symbol ?? "",
          side,
          d.volume,
          open ? open.price : d.price,
          null, null,
          openTs,
          isoFromEpoch(d.time),
          d.price,
          Math.round(profit * 100) / 100,
          "MT5 History",
          null,
          "Synced dari MT5 history (deal " + d.ticket + ")",
          JSON.stringify({ deals: { in: open ?? null, out: d } }),
        );
        result.newTrades++;
        continue;
      }

      // ---- existing row ----
      if (existing.status === "open" || existing.status === "pending") {
        // bot-tracked trade got closed while journal thought open — reconcile
        const profit = (d.profit ?? 0) + (d.commission ?? 0) + (d.swap ?? 0) + (d.fee ?? 0);
        const rounded = Math.round(profit * 100) / 100;
        const closeTs = isoFromEpoch(d.time);

        // if journal already recorded a close (close event) at ~same time, treat as duplicate-ish: verify profit
        if (existing.close_ts) {
          const recorded = new Date(existing.close_ts).getTime();
          if (Math.abs(recorded - new Date(closeTs).getTime()) <= CLOSE_TS_TOLERANCE_MS) {
            // update to authoritative MT5 numbers
            db.run(
              "UPDATE trades SET close_price = ?, profit = ?, status = 'closed', source = ? WHERE id = ?",
              d.price, rounded, existing.source === "bot" ? "bot+mt5" : existing.source, existing.id,
            );
            result.closedTrades++;
            continue;
          }
        }
        // journal thought open — subtract nothing from daily (it was never added)
        db.run(
          "UPDATE trades SET status = 'closed', close_ts = ?, close_price = ?, profit = ?, source = ? WHERE id = ?",
          closeTs, d.price, rounded, existing.source === "bot" ? "bot+mt5" : existing.source, existing.id,
        );
        result.closedTrades++;
      } else if (existing.status === "closed") {
        // both closed — verify profit matches; if differs beyond tolerance, correct daily_pnl
        const mt5Profit = Math.round(((d.profit ?? 0) + (d.commission ?? 0) + (d.swap ?? 0) + (d.fee ?? 0)) * 100) / 100;
        const recorded = num(existing.profit) ?? 0;
        if (Math.abs(mt5Profit - recorded) > 0.01) {
          db.run("UPDATE trades SET profit = ?, source = 'bot+mt5' WHERE id = ?", mt5Profit, existing.id);
          result.closedTrades++;
        } else {
          result.closedTrades++; // verified, no change
          db.run("UPDATE trades SET source = CASE WHEN source = 'bot' THEN 'bot+mt5' ELSE source END WHERE id = ?", existing.id);
        }
      } else if (existing.status === "rejected") {
        // bot pushed rejected but MT5 shows the order actually filled & closed — reopen as closed
        const profit = Math.round(((d.profit ?? 0) + (d.commission ?? 0) + (d.swap ?? 0) + (d.fee ?? 0)) * 100) / 100;
        const closeTs = isoFromEpoch(d.time);
        db.run(
          "UPDATE trades SET status = 'closed', close_ts = ?, close_price = ?, profit = ?, source = 'mt5' WHERE id = ?",
          closeTs, d.price, profit, existing.id,
        );
        result.reopenedTrades++;
      }
    }
  }

  // ---------- 4) refresh open positions ----------
  for (const [ticket, p] of openByTicket) {
    const existing = db.get<{ id: number; status: string; entry: number | null; sl: number | null; tp: number | null; source: string }>(
      "SELECT id, status, entry, sl, tp, source FROM trades WHERE ticket = ?",
      ticket,
    );
    if (!existing) {
      db.run(
        `INSERT INTO trades (ticket, symbol, side, lots, entry, sl, tp, open_ts, status, strategy, confidence, reason, raw, source)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'open', ?, ?, ?, ?, 'mt5')`,
        ticket,
        p.symbol ?? "",
        SIDE_BY_MT5_TYPE[p.type] ?? "BUY",
        p.volume,
        p.price_open,
        p.sl || null,
        p.tp || null,
        isoFromEpoch(p.time),
        "MT5 Live",
        null,
        "Synced dari MT5 positions (live)",
        JSON.stringify(p),
      );
      result.newTrades++;
    } else {
      db.run(
        "UPDATE trades SET lots = ?, entry = ?, sl = ?, tp = ?, status = CASE WHEN status = 'pending' THEN 'open' ELSE status END, source = CASE WHEN source = 'bot' THEN 'bot+mt5' ELSE source END WHERE id = ?",
        p.volume, p.price_open, p.sl || null, p.tp || null, existing.id,
      );
      result.updatedOpen++;
    }
  }

  // ---------- 5) mark stale 'open' rows as closed_missing (closed on MT5 but no close deal in window) ----------
  // deliberately NOT auto-closing: if deal window misses the close leg, a manual review is safer.
  // rows stay 'open' until the deal appears in a wider window or bot pushes close.

  return result;
}

const DEAL_OUT_BY = 3; // DEAL_ENTRY_OUT_BY
