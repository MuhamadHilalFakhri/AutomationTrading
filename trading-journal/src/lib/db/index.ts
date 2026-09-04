import { DatabaseSync } from "node:sqlite";
import { join } from "path";
import { cwd } from "process";
import { mkdirSync } from "fs";

declare global {
  var __sqliteDb: DatabaseSync | undefined;
}

function getDb(): DatabaseSync {
  if (!globalThis.__sqliteDb) {
    const dataDir = join(cwd(), "data");
    mkdirSync(dataDir, { recursive: true });
    const dbPath = join(dataDir, "journal.db");
    globalThis.__sqliteDb = new DatabaseSync(dbPath);
    // init schema
    globalThis.__sqliteDb.exec(`
      CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT NOT NULL,
        kind TEXT NOT NULL,
        symbol TEXT,
        payload TEXT NOT NULL
      );
      CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);
      CREATE INDEX IF NOT EXISTS idx_events_kind ON events(kind);

      CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket INTEGER UNIQUE,
        symbol TEXT NOT NULL,
        side TEXT NOT NULL,
        lots REAL,
        entry REAL,
        sl REAL,
        tp REAL,
        open_ts TEXT,
        close_ts TEXT,
        close_price REAL,
        profit REAL,
        status TEXT NOT NULL DEFAULT 'pending',
        strategy TEXT,
        confidence REAL,
        reason TEXT,
        raw TEXT
      );
      CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status);
      CREATE INDEX IF NOT EXISTS idx_trades_open_ts ON trades(open_ts);

      CREATE TABLE IF NOT EXISTS daily_pnl (
        date TEXT PRIMARY KEY,
        realized REAL NOT NULL DEFAULT 0,
        trade_count INTEGER NOT NULL DEFAULT 0,
        wins INTEGER NOT NULL DEFAULT 0,
        losses INTEGER NOT NULL DEFAULT 0
      );

      CREATE TABLE IF NOT EXISTS account_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT NOT NULL,
        balance REAL NOT NULL,
        equity REAL NOT NULL,
        currency TEXT,
        server TEXT,
        payload TEXT
      );
      CREATE INDEX IF NOT EXISTS idx_snap_ts ON account_snapshots(ts);

      CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
      );
    `);

    // ---- migrations for existing DBs ----
    const cols = (globalThis.__sqliteDb
      .prepare("PRAGMA table_info(trades)")
      .all() as Array<{ name: string }>)
      .map((c) => c.name);
    if (!cols.includes("source")) {
      globalThis.__sqliteDb.exec("ALTER TABLE trades ADD COLUMN source TEXT NOT NULL DEFAULT 'bot'");
    }
    if (!cols.includes("balance")) {
      globalThis.__sqliteDb.exec("ALTER TABLE trades ADD COLUMN balance REAL");
    }
  }
  return globalThis.__sqliteDb;
}

type SqlValue = string | number | bigint | Buffer | null;

export const db = {
  run(sql: string, ...params: SqlValue[]) {
    return getDb().prepare(sql).run(...params);
  },
  get<T = Record<string, unknown>>(sql: string, ...params: SqlValue[]): T | undefined {
    return getDb().prepare(sql).get(...params) as T | undefined;
  },
  all<T = Record<string, unknown>>(sql: string, ...params: SqlValue[]): T[] {
    return getDb().prepare(sql).all(...params) as T[];
  },
};

export type DbType = typeof db;
