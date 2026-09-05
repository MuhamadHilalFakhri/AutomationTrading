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
  title: "Automation Trading — MT5 AI Bot",
  description: "Live journal untuk MT5 AI trading bot",
  icons: {
    icon: [{ url: "/LogoAT.png", type: "image/png" }],
    shortcut: "/LogoAT.png",
    apple: "/LogoAT.png",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="id" className={`${inter.variable} ${jetbrainsMono.variable} dark`} data-scroll-behavior="smooth">
      <body className="font-sans">
        {children}
        <Toaster
          position="bottom-right"
          toastOptions={{
            style: {
              background: "var(--card)",
              color: "var(--foreground)",
              border: "1px solid var(--border)",
              borderRadius: "15px",
              boxShadow: "none",
              fontFamily: "var(--font-inter), Inter, sans-serif",
            },
          }}
        />
      </body>
    </html>
  );
}
