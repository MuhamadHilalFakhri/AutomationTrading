import { spawn } from "child_process";
import { getSyncPaths } from "@/lib/config";

export interface RunResult {
  ok: boolean;
  processedDeals?: number;
  newTrades?: number;
  closedTrades?: number;
  error?: string;
  raw?: string;
}

export function runMt5Sync(days: number, timeoutMs = 60000): Promise<RunResult> {
  const { mt5SyncScript, python, journalUrl, terminalPath } = getSyncPaths();
  return new Promise((resolve) => {
    const child = spawn(python, [mt5SyncScript, "--days", String(days)], {
      cwd: process.cwd(),
      windowsHide: true,
      env: { ...process.env, TJ_URL: journalUrl, MT5_TERMINAL_PATH: terminalPath },
    });
    let out = "";
    child.stdout.on("data", (d) => (out += String(d)));
    child.stderr.on("data", (d) => (out += String(d)));
    const t = setTimeout(() => {
      child.kill();
      resolve({ ok: false, error: "timeout", raw: out.slice(-800) });
    }, timeoutMs);
    child.on("error", (e) => {
      clearTimeout(t);
      resolve({ ok: false, error: String(e), raw: out.slice(-800) });
    });
    child.on("close", (code) => {
      clearTimeout(t);
      if (code === 0) {
        const m = out.match(/ok — deals:(\d+) new:(\d+) closed:(\d+)/);
        resolve({
          ok: true,
          processedDeals: m ? Number(m[1]) : undefined,
          newTrades: m ? Number(m[2]) : undefined,
          closedTrades: m ? Number(m[3]) : undefined,
          raw: out.slice(-800),
        });
      } else {
        resolve({ ok: false, error: `exit ${code}`, raw: out.slice(-800) });
      }
    });
  });
}
