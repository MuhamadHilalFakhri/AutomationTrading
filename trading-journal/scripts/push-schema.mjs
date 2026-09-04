import { PGlite } from "@electric-sql/pglite";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const pglite = new PGlite(join(__dirname, "..", ".pglite"));

const schemaSQL = `
CREATE TABLE IF NOT EXISTS events (
  id SERIAL PRIMARY KEY,
  ts TEXT NOT NULL,
  kind TEXT NOT NULL,
  symbol TEXT,
  payload JSONB NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);
CREATE INDEX IF NOT EXISTS idx_events_kind ON events(kind);

CREATE TABLE IF NOT EXISTS trades (
  id SERIAL PRIMARY KEY,
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
  raw JSONB
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
`;

async function main() {
  console.log("Pushing schema to PGlite...");
  await pglite.exec(schemaSQL);
  console.log("Done. Schema created.");
  await pglite.close();
}

main().catch((e) => {
  console.error("Error:", e);
  process.exit(1);
});
