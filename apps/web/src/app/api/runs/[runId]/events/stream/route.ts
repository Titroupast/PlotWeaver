import { NextRequest } from "next/server";

import { getApiBaseUrl, getTenantId, parseJsonOrThrow } from "@/lib/api/shared";
import type { Run, RunEvent } from "@/lib/api/types";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

type Params = {
  params: Promise<{ runId: string }>;
};

function sseLine(event: string, data: unknown): string {
  return `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
}

async function fetchRun(runId: string): Promise<Run> {
  const res = await fetch(`${getApiBaseUrl()}/runs/${runId}`, {
    headers: {
      "x-tenant-id": getTenantId()
    },
    cache: "no-store"
  });
  return parseJsonOrThrow<Run>(res);
}

async function fetchEvents(runId: string): Promise<RunEvent[]> {
  const res = await fetch(`${getApiBaseUrl()}/runs/${runId}/events?limit=200`, {
    headers: {
      "x-tenant-id": getTenantId()
    },
    cache: "no-store"
  });
  return parseJsonOrThrow<RunEvent[]>(res);
}

export async function GET(_request: NextRequest, { params }: Params) {
  const { runId } = await params;
  const encoder = new TextEncoder();
  const seenEventIds = new Set<string>();
  let closed = false;

  const stream = new ReadableStream<Uint8Array>({
    cancel() {
      closed = true;
    },
    async start(controller) {
      const close = () => {
        if (!closed) {
          closed = true;
          controller.close();
        }
      };

      controller.enqueue(encoder.encode(sseLine("connected", { runId })));

      const tick = async () => {
        if (closed) return;
        try {
          const [run, events] = await Promise.all([fetchRun(runId), fetchEvents(runId)]);
          const deltas = events.filter((e) => {
            if (seenEventIds.has(e.id)) {
              return false;
            }
            seenEventIds.add(e.id);
            return true;
          });

          for (const event of deltas) {
            controller.enqueue(encoder.encode(sseLine("run-event", event)));
          }

          controller.enqueue(encoder.encode(sseLine("run-state", run)));

          if (["SUCCEEDED", "FAILED", "DEAD_LETTER", "CANCELLED"].includes(run.state)) {
            controller.enqueue(encoder.encode(sseLine("done", { state: run.state })));
            close();
            return;
          }
        } catch (error) {
          controller.enqueue(
            encoder.encode(
              sseLine("error", {
                message: error instanceof Error ? error.message : "stream fetch failed"
              })
            )
          );
        }
        if (!closed) {
          setTimeout(tick, 2000);
        }
      };

      tick();
    }
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive"
    }
  });
}
