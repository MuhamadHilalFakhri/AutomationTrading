"use client";

import { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface AccountInfo { balance: number | null; equity: number | null; currency: string; }

function formatWibTime() {
  return new Date().toLocaleTimeString("id-ID", {
    hour12: false,
    timeZone: "Asia/Jakarta",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function PageHeader({
  title,
  subtitle,
  connected,
  className,
}: {
  title: string;
  subtitle?: string;
  connected?: boolean;
  className?: string;
}) {
  const [account, setAccount] = useState<AccountInfo>({ balance: null, equity: null, currency: "USD" });
  const [syncing, setSyncing] = useState(false);
  const [syncMsg, setSyncMsg] = useState<string | null>(null);
  // Keep the server and first client render identical; the live clock starts after hydration.
  const [time, setTime] = useState("--:--:--");

  useEffect(() => {
    let active = true;
    const load = () => fetch("/api/account", { cache: "no-store" })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => { if (active && d?.ok) setAccount({ balance: d.balance, equity: d.equity, currency: d.currency ?? "USD" }); })
      .catch(() => {});
    load();
    const timer = setInterval(load, 10000);
    return () => { active = false; clearInterval(timer); };
  }, []);

  useEffect(() => {
    const timer = setInterval(() => setTime(formatWibTime()), 1000);
    return () => clearInterval(timer);
  }, []);

  const doSync = async () => {
    setSyncing(true); setSyncMsg(null);
    try {
      const r = await fetch("/api/sync/run", { method: "POST" });
      const d = await r.json();
      setSyncMsg(d?.ok ? `Sync selesai · ${d.processedDeals} deal, ${d.newTrades} baru` : `Sync gagal · ${d?.error ?? r.status}`);
    } catch (e) { setSyncMsg(`Sync gagal · ${String(e)}`); }
    finally { setSyncing(false); }
  };

  return (
    <header className={cn("glass-panel mb-7 flex flex-col gap-4 rounded-2xl px-4 py-4 sm:px-5 lg:flex-row lg:items-end lg:justify-between", className)}>
      <div className="min-w-0">
        <p className="mb-1 text-xs font-medium tracking-normal text-blue-400/80">Trading workspace</p>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-50 sm:text-[28px]">{title}</h1>
        {subtitle && <p className="mt-1 max-w-2xl text-sm leading-6 text-slate-400">{subtitle}</p>}
      </div>
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="glass-inset inline-flex h-8 items-center gap-1.5 rounded-lg px-2.5 text-slate-400">
          <span className="text-slate-500">WIB</span><span className="font-mono text-slate-200">{time}</span>
        </span>
        {account.balance != null && (
          <span className="glass-inset inline-flex h-8 items-center gap-2 rounded-lg px-2.5 font-mono">
            <span className="text-slate-500">Bal</span>
            <span className="text-slate-300">{account.balance.toLocaleString("id-ID", { minimumFractionDigits: 2 })}</span>
            <span className="text-slate-600">/</span>
            <span className="text-slate-500">Eq</span>
            <span className={account.equity != null && account.equity < account.balance ? "text-amber-300" : "text-emerald-300"}>{account.equity?.toLocaleString("id-ID", { minimumFractionDigits: 2 })}</span>
            <span className="text-slate-500">{account.currency}</span>
          </span>
        )}
        <Button type="button" variant="outline" size="sm" onClick={doSync} disabled={syncing} className="h-8 border-slate-700 bg-slate-900/70 text-slate-300 hover:border-blue-500/50 hover:bg-blue-500/10 hover:text-blue-200">
          <RefreshCw className={cn("h-3.5 w-3.5", syncing && "animate-spin")} />
          {syncing ? "Sync..." : "Sync MT5"}
        </Button>
        {connected !== undefined && (
          <span className={cn("inline-flex h-8 items-center gap-2 rounded-lg px-2.5", connected ? "bg-emerald-500/10 text-emerald-300" : "bg-red-500/10 text-red-300")}>
            <span className={cn("h-1.5 w-1.5 rounded-full", connected ? "animate-pulse bg-emerald-400" : "bg-red-400")} />
            {connected ? "Live" : "Offline"}
          </span>
        )}
        {syncMsg && <span role="status" className="basis-full text-right text-xs text-slate-500">{syncMsg}</span>}
      </div>
    </header>
  );
}
