"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import Image from "next/image";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard, SquareTerminal, CalendarDays, ArrowLeftRight,
  BrainCircuit, BarChart3, Menu, X, Settings,
} from "lucide-react";

const NAV = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/terminal", label: "Terminal", icon: SquareTerminal },
  { href: "/kalender", label: "Kalender PnL", icon: CalendarDays },
  { href: "/trades", label: "Trades", icon: ArrowLeftRight },
  { href: "/sinyal", label: "Sinyal AI", icon: BrainCircuit },
  { href: "/analitik", label: "Analitik", icon: BarChart3 },
  { href: "/settings", label: "Pengaturan", icon: Settings },
];

function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  return (
    <nav className="flex flex-col gap-1 p-3">
      {NAV.map(({ href, label, icon: Icon }) => {
        const active = pathname === href;
        return (
          <Link
            key={href}
            href={href}
            onClick={onNavigate}
            className={cn(
              "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
              active
                ? "bg-zinc-800/80 font-medium text-zinc-100"
                : "text-zinc-500 hover:bg-zinc-900 hover:text-zinc-200",
            )}
          >
            <Icon className="h-4 w-4 shrink-0" />
            {label}
          </Link>
        );
      })}
    </nav>
  );
}

function Brand() {
  return (
    <div className="flex items-center gap-2.5 px-5 py-4">
      <Image
        src="/logo-brand.png"
        alt="Trading Journal"
        width={220}
        height={162}
        className="h-10 w-auto object-contain"
        priority
      />
    </div>
  );
}

export function Sidebar() {
  const [open, setOpen] = useState(false);

  return (
    <>
      {/* top bar mobile */}
      <header className="fixed inset-x-0 top-0 z-40 flex items-center gap-3 border-b border-zinc-800 bg-black/90 px-4 py-3 backdrop-blur lg:hidden">
        <button
          onClick={() => setOpen(true)}
          className="text-zinc-400 hover:text-zinc-100"
          aria-label="Buka menu"
        >
          <Menu className="h-5 w-5" />
        </button>
        <span className="text-sm font-semibold">Trading Journal</span>
      </header>

      {/* backdrop drawer */}
      {open && (
        <div
          className="fixed inset-0 z-50 bg-black/60 lg:hidden"
          onClick={() => setOpen(false)}
        />
      )}

      {/* drawer mobile */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-60 flex-col border-r border-zinc-800 bg-zinc-950 transition-transform duration-200 lg:hidden",
          open ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="flex items-center justify-between border-b border-zinc-800 pr-3">
          <Brand />
          <button
            onClick={() => setOpen(false)}
            className="text-zinc-500 hover:text-zinc-200"
            aria-label="Tutup menu"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <NavLinks onNavigate={() => setOpen(false)} />
        <p className="mt-auto p-4 text-[11px] text-zinc-700">MT5 AI Trading Bot Journal</p>
      </aside>

      {/* sidebar desktop */}
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-60 flex-col border-r border-zinc-800 bg-zinc-950 lg:flex">
        <div className="border-b border-zinc-800">
          <Brand />
        </div>
        <NavLinks />
        <p className="mt-auto p-4 text-[11px] text-zinc-700">MT5 AI Trading Bot Journal</p>
      </aside>
    </>
  );
}
