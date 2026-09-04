"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { RefreshCw } from "lucide-react";

interface AccountInfo {
  balance: number | null;
  equity: number | null;
  currency: string;
}

export function PageHeader({
  title, subtitle, connected,
}: {
  title: string;
  subtitle?: string;
  connected?: boolean;
}) {
  const [account, setAccount] = useState<AccountInfo>({ balance: null, equity: null, currency: "USD" });
  const [syncing, setSyncing] = useState(false);
  const [syncMsg, setSyncMsg] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const load = () => {
      fetch("/api/account", { cache: "no-store" })
        .then((r) => (r.ok ? r.json() : null))
        .then((d) => {
          if (!active || !d?.ok) return;
          setAccount({ balance: d.balance, equity: d.equity, currency: d.currency ?? "USD" });
        })
        .catch(() => {});
    };
    load();
    const t = setInterval(load, 10000);
    return () => {
      active = false;
      clearInterval(t);
    };
  }, []);

  const doSync = async () => {
    setSyncing(true);
    setSyncMsg(null);
    try {
      const r = await fetch("/api/sync/run", { method: "POST" });
      const d = await r.json();
      setSyncMsg(d?.ok ? `Sync ok — ${d.processedDeals} deals, ${d.newTrades} baru` : `Sync gagal: ${d?.error ?? r.status}`);
    } catch (e) {
      setSyncMsg(`Sync gagal: ${String(e)}`);
    } finally {
      setSyncing(false);
    }
  };

  return (
    <header className="mb-6 flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
        {subtitle && <p className="mt-0.5 text-sm text-zinc-600">{subtitle}</p>}
      </div>
      <div className="flex flex-wrap items-center gap-3 text-xs">
        <span className="rounded-md border border-zinc-800 bg-zinc-950 px-2 py-1 font-mono text-zinc-500">
          WIB {new Date().toLocaleTimeString("id-ID", { hour12: false, timeZone: "Asia/Jakarta" })}
        </span>
        {account.balance != null && (
          <span className="flex items-center gap-2 rounded-md border border-zinc-800 bg-zinc-950 px-2 py-1 font-mono">
            <span className="text-zinc-500">Bal</span>
            <span className={account.equity != null && account.equity < account.balance ? "text-amber-400" : "text-emerald-400"}>
              {account.balance.toLocaleString("id-ID", { minimumFractionDigits: 2 })} {account.currency}
            </span>
            <span className="text-zinc-700">/</span>
            <span className="text-zinc-500">Eq</span>
            <span className="text-zinc-300">
              {account.equity?.toLocaleString("id-ID", { minimumFractionDigits: 2 })} {account.currency}
            </span>
          </span>
        )}
        <button
          onClick={doSync}
          disabled={syncing}
          className="flex items-center gap-1.5 rounded-md border border-zinc-800 bg-zinc-950 px-2 py-1 font-mono text-zinc-400 transition-colors hover:border-zinc-700 hover:text-zinc-200 disabled:opacity-50"
        >
          <RefreshCw className={cn("h-3 w-3", syncing && "animate-spin")} />
          Sync MT5
        </button>
        {connected !== undefined && (
          <span className="flex items-center gap-2">
            <span
              className={cn(
                "inline-block h-1.5 w-1.5 rounded-full",
                connected ? "animate-pulse bg-emerald-400" : "bg-red-500",
              )}
            />
            <span className={connected ? "text-emerald-400" : "text-red-400"}>
              {connected ? "connected" : "disconnected"}
            </span>
          </span>
        )}
      </div>
      {syncMsg && <div className="w-full text-right text-xs text-zinc-500">{syncMsg}</div>}
    </header>
  );
}
