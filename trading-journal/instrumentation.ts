export async function register() {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    const { initAutoSync } = await import("@/lib/auto-sync");
    initAutoSync();
  }
}
