import { NextRequest } from "next/server";

import { getApiBaseUrl, getTenantId } from "@/lib/api/shared";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

type Params = {
  params: Promise<{ runId: string }>;
};

export async function GET(request: NextRequest, { params }: Params) {
  const { runId } = await params;
  const afterCursor = request.nextUrl.searchParams.get("after_cursor");
  const query = afterCursor ? `?after_cursor=${encodeURIComponent(afterCursor)}` : "";

  const upstream = await fetch(`${getApiBaseUrl()}/runs/${runId}/stream${query}`, {
    headers: {
      "x-tenant-id": getTenantId(),
      Accept: "text/event-stream"
    },
    cache: "no-store"
  });

  if (!upstream.ok || !upstream.body) {
    const detail = await upstream.text();
    return new Response(`SSE upstream failed: ${detail}`, { status: upstream.status || 502 });
  }

  return new Response(upstream.body, {
    status: 200,
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive"
    }
  });
}
