"use client";

import { CandlestickChart, Crosshair } from "lucide-react";
import { Mt5EntryChart } from "@/components/mt5-entry-chart";
import { TradingViewChart } from "@/components/tradingview-chart";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export function ChartWorkspace() {
  return (
    <Tabs defaultValue="market" className="space-y-3">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <TabsList aria-label="Mode chart" activateOnFocus>
          <TabsTrigger value="market">
            <CandlestickChart />
            Chart Market
          </TabsTrigger>
          <TabsTrigger value="mt5">
            <Crosshair />
            Entry MT5
          </TabsTrigger>
        </TabsList>
        <p className="px-1 text-xs text-slate-500">Pilih feed market umum atau eksekusi dari akun MT5</p>
      </div>

      <TabsContent value="market">
        <TradingViewChart />
      </TabsContent>
      <TabsContent value="mt5">
        <Mt5EntryChart />
      </TabsContent>
    </Tabs>
  );
}
