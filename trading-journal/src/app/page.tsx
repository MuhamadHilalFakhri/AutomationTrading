import type { Metadata } from "next";
import Link from "next/link";
import { Activity, ArrowDown, ArrowRight, ArrowUpRight, BarChart3, BrainCircuit, CalendarDays, CandlestickChart, Check, Database, Radio, RefreshCw, SquareTerminal, Target } from "lucide-react";
import { FeatureExplorer } from "@/components/landing-feature-explorer";
import styles from "./landing.module.css";

export const metadata: Metadata = {
  title: "Trading Journal | Catat. Pahami. Tingkatkan.",
  description: "Workspace jurnal trading untuk bot MT5. Pantau transaksi, evaluasi PnL, dan telusuri keputusan AI dalam satu tempat.",
};

const steps = [
  { icon: RefreshCw, title: "Hubungkan data MT5", text: "Atur integrasi terminal MT5, lalu jalankan sinkronisasi manual atau berkala dari pengaturan." },
  { icon: SquareTerminal, title: "Ikuti setiap aktivitas", text: "Pantau posisi, transaksi, dan event bot. Telusuri keputusan AI beserta alasan yang tercatat." },
  { icon: Target, title: "Evaluasi dengan konteks", text: "Baca kalender PnL dan bandingkan performa simbol serta strategi sebelum mengambil langkah berikutnya." },
];

export default function LandingPage() {
  return (
    <div className={styles.landing}>
      <a href="#konten" className={styles.skipLink}>Lewati ke konten</a>
      <div className={styles.announcement}><span>BUILT FOR MT5</span> Dari aktivitas bot menjadi insight yang berarti. <a href="#cara-kerja">Kenali workspace <ArrowRight size={13} /></a></div>
      <div className={styles.atmosphere}>
        <header className={`${styles.container} ${styles.header}`}>
          <Link href="/" className={styles.brand} aria-label="Trading Journal beranda"><CandlestickChart aria-hidden="true" size={30} /><span>trading<span className={styles.brandLight}>journal</span><span className={styles.brandDot}>.</span></span></Link>
          <nav aria-label="Navigasi landing page" className={styles.nav}><a href="#fitur">Workspace</a><a href="#cara-kerja">Cara kerja</a><a href="#faq">FAQ</a></nav>
          <Link href="/dashboard" className={styles.primary}>Buka Dashboard <ArrowUpRight size={16} /></Link>
        </header>
        <main id="konten">
          <section className={`${styles.container} ${styles.hero}`} aria-labelledby="hero-title">
            <div className={styles.eyebrow}><span className={styles.signalDot} /> YOUR TRADING. IN PERSPECTIVE.</div>
            <h1 id="hero-title">Bukan sekadar trading.<br />Pahami <span>setiap keputusan.</span></h1>
            <p className={styles.heroCopy}>Satu workspace untuk jurnal trading, performa MT5, dan jejak keputusan AI.<br className={styles.desktopBreak} /> Lebih sedikit tebakan. Lebih banyak konteks.</p>
            <div className={styles.actions}><Link href="/dashboard" className={styles.primary}>Jelajahi Dashboard <ArrowUpRight size={17} /></Link><a href="#fitur" className={styles.secondary}>Lihat fitur <ArrowDown size={16} /></a></div>
            <div className={styles.heroNotes}><span><Check size={13} /> Terintegrasi dengan MT5</span><span><Check size={13} /> Jurnal & analitik dalam satu tempat</span></div>

            <div className={styles.previewHeading}><span><Activity size={14} /> PERSPEKTIF PERFORMA</span><span className={styles.demoBadge}>ILUSTRASI DATA, BUKAN HASIL AKTUAL</span></div>
            <div className={styles.metrics}>
              <article className={styles.metricCard}>
                <div className={styles.cardTop}><span className={styles.iconBadge}><BarChart3 size={20} /></span><div><h2>Realized PnL</h2><p>Hasil dari posisi yang ditutup</p></div><ArrowUpRight size={17} /></div>
                <div className={styles.metricValue}>+$1,284<span>.50</span></div>
                <svg className={styles.sparkline} viewBox="0 0 320 64" fill="none" aria-hidden="true"><path d="M0 52H320M0 28H320M0 4H320" stroke="white" strokeOpacity=".07" /><path d="M0 54L20 48L35 52L54 36L73 42L94 32L113 37L133 22L153 31L173 19L193 24L214 9L234 16L254 7L275 12L295 5L320 2" stroke="#6ae4ff" strokeWidth="2" /></svg>
                <div className={styles.cardBottom}><span>Rekap hasil trading</span><span>30 hari</span></div>
              </article>
              <article className={styles.metricCard}>
                <div className={styles.cardTop}><span className={styles.iconBadge}><Target size={20} /></span><div><h2>Win Rate</h2><p>Perspektif di balik setiap hasil</p></div><ArrowUpRight size={17} /></div>
                <div className={styles.metricValue}>64<span>.8%</span></div>
                <div className={styles.winBars} aria-hidden="true">{Array.from({ length: 30 }, (_, i) => <i key={i} className={i < 19 ? styles.wonBar : undefined} />)}</div>
                <div className={styles.cardBottom}><span>81 menang / 125 closed</span><span>Closed trades</span></div>
              </article>
              <article className={styles.metricCard}>
                <div className={styles.cardTop}><span className={styles.iconBadge}><BrainCircuit size={20} /></span><div><h2>Jejak Keputusan AI</h2><p>Sinyal, alasan, dan eksekusi</p></div><ArrowUpRight size={17} /></div>
                <div className={styles.decision}><span>HOLD</span><span className={styles.decisionSymbol}>XAUUSD <span>/ M15</span></span></div>
                <p className={styles.reason}>&quot;Menunggu konfirmasi arah sebelum membuka posisi baru.&quot;</p>
                <div className={styles.cardBottom}><span>Contoh alasan sinyal</span><span>Confidence 78%</span></div>
              </article>
            </div>
            <div className={styles.contextStrip}><p>DARI TERMINAL.<br /><strong>UNTUK PERSPEKTIF YANG UTUH.</strong></p><span><CandlestickChart size={21} /> MetaTrader 5</span><span><Activity size={21} /> Live event feed</span><span><Database size={21} /> Riwayat transaksi</span><span><CalendarDays size={21} /> Rekap PnL</span></div>
          </section>

          <section id="fitur" className={`${styles.container} ${styles.section}`} aria-labelledby="features-title">
            <div className={styles.sectionHeading}><div><p className={styles.kicker}>01 / WORKSPACE</p><h2 id="features-title">Semua data. <span>Satu sudut pandang.</span></h2></div><p>Dari gambaran besar hingga detail satu transaksi.<br />Temukan konteks tanpa berpindah-pindah alat.</p></div>
            <FeatureExplorer />
          </section>

          <section id="cara-kerja" className={`${styles.container} ${styles.section}`} aria-labelledby="workflow-title">
            <div className={styles.sectionHeading}><div><p className={styles.kicker}>02 / ALUR KERJA</p><h2 id="workflow-title">Catat. Pahami. <span>Tingkatkan.</span></h2></div><p>Bangun kebiasaan evaluasi.<br />Bukan sekadar mengejar transaksi berikutnya.</p></div>
            <div className={styles.steps}>{steps.map(({ icon: Icon, title, text }, i) => <article key={title}><div className={styles.stepTop}><Icon size={34} strokeWidth={1.3} /><span>0{i + 1}</span></div><h3>{title}</h3><p>{text}</p><Link href={i === 0 ? "/settings" : i === 1 ? "/terminal" : "/analitik"}> {i === 0 ? "Atur sinkronisasi" : i === 1 ? "Buka terminal" : "Lihat analitik"} <ArrowUpRight size={16} /></Link></article>)}</div>
          </section>

          <section className={`${styles.container} ${styles.principles}`} aria-label="Cakupan workspace"><div><strong>MT5</strong><span>Sumber data trading</span></div><div><strong>BUY / SELL / HOLD</strong><span>Jejak keputusan bot</span></div><div><strong>WIB</strong><span>Konteks waktu jurnal</span></div><div><strong>1 workspace</strong><span>Monitoring hingga evaluasi</span></div></section>

          <section id="faq" className={`${styles.container} ${styles.faqSection}`} aria-labelledby="faq-title"><div><p className={styles.kicker}>03 / SEBELUM MEMULAI</p><h2 id="faq-title">Kenali jurnal<br />trading Anda.</h2><p>Alat untuk memahami proses.<br />Bukan janji hasil trading.</p></div><div className={styles.faqs}>
            <details><summary>Apa itu Trading Journal?<span>+</span></summary><p>Trading Journal adalah workspace untuk memantau bot MT5, meninjau riwayat transaksi, membaca kalender PnL, dan mengevaluasi performa berdasarkan simbol maupun strategi.</p></details>
            <details><summary>Apakah aplikasi ini menjalankan trading AI?<span>+</span></summary><p>Aplikasi ini menampilkan aktivitas dan keputusan dari bot MT5 yang terhubung. Keputusan AI beserta confidence dan alasannya dicatat untuk ditinjau, bukan dihasilkan oleh landing page ini.</p></details>
            <details><summary>Bagaimana data diperbarui?<span>+</span></summary><p>Event bot diterima melalui live feed. Data MT5 dapat disinkronkan secara manual atau berkala melalui Pengaturan. Ketersediaan data bergantung pada konfigurasi integrasi dan terminal MT5 Anda.</p></details>
            <details><summary>Apakah angka di halaman ini hasil trading nyata?<span>+</span></summary><p>Tidak. Kartu di atas menggunakan data ilustrasi untuk menunjukkan jenis informasi yang tersedia. Dashboard menampilkan data dari integrasi Anda. Performa masa lalu tidak menjamin hasil di masa depan.</p></details>
          </div></section>

          <section className={`${styles.container} ${styles.finalCta}`}><div className={styles.eyebrow}><Radio size={15} /> A CLEARER VIEW STARTS HERE</div><h2>Setiap transaksi punya cerita.<br /><span>Mulai membacanya.</span></h2><p>Buka workspace Anda dan lihat trading dari perspektif yang lebih lengkap.</p><div className={styles.actions}><Link href="/dashboard" className={styles.primary}>Buka Dashboard <ArrowUpRight size={17} /></Link><Link href="/settings" className={styles.secondary}>Atur integrasi MT5 <ArrowRight size={16} /></Link></div></section>
        </main>
      </div>
      <footer className={`${styles.container} ${styles.footer}`}><Link href="/" className={styles.brand}><CandlestickChart size={24} /><span>trading<span className={styles.brandLight}>journal</span>.</span></Link><p>Jurnal yang jelas. Evaluasi yang terarah.</p><a href="#faq">Trading memiliki risiko <ArrowUpRight size={13} /></a><span>&copy; {new Date().getFullYear()} Trading Journal</span></footer>
    </div>
  );
}
