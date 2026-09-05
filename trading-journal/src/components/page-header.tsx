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
    <header className={cn("mb-8 flex flex-col gap-5 border-b border-divider pb-6 pt-2 lg:flex-row lg:items-end lg:justify-between", className)}>
      <div className="min-w-0">
        <p className="mb-3 text-[10px] font-medium uppercase tracking-[0.16em] text-muted-foreground">Trading workspace / MT5</p>
        <h1 className="text-[28px] font-semibold tracking-[-0.05em] text-foreground sm:text-4xl">{title}</h1>
        {subtitle && <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">{subtitle}</p>}
      </div>
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="inline-flex h-8 items-center gap-1.5 rounded-full border border-divider px-3 text-muted-foreground">
          <span>WIB</span><span className="tabular-nums text-foreground">{time}</span>
        </span>
        {account.balance != null && (
          <span className="inline-flex min-h-8 flex-wrap items-center gap-2 rounded-full border border-divider px-3 py-1 tabular-nums">
            <span className="text-muted-foreground">Bal</span>
            <span className="text-foreground">{account.balance.toLocaleString("id-ID", { minimumFractionDigits: 2 })}</span>
            <span className="text-muted-foreground">/</span>
            <span className="text-muted-foreground">Eq</span>
            <span className={account.equity != null && account.equity < account.balance ? "text-negative" : "text-foreground"}>{account.equity?.toLocaleString("id-ID", { minimumFractionDigits: 2 }) ?? "-"}</span>
            <span className="text-muted-foreground">{account.currency}</span>
          </span>
        )}
        <Button type="button" variant="outline" size="sm" onClick={doSync} disabled={syncing} className="h-8">
          <RefreshCw className={cn("h-3.5 w-3.5", syncing && "animate-spin")} />
          {syncing ? "Sync..." : "Sync MT5"}
        </Button>
        {connected !== undefined && (
          <span className="inline-flex h-8 items-center gap-2 rounded-full border border-divider px-3 text-muted-foreground">
            <span className={cn("h-1.5 w-1.5 rounded-full", connected ? "animate-pulse bg-signal" : "border border-muted-foreground")} />
            {connected ? "Live" : "Offline"}
          </span>
        )}
        {syncMsg && <span role="status" className="basis-full text-right text-xs text-muted-foreground">{syncMsg}</span>}
      </div>
    </header>
  );
}
