"use client";

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
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard, group: "Workspace" },
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
        const active = pathname === href || pathname.startsWith(`${href}/`);
        const showGroup = index === 0 || NAV[index - 1].group !== group;
        const navLink = (
          <Link
            href={href}
            onClick={onNavigate}
            aria-label={collapsed ? label : undefined}
            aria-current={active ? "page" : undefined}
            className={cn(
              "group flex min-h-11 items-center rounded-full text-[13px] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              collapsed ? "justify-center px-0" : "gap-3 px-3",
              active
                ? "bg-primary font-semibold text-primary-foreground"
                : "text-muted-foreground hover:bg-card hover:text-foreground",
            )}
          >
            <Icon className={cn("h-[18px] w-[18px] shrink-0", active ? "text-primary-foreground" : "text-muted-foreground group-hover:text-signal")} />
            <span className={collapsed ? "sr-only" : undefined}>{label}</span>
          </Link>
        );
        return (
          <div key={href}>
            {showGroup && !collapsed && (
              <p className="px-3 pb-2 pt-5 text-[9px] font-medium uppercase tracking-[0.14em] text-muted-foreground first:pt-0">{group}</p>
            )}
            {showGroup && collapsed && index > 0 && <div aria-hidden="true" className="mx-3 my-2 h-px bg-divider" />}
            {collapsed ? (
              <Tooltip>
                <TooltipTrigger render={navLink} />
                <TooltipContent side="right" sideOffset={8}>
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
    <Link href="/dashboard" aria-label="Trading Journal" className={cn("flex min-w-0 items-center py-5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring", collapsed ? "gap-0 px-1" : "gap-2 px-4")}>
      <CandlestickChart aria-hidden="true" className="h-7 w-7 shrink-0 text-signal" />
      <span className={cn("min-w-0", collapsed && "sr-only")}>
        <span className="block text-[18px] font-bold tracking-[-0.06em] text-foreground">trading<span className="font-normal">journal</span><span className="text-signal">.</span></span>
        <span className="block text-[10px] text-muted-foreground">MT5 workspace</span>
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
        <div className={cn("flex min-h-[84px] items-center border-b border-divider", collapsed ? "justify-between px-2" : "justify-between pr-2")}>
          <Brand collapsed={collapsed} />
          {onToggle && (
            <button
              type="button"
              onClick={onToggle}
              aria-label={collapsed ? "Perluas sidebar" : "Ringkas sidebar"}
              title={collapsed ? "Perluas sidebar" : "Ringkas sidebar"}
              className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-muted-foreground transition-colors hover:bg-card hover:text-signal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              {collapsed ? <PanelLeftOpen className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
            </button>
          )}
        </div>
      )}
      <NavLinks onNavigate={onNavigate} collapsed={collapsed} />
      <div className={cn("mt-auto border-t border-divider", collapsed ? "p-2" : "p-4")}>
        <div
          role="status"
          title={collapsed ? "Workspace aktif · Menunggu feed MT5" : undefined}
          className={cn("flex items-center rounded-[15px] border border-border bg-card", collapsed ? "h-10 justify-center px-0" : "gap-2.5 px-3 py-3")}
        >
          <SquareTerminal aria-hidden="true" className="h-4 w-4 shrink-0 text-signal" />
          <div className={cn("min-w-0", collapsed && "sr-only")}>
            <p className="text-xs font-medium text-foreground">Workspace aktif</p>
            <p className="truncate text-[10px] text-muted-foreground">Menunggu feed MT5</p>
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
        <Link href="/dashboard" className="flex items-center gap-2.5">
          <CandlestickChart aria-hidden="true" className="h-6 w-6 text-signal" />
          <span className="text-xl font-bold tracking-[-0.06em] text-foreground">trading<span className="font-normal">journal</span><span className="text-signal">.</span></span>
        </Link>
        <button type="button" onClick={() => setOpen(true)} className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-signal text-signal transition-colors hover:bg-card focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" aria-label="Buka menu">
          <Menu className="h-5 w-5" />
        </button>
      </header>

      {open && <button type="button" aria-label="Tutup menu" className="fixed inset-0 z-50 bg-black/70 lg:hidden" onClick={() => setOpen(false)} />}

      <aside className={cn("glass-nav fixed inset-y-0 left-0 z-[60] flex w-72 flex-col border-r transition-transform duration-200 lg:hidden", open ? "translate-x-0" : "-translate-x-full")}>
        <div className="flex items-center justify-between border-b border-divider pr-3">
          <Brand />
          <button type="button" onClick={() => setOpen(false)} className="inline-flex h-10 w-10 items-center justify-center rounded-full text-muted-foreground hover:bg-card hover:text-signal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" aria-label="Tutup menu"><X className="h-5 w-5" /></button>
        </div>
        <SidebarContent onNavigate={() => setOpen(false)} showHeader={false} />
      </aside>

      <aside className={cn("glass-nav fixed inset-y-0 left-0 z-40 hidden flex-col border-r transition-[width] duration-200 ease-out lg:flex", collapsed ? "w-20" : "w-64")}>
        <SidebarContent collapsed={collapsed} onToggle={toggleCollapsed} />
      </aside>
    </>
  );
}
