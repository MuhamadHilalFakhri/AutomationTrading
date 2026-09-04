import {
  pgTable,
  serial,
  text,
  real,
  integer,
  jsonb,
  index,
} from "drizzle-orm/pg-core";

// Raw event log from bot (append-only)
export const events = pgTable("events", {
  id: serial("id").primaryKey(),
  ts: text("ts").notNull(), // ISO UTC
  kind: text("kind", { enum: ["scan", "decision", "executed", "failed", "risk_block", "close", "pnl", "status", "error"] }).notNull(),
  symbol: text("symbol"),
  payload: jsonb("payload").notNull().$type<Record<string, unknown>>(),
}, (table) => [
  index("idx_events_ts").on(table.ts),
  index("idx_events_kind").on(table.kind),
]);

// Trade book (positions + closed trades)
export const trades = pgTable("trades", {
  id: serial("id").primaryKey(),
  ticket: integer("ticket").unique(), // MT5 ticket
  symbol: text("symbol").notNull(),
  side: text("side").notNull(), // BUY|SELL|BUY_LIMIT|SELL_LIMIT|BUY_STOP|SELL_STOP
  lots: real("lots"),
  entry: real("entry"),
  sl: real("sl"),
  tp: real("tp"),
  openTs: text("open_ts"),
  closeTs: text("close_ts"),
  closePrice: real("close_price"),
  profit: real("profit"),
  status: text("status", { enum: ["pending", "open", "closed", "rejected"] }).notNull().default("pending"),
  strategy: text("strategy"),
  confidence: real("confidence"),
  reason: text("reason"),
  raw: jsonb("raw").$type<Record<string, unknown>>(),
}, (table) => [
  index("idx_trades_status").on(table.status),
  index("idx_trades_open_ts").on(table.openTs),
]);

// Daily PnL aggregate (for calendar)
export const dailyPnl = pgTable("daily_pnl", {
  date: text("date").primaryKey(), // YYYY-MM-DD (UTC)
  realized: real("realized").notNull().default(0),
  tradeCount: integer("trade_count").notNull().default(0),
  wins: integer("wins").notNull().default(0),
  losses: integer("losses").notNull().default(0),
});

// Type exports
export type Event = typeof events.$inferSelect;
export type NewEvent = typeof events.$inferInsert;
export type Trade = typeof trades.$inferSelect;
export type NewTrade = typeof trades.$inferInsert;
export type DailyPnl = typeof dailyPnl.$inferSelect;
