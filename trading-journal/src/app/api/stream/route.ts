import { listEvents } from "@/lib/journal";

export const dynamic = "force-dynamic";

// Server-Sent Events: stream new events to the browser (live terminal).
export async function GET(req: Request) {
  const encoder = new TextEncoder();

  const stream = new ReadableStream({
    async start(controller) {
      let lastId = 0;
      let closed = false;

      // catch-up: send the last 30 events first
      const recent = await listEvents({ limit: 30 });
      for (const ev of recent.reverse()) {
        controller.enqueue(encoder.encode(`data: ${JSON.stringify(ev)}\n\n`));
        lastId = Math.max(lastId, ev.id);
      }

      const tick = async () => {
        if (closed) return;
        try {
          const rows = await listEvents({ limit: 100, sinceId: lastId });
          for (const ev of rows) {
            controller.enqueue(encoder.encode(`data: ${JSON.stringify(ev)}\n\n`));
            lastId = Math.max(lastId, ev.id);
          }
        } catch {
          // db busy — skip this tick
        }
      };

      const interval = setInterval(tick, 2000);

      // close on client disconnect
      req.signal.addEventListener("abort", () => {
        closed = true;
        clearInterval(interval);
        try { controller.close(); } catch { /* already closed */ }
      });
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
    },
  });
}
