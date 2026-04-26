import { NextRequest } from "next/server";

import { runAgent, type AgentRunEvent } from "@/lib/agent/runner";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type RunBody = {
  caseId?: string;
  apiKey?: string;
  baseUrl?: string;
  model?: string;
  maxIterations?: number;
  temperature?: number;
};

function eventToSse(event: AgentRunEvent): string {
  return `data: ${JSON.stringify(event)}\n\n`;
}

export async function POST(request: NextRequest) {
  let body: RunBody = {};
  try {
    body = (await request.json()) as RunBody;
  } catch {
    return new Response(JSON.stringify({ error: "Invalid JSON body" }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }

  const caseId = body.caseId || "";

  if (!caseId) {
    return new Response(JSON.stringify({ error: "caseId is required" }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }

  if (!body.apiKey) {
    return new Response(JSON.stringify({ error: "apiKey is required" }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }

  if (!body.model) {
    return new Response(JSON.stringify({ error: "model is required" }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }

  const encoder = new TextEncoder();
  const stream = new ReadableStream<Uint8Array>({
    async start(controller) {
      const send = (event: AgentRunEvent) => {
        try {
          controller.enqueue(encoder.encode(eventToSse(event)));
        } catch {
          /* controller may already be closed */
        }
      };

      const ping = setInterval(() => {
        try {
          controller.enqueue(encoder.encode(": ping\n\n"));
        } catch {
          /* ignore */
        }
      }, 15000);

      try {
        for await (const event of runAgent({
          caseId,
          apiKey: body.apiKey || "",
          baseUrl: body.baseUrl,
          model: body.model || "gpt-4o-mini",
          maxIterations: body.maxIterations,
          temperature: body.temperature,
        })) {
          send(event);
          if (event.type === "done") break;
        }
      } catch (err) {
        send({
          type: "error",
          error: (err as Error).message || "Unknown agent error",
        });
        send({ type: "done" });
      } finally {
        clearInterval(ping);
        try {
          controller.close();
        } catch {
          /* ignore */
        }
      }
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}
