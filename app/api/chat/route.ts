import { NextRequest } from "next/server";
import { localCorpusChat, localPageIndexChat } from "@/lib/pageindex";
import { getAllRepos, getRepoToc } from "@/lib/wiki";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { repo, repos, messages } = body;

    if (!Array.isArray(messages) || messages.length === 0) {
      return new Response(JSON.stringify({ error: "Missing or invalid 'messages' parameter" }), {
        status: 400,
        headers: { "Content-Type": "application/json" },
      });
    }

    /**
     * Scope is optional by design. With no `repo` and no `repos`, the question
     * is searched against every line on the board, so a user can hunt for a
     * problem without first knowing which repository owns it. Naming a line
     * narrows the search to that tree.
     */
    let scope: string[] | null = null;
    if (typeof repo === "string" && repo.trim()) {
      scope = [repo.trim()];
    } else if (Array.isArray(repos) && repos.length > 0) {
      const named = repos.filter(
        (entry): entry is string => typeof entry === "string" && entry.trim().length > 0
      );
      if (named.length > 0) scope = named;
    }

    if (scope) {
      for (const name of scope) {
        const toc = await getRepoToc(name);
        if (!toc) {
          return new Response(
            JSON.stringify({ error: `Unknown repository: ${name}` }),
            { status: 404, headers: { "Content-Type": "application/json" } }
          );
        }
      }
    } else {
      const all = await getAllRepos();
      const indexed = all.map((entry) => entry.repo_name);
      if (indexed.length === 0) {
        return new Response(
          JSON.stringify({ error: "No lines on the board to search yet." }),
          { status: 404, headers: { "Content-Type": "application/json" } }
        );
      }
      scope = indexed;
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
        body: JSON.stringify({
          repo: scope.length === 1 ? scope[0] : undefined,
          repos: scope,
          messages,
        }),
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
          const streamGenerator =
            scope.length === 1
              ? localPageIndexChat(scope[0], messages)
              : localCorpusChat(scope, messages);

          for await (const { event, data } of streamGenerator) {
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
