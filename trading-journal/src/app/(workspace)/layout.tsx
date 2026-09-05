import { Sidebar } from "@/components/sidebar";

export default function WorkspaceLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <Sidebar />
      <main className="min-h-screen pt-16 transition-[padding] duration-200 ease-out lg:pl-[var(--sidebar-width)] lg:pt-0">
        <div className="mx-auto max-w-[1440px] px-4 py-5 sm:px-6 sm:py-7 lg:px-8">{children}</div>
      </main>
    </>
  );
}
