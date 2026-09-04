import { Sidebar } from "@/components/sidebar";
import { Toaster } from "sonner";
import { Inter, JetBrains_Mono } from "next/font/google";
import type { Metadata } from "next";
import "./globals.css";

const inter = Inter({
  variable: "--font-sans",
  subsets: ["latin"],
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-geist-mono",
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
    <html lang="id" className="dark">
      <body className={`${inter.variable} ${jetbrainsMono.variable} h-full antialiased bg-black text-zinc-100`}>
        <Sidebar />
        <main className="min-h-screen pt-14 lg:pt-0 lg:pl-60">
          <div className="mx-auto max-w-7xl p-4 sm:p-6">{children}</div>
        </main>
        <Toaster
          position="bottom-right"
          toastOptions={{
            style: {
              background: "#18181b",
              color: "#e4e4e7",
              border: "1px solid #27272a",
            },
          }}
        />
      </body>
    </html>
  );
}
