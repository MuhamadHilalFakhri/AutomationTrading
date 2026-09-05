import "server-only";

import { spawn } from "child_process";
import { join } from "path";
import { getSyncPaths } from "@/lib/config";

export const MT5_TIMEFRAMES = ["1", "5", "15", "60", "240", "D", "W"] as const;
export type Mt5Timeframe = (typeof MT5_TIMEFRAMES)[number];

export interface Mt5Candle {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  tickVolume: number;
}

export type Mt5RatesResult =
  | {
      ok: true;
      symbol: string;
      timeframe: Mt5Timeframe;
      digits: number;
      candles: Mt5Candle[];
    }
  | { ok: false; error: string };

export function getMt5Rates(
  symbol: string,
  timeframe: Mt5Timeframe,
  count: number,
  timeoutMs = 20000,
): Promise<Mt5RatesResult> {
  const { python, terminalPath } = getSyncPaths();
  const script = join(process.cwd(), "scripts", "mt5_rates.py");

  return new Promise((resolve) => {
    let settled = false;
    let stdout = "";
    let stderr = "";

    const finish = (result: Mt5RatesResult) => {
      if (settled) return;
      settled = true;
      resolve(result);
    };

    const child = spawn(
      python,
      [script, "--symbol", symbol, "--timeframe", timeframe, "--count", String(count)],
      {
        cwd: process.cwd(),
        windowsHide: true,
        env: { ...process.env, MT5_TERMINAL_PATH: terminalPath },
      },
    );

    child.stdout.on("data", (chunk) => {
      stdout += String(chunk);
      if (stdout.length > 4_000_000) child.kill();
    });
    child.stderr.on("data", (chunk) => {
      stderr += String(chunk);
    });

    const timeout = setTimeout(() => {
      child.kill();
      finish({ ok: false, error: "Pengambilan candle MT5 melewati batas waktu" });
    }, timeoutMs);

    child.on("error", () => {
      clearTimeout(timeout);
      finish({ ok: false, error: "Proses pembaca data MT5 tidak dapat dijalankan" });
    });

    child.on("close", (code) => {
      clearTimeout(timeout);
      try {
        const parsed = JSON.parse(stdout.trim()) as Mt5RatesResult;
        if (parsed && typeof parsed.ok === "boolean") {
          finish(parsed);
          return;
        }
      } catch {
        // Return the sanitized fallback below.
      }

      const detail = stderr.trim().split(/\r?\n/).at(-1);
      finish({
        ok: false,
        error: detail ? `MT5 gagal membaca candle (${detail.slice(0, 160)})` : `MT5 gagal membaca candle (exit ${code ?? "unknown"})`,
      });
    });
  });
}
