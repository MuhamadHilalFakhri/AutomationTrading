"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowUpRight, BarChart3, BrainCircuit, CalendarDays, CandlestickChart, LayoutDashboard, ListFilter, RefreshCw, SquareTerminal } from "lucide-react";
import styles from "@/app/landing.module.css";

const features = [
  { title: "Dashboard performa", category: "Monitoring", icon: LayoutDashboard, href: "/dashboard", label: "THE BIG PICTURE", text: "Win rate, realized PnL, posisi terbuka, dan pending order. Ringkasan yang Anda butuhkan, dalam satu tampilan." },
  { title: "Jurnal transaksi", category: "Jurnal & Analitik", icon: ListFilter, href: "/trades", label: "EVERY TRADE MATTERS", text: "Telusuri transaksi berdasarkan simbol, status, dan rentang tanggal. Kembali ke detail, bukan sekadar ingatan." },
  { title: "Jejak sinyal AI", category: "Sinyal & Integrasi", icon: BrainCircuit, href: "/sinyal", label: "BEHIND THE DECISION", text: "Tinjau BUY, SELL, dan HOLD beserta confidence, alasan, serta status eksekusi yang tercatat dari bot." },
  { title: "Kalender & analitik PnL", category: "Jurnal & Analitik", icon: CalendarDays, href: "/kalender", label: "PATTERNS OVER NOISE", text: "Baca hasil harian dalam kalender bulanan. Lanjutkan ke analitik untuk mengevaluasi simbol dan strategi." },
  { title: "Market chart & terminal", category: "Monitoring", icon: CandlestickChart, href: "/chart", label: "MARKET IN CONTEXT", text: "Amati market melalui chart TradingView dan entry MT5. Ikuti aktivitas bot secara terpisah di terminal live." },
  { title: "Sinkronisasi MT5", category: "Sinyal & Integrasi", icon: RefreshCw, href: "/settings", label: "CONNECTED TO YOUR FLOW", text: "Atur interval sinkronisasi otomatis, jalankan sync manual, dan periksa status pembaruan data terakhir." },
];
const filters = ["Semua fitur", "Monitoring", "Jurnal & Analitik", "Sinyal & Integrasi"];

export function FeatureExplorer() {
  const [filter, setFilter] = useState("Semua fitur");
  return <div>
    <div className={styles.filterBar}><div className={styles.filters} role="group" aria-label="Filter fitur">{filters.map((item) => <button key={item} type="button" aria-pressed={filter === item} onClick={() => setFilter(item)} className={filter === item ? styles.activeFilter : undefined}>{item}</button>)}</div><span className={styles.filterCaption}><SquareTerminal size={14} /> Dirancang untuk alur trading Anda</span></div>
    <div className={styles.featureGrid} aria-live="polite">{features.filter((feature) => filter === "Semua fitur" || feature.category === filter).map(({ title, icon: Icon, href, label, text }) => <Link key={title} href={href} className={styles.featureCard}><div className={styles.featureTop}><Icon size={28} strokeWidth={1.4} /><ArrowUpRight size={18} /></div><p className={styles.featureLabel}>{label}</p><h3>{title}</h3><p>{text}</p><span className={styles.featureLink}>Jelajahi fitur <ArrowUpRight size={14} /></span></Link>)}</div>
    <Link href="/analitik" className={styles.analyticsNote}><BarChart3 size={17} /><span>Angka memberi gambaran. Analitik memberi konteks.</span><span>Buka analitik <ArrowUpRight size={15} /></span></Link>
  </div>;
}
