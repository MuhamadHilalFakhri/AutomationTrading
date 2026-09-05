import { Sidebar } from "@/components/sidebar";
import { Toaster } from "sonner";
import { Inter, JetBrains_Mono } from "next/font/google";
import type { Metadata } from "next";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Trading Journal — MT5 AI Bot",
  description: "Live journal untuk MT5 AI trading bot",
  icons: {
    icon: [{ url: "/icon-32.png", sizes: "32x32", type: "image/png" }],
    apple: "/icon-256.png",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="id" className={`${inter.variable} ${jetbrainsMono.variable} dark`} data-scroll-behavior="smooth">
      <body className="font-sans">
        <Sidebar />
        <main className="min-h-screen pt-16 transition-[padding] duration-200 ease-out lg:pl-[var(--sidebar-width)] lg:pt-0">
          <div className="mx-auto max-w-[1440px] px-4 py-5 sm:px-6 sm:py-7 lg:px-8">{children}</div>
        </main>
        <Toaster
          position="bottom-right"
          richColors
          toastOptions={{
            style: {
              background: "#172033",
              color: "#eef2ff",
              border: "1px solid #334155",
            },
          }}
        />
      </body>
    </html>
  );
}
