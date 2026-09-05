"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { cn } from "@/lib/utils";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import {
  ArrowLeftRight, BarChart3, BrainCircuit, CalendarDays, CandlestickChart,
  LayoutDashboard, Menu, PanelLeftClose, PanelLeftOpen, Settings, SquareTerminal, X,
} from "lucide-react";

const NAV = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard, group: "Workspace" },
  { href: "/chart", label: "Market Chart", icon: CandlestickChart, group: "Workspace" },
  { href: "/terminal", label: "Terminal", icon: SquareTerminal, group: "Workspace" },
  { href: "/trades", label: "Trades", icon: ArrowLeftRight, group: "Workspace" },
  { href: "/kalender", label: "Kalender PnL", icon: CalendarDays, group: "Insights" },
  { href: "/analitik", label: "Analitik", icon: BarChart3, group: "Insights" },
  { href: "/sinyal", label: "Sinyal AI", icon: BrainCircuit, group: "Insights" },
  { href: "/settings", label: "Pengaturan", icon: Settings, group: "System" },
];

function NavLinks({ onNavigate, collapsed = false }: { onNavigate?: () => void; collapsed?: boolean }) {
  const pathname = usePathname();
  return (
    <TooltipProvider delay={250}>
    <nav aria-label="Navigasi utama" className={cn("flex flex-col gap-1 py-4", collapsed ? "px-2" : "px-3")}>
      {NAV.map(({ href, label, icon: Icon, group }, index) => {
        const active = href === "/" ? pathname === href : pathname.startsWith(href);
        const showGroup = index === 0 || NAV[index - 1].group !== group;
        const navLink = (
          <Link
            href={href}
            onClick={onNavigate}
            aria-label={collapsed ? label : undefined}
            aria-current={active ? "page" : undefined}
            className={cn(
              "group flex min-h-10 items-center rounded-lg text-[14px] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400/70",
              collapsed ? "justify-center px-0" : "gap-3 px-3",
              active
                ? "bg-blue-500/12 font-medium text-blue-200 ring-1 ring-inset ring-blue-400/20"
                : "text-slate-400 hover:bg-slate-800/70 hover:text-slate-100",
            )}
          >
            <Icon className={cn("h-[18px] w-[18px] shrink-0", active ? "text-blue-400" : "text-slate-500 group-hover:text-slate-300")} />
            <span className={collapsed ? "sr-only" : undefined}>{label}</span>
          </Link>
        );
        return (
          <div key={href}>
            {showGroup && !collapsed && (
              <p className="px-3 pb-2 pt-3 text-[11px] font-medium tracking-normal text-slate-500 first:pt-0">{group}</p>
            )}
            {showGroup && collapsed && index > 0 && <div aria-hidden="true" className="mx-3 my-2 h-px bg-white/[0.07]" />}
            {collapsed ? (
              <Tooltip>
                <TooltipTrigger render={navLink} />
                <TooltipContent side="right" sideOffset={8} className="bg-slate-100 text-slate-950">
                  {label}
                </TooltipContent>
              </Tooltip>
            ) : navLink}
          </div>
        );
      })}
    </nav>
    </TooltipProvider>
  );
}

function Brand({ collapsed = false }: { collapsed?: boolean }) {
  return (
    <Link href="/" aria-label="Trading Journal" className={cn("flex min-w-0 items-center py-5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400/70", collapsed ? "gap-0 px-1" : "gap-3 px-5")}>
      <Image src="/icon-64.png" alt="" width={32} height={32} className={cn("shrink-0 rounded-lg", collapsed ? "h-7 w-7" : "h-8 w-8")} priority />
      <span className={cn("min-w-0", collapsed && "sr-only")}>
        <span className="block truncate text-[15px] font-semibold tracking-tight text-slate-100">Trading Journal</span>
        <span className="block text-[11px] text-slate-500">MT5 workspace</span>
      </span>
    </Link>
  );
}

function SidebarContent({
  onNavigate,
  collapsed = false,
  onToggle,
  showHeader = true,
}: {
  onNavigate?: () => void;
  collapsed?: boolean;
  onToggle?: () => void;
  showHeader?: boolean;
}) {
  return (
    <>
      {showHeader && (
        <div className={cn("flex min-h-[73px] items-center border-b border-white/[0.07]", collapsed ? "justify-between px-2" : "justify-between pr-2")}>
          <Brand collapsed={collapsed} />
          {onToggle && (
            <button
              type="button"
              onClick={onToggle}
              aria-label={collapsed ? "Perluas sidebar" : "Ringkas sidebar"}
              title={collapsed ? "Perluas sidebar" : "Ringkas sidebar"}
              className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-slate-500 transition-colors hover:bg-slate-800 hover:text-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400/70"
            >
              {collapsed ? <PanelLeftOpen className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
            </button>
          )}
        </div>
      )}
      <NavLinks onNavigate={onNavigate} collapsed={collapsed} />
      <div className={cn("mt-auto border-t border-white/[0.07]", collapsed ? "p-2" : "p-4")}>
        <div
          role="status"
          title={collapsed ? "Workspace aktif · Menunggu feed MT5" : undefined}
          className={cn("glass-inset flex items-center rounded-lg", collapsed ? "h-10 justify-center px-0" : "gap-2.5 px-3 py-2.5")}
        >
          <span className="relative flex h-2.5 w-2.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400/60" />
            <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-emerald-400" />
          </span>
          <div className={cn("min-w-0", collapsed && "sr-only")}>
            <p className="text-xs font-medium text-slate-200">Workspace aktif</p>
            <p className="truncate text-[11px] text-slate-500">Menunggu feed MT5</p>
          </div>
        </div>
      </div>
    </>
  );
}

export function Sidebar() {
  const [open, setOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  const toggleCollapsed = () => {
    setCollapsed((current) => {
      const next = !current;
      document.documentElement.style.setProperty("--sidebar-width", next ? "5rem" : "16rem");
      return next;
    });
  };

  return (
    <>
      <header className="glass-nav fixed inset-x-0 top-0 z-40 flex h-16 items-center justify-between border-b px-4 lg:hidden">
        <Link href="/" className="flex items-center gap-2.5">
          <Image src="/icon-32.png" alt="" width={26} height={26} className="rounded-md" />
          <span className="text-sm font-semibold text-slate-100">Trading Journal</span>
        </Link>
        <button type="button" onClick={() => setOpen(true)} className="inline-flex h-10 w-10 items-center justify-center rounded-lg text-slate-400 transition-colors hover:bg-slate-800 hover:text-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400/70" aria-label="Buka menu">
          <Menu className="h-5 w-5" />
        </button>
      </header>

      {open && <button type="button" aria-label="Tutup menu" className="fixed inset-0 z-50 bg-slate-950/78 lg:hidden" onClick={() => setOpen(false)} />}

      <aside className={cn("glass-nav fixed inset-y-0 left-0 z-[60] flex w-72 flex-col border-r transition-transform duration-200 lg:hidden", open ? "translate-x-0" : "-translate-x-full")}>
        <div className="flex items-center justify-between border-b border-white/[0.07] pr-3">
          <Brand />
          <button type="button" onClick={() => setOpen(false)} className="inline-flex h-10 w-10 items-center justify-center rounded-lg text-slate-500 hover:bg-slate-800 hover:text-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400/70" aria-label="Tutup menu"><X className="h-5 w-5" /></button>
        </div>
        <SidebarContent onNavigate={() => setOpen(false)} showHeader={false} />
      </aside>

      <aside className={cn("glass-nav fixed inset-y-0 left-0 z-40 hidden flex-col border-r transition-[width] duration-200 ease-out lg:flex", collapsed ? "w-20" : "w-64")}>
        <SidebarContent collapsed={collapsed} onToggle={toggleCollapsed} />
      </aside>
    </>
  );
}
