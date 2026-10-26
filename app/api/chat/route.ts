import { NextRequest } from "next/server";
import { localPageIndexChat } from "@/lib/pageindex";
import { getRepoToc } from "@/lib/wiki";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { repo, messages } = body;

    if (!repo || typeof repo !== "string") {
      return new Response(JSON.stringify({ error: "Missing or invalid 'repo' parameter" }), {
        status: 400,
        headers: { "Content-Type": "application/json" },
      });
    }

    const toc = await getRepoToc(repo);
    if (!toc) {
      return new Response(JSON.stringify({ error: `Unknown repository: ${repo}` }), {
        status: 404,
        headers: { "Content-Type": "application/json" },
      });
    }

    if (!Array.isArray(messages) || messages.length === 0) {
      return new Response(JSON.stringify({ error: "Missing or invalid 'messages' parameter" }), {
        status: 400,
        headers: { "Content-Type": "application/json" },
      });
    }

    const backendUrl =
      process.env.NEXT_PUBLIC_API_URL ||
      process.env.BACKEND_API_URL ||
      "http://localhost:8000";

    // Attempt proxying to FastAPI backend first
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 2000);

      const backendResponse = await fetch(`${backendUrl}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo, messages }),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (backendResponse.ok && backendResponse.body) {
        return new Response(backendResponse.body, {
          headers: {
            "Content-Type": "text/event-stream; charset=utf-8",
            "Cache-Control": "no-cache, no-transform",
            Connection: "keep-alive",
            "X-Accel-Buffering": "no",
          },
        });
      }
    } catch {
      // Backend offline or unreachable — proceed to local PageIndex fallback
    }

    // Local PageIndex vectorless tree search and streaming
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      async start(controller) {
        try {
          for await (const { event, data } of localPageIndexChat(repo, messages)) {
            const chunk = `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
            controller.enqueue(encoder.encode(chunk));
          }
        } catch (err) {
          const errChunk = `event: error\ndata: ${JSON.stringify({ error: String(err) })}\n\n`;
          controller.enqueue(encoder.encode(errChunk));
        } finally {
          controller.close();
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
  } catch (err) {
    return new Response(
      JSON.stringify({ error: err instanceof Error ? err.message : "Internal error" }),
      {
        status: 500,
        headers: { "Content-Type": "application/json" },
      }
    );
  }
}
