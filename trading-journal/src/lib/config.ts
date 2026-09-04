import { join } from "path";
import { cwd } from "process";
import { readFileSync, existsSync } from "fs";

// Load .env manual (ringan, tanpa dependency tambahan)
function loadEnv(): Record<string, string> {
  const env: Record<string, string> = {};
  const envPath = join(cwd(), ".env");
  if (existsSync(envPath)) {
    const lines = readFileSync(envPath, "utf8").split(/\r?\n/);
    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith("#")) continue;
      const idx = trimmed.indexOf("=");
      if (idx <= 0) continue;
      const key = trimmed.slice(0, idx).trim();
      let val = trimmed.slice(idx + 1).trim();
      if ((val.startsWith('"') && val.endsWith('"')) || (val.startsWith("'") && val.endsWith("'"))) {
        val = val.slice(1, -1);
      }
      env[key] = val;
    }
  }
  return env;
}

const fileEnv = loadEnv();

function get(key: string, fallback: string): string {
  return process.env[key] ?? fileEnv[key] ?? fallback;
}

export interface SyncPaths {
  /** Path ke script mt5_sync.py di folder bot */
  mt5SyncScript: string;
  /** Path Python yang punya package MetaTrader5 */
  python: string;
  /** URL journal (tempat mt5_sync.py kirim data) */
  journalUrl: string;
  /** Path executable terminal MT5 */
  terminalPath: string;
  /** Interval loop auto-sync (detik), 0 = mati */
  autoSyncSeconds: number;
}

export function getSyncPaths(): SyncPaths {
  return {
    mt5SyncScript: get("MT5_SYNC_SCRIPT", "D:/Projects/AutomationTrading/mt5-ai-trading-bot/mt5_sync.py"),
    python: get("MT5_SYNC_PYTHON", "D:/HermesAgent/hermes-agent/venv/Scripts/python.exe"),
    journalUrl: get("TJ_URL", "http://127.0.0.1:8500"),
    terminalPath: get("MT5_TERMINAL_PATH", "C:/Program Files/MetaTrader 5/terminal64.exe"),
    autoSyncSeconds: Number(get("AUTO_SYNC_SECONDS", "0")),
  };
}
