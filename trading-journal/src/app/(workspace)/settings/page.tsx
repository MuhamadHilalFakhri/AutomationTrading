"use client";

import { useCallback, useEffect, useState } from "react";
import { PageHeader } from "@/components/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import {
  RefreshCw, FileCode2, TerminalSquare, Server, Database, Zap, Clock, CheckCircle2, XCircle, HelpCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

interface PathInfo { path: string; exists: boolean | null; }
interface AutoSyncState { enabled: boolean; interval: number; running: boolean; lastRun: string | null; lastResult: string | null; }
interface SettingsData {
  paths: {
    mt5SyncScript: PathInfo;
    python: PathInfo;
    journalUrl: PathInfo;
    terminalPath: PathInfo;
  };
  autoSync: AutoSyncState;
}

const PATH_META = [
  { key: "mt5SyncScript", label: "Script sinkronisasi", desc: "mt5_sync.py di folder bot", icon: FileCode2 },
  { key: "python", label: "Python (MetaTrader5)", desc: "Interpreter dengan package MetaTrader5", icon: Server },
  { key: "terminalPath", label: "Terminal MT5", desc: "Executable terminal64.exe", icon: TerminalSquare },
  { key: "journalUrl", label: "URL Journal", desc: "Endpoint penerima data sync", icon: Database },
] as const;

const INTERVALS = [
  { v: 15, label: "15 detik" },
  { v: 30, label: "30 detik" },
  { v: 60, label: "1 menit" },
  { v: 300, label: "5 menit" },
  { v: 900, label: "15 menit" },
  { v: 3600, label: "1 jam" },
];

function fmtLast(t: string | null) {
  if (!t) return "Belum pernah";
  return new Date(t).toLocaleString("id-ID", { timeZone: "Asia/Jakarta", hour12: false });
}

export default function SettingsPage() {
  const [data, setData] = useState<SettingsData | null>(null);
  const [enabled, setEnabled] = useState(false);
  const [interval, setIntervalVal] = useState(60);
  const [saving, setSaving] = useState(false);
  const [syncing, setSyncing] = useState(false);

  useEffect(() => {
    fetch("/api/settings", { cache: "no-store" })
      .then((r) => r.json())
      .then((d: SettingsData) => {
        setData(d);
        setEnabled(d.autoSync.enabled);
        setIntervalVal(d.autoSync.interval || 60);
      })
      .catch(() => toast.error("Gagal memuat pengaturan"));
  }, []);

  /** Simpan ke server, lalu sinkronkan state dari response server. */
  const save = useCallback(async (nextEnabled: boolean, nextInterval: number) => {
    setSaving(true);
    try {
      const r = await fetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: nextEnabled, interval: nextInterval }),
      });
      const d = await r.json();
      if (!r.ok || !d.ok) throw new Error(d.error ?? "gagal simpan");
      // state mengikuti server (source of truth)
      setEnabled(d.autoSync.enabled);
      setIntervalVal(d.autoSync.interval || 60);
      setData((prev) => (prev ? { ...prev, autoSync: d.autoSync } : prev));
      toast.success(
        d.autoSync.enabled
          ? `Auto sync aktif (tiap ${d.autoSync.interval} detik)`
          : "Auto sync dimatikan",
      );
    } catch (e) {
      // rollback ke state server saat gagal
      setData((prev) => {
        if (prev) {
          setEnabled(prev.autoSync.enabled);
          setIntervalVal(prev.autoSync.interval || 60);
        }
        return prev;
      });
      toast.error(String(e));
    } finally {
      setSaving(false);
    }
  }, []);

  const toggleEnabled = useCallback(() => save(!enabled, interval), [save, enabled, interval]);
  const changeInterval = useCallback(
    (v: number) => save(enabled, v),
    [save, enabled],
  );

  async function syncNow() {
    setSyncing(true);
    try {
      const r = await fetch("/api/sync/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ days: 90 }),
      });
      const d = await r.json();
      if (!r.ok || !d.ok) throw new Error(d.error ?? "gagal");
      toast.success(`Sync selesai: ${d.processedDeals ?? 0} deal, ${d.newTrades ?? 0} trade baru`);
      fetch("/api/settings", { cache: "no-store" })
        .then((rr) => rr.json())
        .then((dd) => setData((prev) => (prev ? { ...prev, autoSync: dd.autoSync } : prev)))
        .catch(() => {});
    } catch (e) {
      toast.error(String(e));
    } finally {
      setSyncing(false);
    }
  }

  const paths = data?.paths;
  const auto = data?.autoSync;

  return (
    <div>
      <PageHeader title="Pengaturan" subtitle="Konfigurasi sinkronisasi MT5 & auto sync" />

      <div className="grid gap-5 lg:grid-cols-2">
        {/* Auto Sync */}
        <Card className="rounded-[15px] border border-border bg-card shadow-none ring-0">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm font-semibold text-foreground">
              <Zap className="h-4 w-4 text-signal" /> Auto Sync
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <div className="glass-inset flex items-center justify-between gap-4 rounded-[15px] px-4 py-3.5">
              <div>
                <p className="text-sm font-medium text-foreground">Sinkronisasi otomatis</p>
                <p className="text-xs text-muted-foreground">Tarik data MT5 → journal secara berkala</p>
              </div>
              <Switch
                checked={enabled}
                onCheckedChange={toggleEnabled}
                disabled={saving}
                aria-label="Auto sync"
                className="border-border bg-background shadow-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring data-[checked]:border-border data-[checked]:bg-foreground [&_[data-slot=switch-thumb]]:data-[checked]:bg-border"
              />
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <label htmlFor="sync-interval" className="text-sm text-muted-foreground">Interval sync</label>
              <select
                id="sync-interval"
                value={interval}
                onChange={(e) => changeInterval(Number(e.target.value))}
                disabled={!enabled || saving}
                className="h-9 rounded-full border border-border bg-foreground px-3 text-sm text-black outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-40"
              >
                {INTERVALS.map((o) => (
                  <option key={o.v} value={o.v}>{o.label}</option>
                ))}
              </select>
              {saving && <span role="status" className="text-xs text-muted-foreground">Menyimpan...</span>}
            </div>

            {auto && (
              <div className="glass-inset flex flex-col gap-2 rounded-[15px] px-4 py-3 text-[13px]">
                <div className="flex items-center gap-2">
                  <Clock className="h-3.5 w-3.5 text-muted-foreground" />
                  <span className="text-muted-foreground">Status:</span>
                  <Badge variant="outline" className={cn("rounded-full border-border text-[10px]", auto.enabled ? "bg-foreground text-black" : "bg-background text-muted-foreground")}>
                    {auto.enabled ? "AKTIF" : "MATI"}
                  </Badge>
                  {auto.running && <Badge variant="outline" className="rounded-full border-border text-[10px] text-warning">SYNC BERJALAN</Badge>}
                </div>
                <p className="text-muted-foreground">Terakhir: <span className="font-mono text-foreground">{fmtLast(auto.lastRun)}</span></p>
                <p className="text-muted-foreground">Hasil: <span className={cn("font-mono", auto.lastResult?.startsWith("ok") ? "text-positive" : "text-muted-foreground")}>{auto.lastResult ?? "-"}</span></p>
              </div>
            )}

            <Button variant="outline" onClick={syncNow} disabled={syncing} className="rounded-full border-border bg-foreground text-black shadow-none hover:bg-muted-foreground hover:text-black focus-visible:ring-ring">
              <RefreshCw className={cn("h-4 w-4", syncing && "animate-spin")} />
              {syncing ? "Menyinkronkan..." : "Sync Sekarang"}
            </Button>
          </CardContent>
        </Card>

        {/* Paths */}
        <Card className="rounded-[15px] border border-border bg-card shadow-none ring-0">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm font-semibold text-foreground">
              <Database className="h-4 w-4 text-signal" /> Path yang disinkronkan
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {!paths ? (
              <p className="text-sm text-muted-foreground">Memuat...</p>
            ) : (
              PATH_META.map(({ key, label, desc, icon: Icon }) => {
                const p = paths[key];
                return (
                  <div key={key} className="glass-inset flex items-start gap-3 rounded-[15px] px-3.5 py-3">
                    <Icon className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-medium text-foreground">{label}</p>
                        {p.exists === null ? (
                          <HelpCircle className="h-3.5 w-3.5 text-muted-foreground" />
                        ) : p.exists ? (
                          <span className="flex items-center gap-1 text-[10px] text-positive"><CheckCircle2 className="h-3 w-3" /> ada</span>
                        ) : (
                          <span className="flex items-center gap-1 text-[10px] text-negative"><XCircle className="h-3 w-3" /> tidak ada</span>
                        )}
                      </div>
                      <p className="truncate font-mono text-xs text-muted-foreground">{p.path}</p>
                      <p className="mt-0.5 text-xs text-muted-foreground">{desc}</p>
                    </div>
                  </div>
                );
              })
            )}
            <p className="text-xs leading-5 text-muted-foreground">
              Path diatur lewat file <span className="font-mono text-muted-foreground">.env</span> di folder proyek (lihat <span className="font-mono text-muted-foreground">.env.example</span>). Sesuaikan saat pindah ke device lain.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
