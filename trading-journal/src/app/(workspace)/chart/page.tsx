import type { Metadata } from "next";
import { PageHeader } from "@/components/page-header";
import { ChartWorkspace } from "@/components/chart-workspace";

export const metadata: Metadata = {
  title: "Market Chart — Automation Trading",
  description: "Chart pasar real-time untuk forex, metal, crypto, dan indeks.",
};

export default function MarketChartPage() {
  return (
    <div className="text-foreground">
      <PageHeader
        title="Market Chart"
        subtitle="Pantau pergerakan harga dan analisis berbagai pair dalam satu workspace"
        className="mb-4"
      />
      <ChartWorkspace />
    </div>
  );
}
