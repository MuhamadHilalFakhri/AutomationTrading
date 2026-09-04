export type EventKind =
  | "scan" | "decision" | "executed" | "failed" | "risk_block"
  | "close" | "pnl" | "status" | "error";

export interface JournalEvent {
  id: number;
  ts: string;
  kind: EventKind | string;
  symbol: string | null;
  payload: Record<string, unknown>;
}

export interface Trade {
  id: number;
  ticket: number | null;
  symbol: string;
  side: string;
  lots: number | null;
  entry: number | null;
  sl: number | null;
  tp: number | null;
  openTs: string | null;
  closeTs: string | null;
  closePrice: number | null;
  profit: number | null;
  status: "open" | "closed" | "pending" | "rejected";
  strategy: string | null;
  confidence: number | null;
  reason: string | null;
  source?: string;
}

export interface DailyPnl {
  date: string;
  realized: number;
  tradeCount: number;
  wins: number;
  losses: number;
}

export interface Stats {
  totalClosed: number;
  winRate: number;
  realizedPnl: number;
  openPositions: number;
  pendingOrders: number;
}

export function fmtMoney(n: number | null | undefined): string {
  if (n == null || !Number.isFinite(n)) return "-";
  const abs = Math.abs(n);
  const sign = n < 0 ? "-" : "";
  if (abs >= 1000) return `${sign}$${(abs / 1000).toFixed(1)}k`;
  return `${sign}$${abs.toFixed(2)}`;
}

export function fmtNum(n: number | null | undefined, digits = 2): string {
  if (n == null || !Number.isFinite(n)) return "-";
  return n.toFixed(digits);
}

export function fmtTime(iso: string | null | undefined): string {
  if (!iso) return "-";
  try {
    return new Date(iso).toLocaleTimeString("id-ID", { hour12: false, timeZone: "Asia/Jakarta" });
  } catch {
    return iso.slice(11, 19);
  }
}

export function fmtDateTime(iso: string | null | undefined): string {
  if (!iso) return "-";
  try {
    return new Date(iso).toLocaleString("id-ID", { hour12: false, timeZone: "Asia/Jakarta" });
  } catch {
    return iso;
  }
}

export const KIND_LABEL: Record<string, string> = {
  scan: "Scan",
  decision: "Decision",
  executed: "Executed",
  failed: "Failed",
  risk_block: "Risk Block",
  close: "Close",
  pnl: "PnL",
  status: "Status",
  error: "Error",
};
