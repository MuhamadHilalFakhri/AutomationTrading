"use client";

import * as React from "react";
import { Tabs as TabsPrimitive } from "@base-ui/react/tabs";
import { cn } from "@/lib/utils";

const Tabs = TabsPrimitive.Root;

function TabsList({ className, ...props }: TabsPrimitive.List.Props) {
  return (
    <TabsPrimitive.List
      data-slot="tabs-list"
      className={cn(
        "inline-flex min-h-10 items-center gap-1 rounded-lg border border-white/[0.07] bg-slate-950/75 p-1",
        className,
      )}
      {...props}
    />
  );
}

function TabsTrigger({ className, ...props }: TabsPrimitive.Tab.Props) {
  return (
    <TabsPrimitive.Tab
      data-slot="tabs-trigger"
      className={cn(
        "inline-flex h-8 items-center justify-center gap-2 rounded-md px-3 text-sm font-medium text-slate-500 transition-colors outline-none hover:bg-slate-800/70 hover:text-slate-200 focus-visible:ring-2 focus-visible:ring-blue-400/70 disabled:pointer-events-none disabled:opacity-50 data-active:bg-blue-500/15 data-active:text-blue-200 data-active:ring-1 data-active:ring-inset data-active:ring-blue-400/20",
        className,
      )}
      {...props}
    />
  );
}

function TabsContent({ className, ...props }: TabsPrimitive.Panel.Props) {
  return (
    <TabsPrimitive.Panel
      data-slot="tabs-content"
      className={cn("outline-none", className)}
      {...props}
    />
  );
}

export { Tabs, TabsContent, TabsList, TabsTrigger };
