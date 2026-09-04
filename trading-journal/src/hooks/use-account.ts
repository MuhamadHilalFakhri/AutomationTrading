"use client";

import { useEffect, useRef, useState } from "react";

export interface AccountState {
  balance: number | null;
  equity: number | null;
  currency: string;
  server: string;
  ts: string | null;
}

const EMPTY: AccountState = { balance: null, equity: null, currency: "USD", server: "", ts: null };

export function useAccount(intervalMs = 10000) {
  const [account, setAccount] = useState<AccountState>(EMPTY);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    let active = true;
    const load = () => {
      fetch("/api/account", { cache: "no-store" })
        .then((r) => (r.ok ? r.json() : null))
        .then((d) => {
          if (!active || !d?.ok) return;
          setAccount({
            balance: d.balance,
            equity: d.equity,
            currency: d.currency ?? "USD",
            server: d.server ?? "",
            ts: d.ts ?? null,
          });
        })
        .catch(() => {});
    };
    load();
    timer.current = setInterval(load, intervalMs);
    return () => {
      active = false;
      if (timer.current) clearInterval(timer.current);
    };
  }, [intervalMs]);

  return account;
}
