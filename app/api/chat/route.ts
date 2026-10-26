import { encodeEvent } from "@/lib/chat";
import type { ChatStreamEvent } from "@/lib/chat";
import { composeLocalAnswer, routeQuestion } from "@/lib/pageindex";
import type { IndexedSection } from "@/lib/pageindex";
import { getRepoToc } from "@/lib/wiki";

interface ChatRequestBody {
  repo?: unknown;
  messages?: unknown;
}

interface IncomingMessage {
  role: "user" | "assistant";
  content: string;
}

function readMessages(value: unknown): IncomingMessage[] {
  if (!Array.isArray(value)) return [];
  return value.flatMap((entry) => {
    if (typeof entry !== "object" || entry === null) return [];
    const { role, content } = entry as { role?: unknown; content?: unknown };
    if (role !== "user" && role !== "assistant") return [];
    if (typeof content !== "string" || content.trim() === "") return [];
    return [{ role, content: content.trim() }];
  });
}

/**
 * The reasoning service, when one is configured, owns the whole protocol: it
 * decides which nodes to open and writes the prose. This build has no such
 * service, so the request falls back to the local reader below rather than
 * failing — the demo has to survive a cold backend.
 */
async function streamFromModel(
  baseUrl: string,
  repo: string,
  messages: IncomingMessage[],
  send: (event: ChatStreamEvent) => void
): Promise<boolean> {
  const response = await fetch(`${baseUrl.replace(/\/$/, "")}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify({ repo, messages }),
    signal: AbortSignal.timeout(20_000),
  }).catch(() => null);

  if (!response?.ok || !response.body) return false;

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let sawEvent = false;

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let split = buffer.indexOf("\n\n");
    while (split >= 0) {
      const frame = buffer.slice(0, split);
      buffer = buffer.slice(split + 2);
      const data = frame
        .split("\n")
        .filter((line) => line.startsWith("data:"))
        .map((line) => line.slice(5).trimStart())
        .join("\n");
      if (data) {
        try {
          const event = JSON.parse(data) as ChatStreamEvent;
          if (event && typeof event === "object" && "type" in event) {
            // Normalise the service's framing onto the surface's contract.
            send(event);
            sawEvent = true;
          }
        } catch {
          // A malformed frame is not worth failing the whole answer over.
        }
      }
      split = buffer.indexOf("\n\n");
    }
  }

  return sawEvent;
}

/**
 * Emits the local answer as the same event stream the model would emit, so the
 * client never branches on which engine replied — it only labels the result.
 */
async function streamLocalAnswer(
  repo: string,
  question: string,
  send: (event: ChatStreamEvent) => void
) {
  const routed = await routeQuestion(repo, question);
  if (!routed) {
    send({ type: "error", message: "No page index on disk for this repository." });
    return;
  }

  const { sections, steps, matched } = routed;
  send({ type: "step", step: "Reading the page index", detail: `${repo}/pageindex_tree.json` });
  for (const step of steps) send({ type: "step", ...step });

  const citations = sections.map((section: IndexedSection) => section.citation);
  if (citations.length > 0) send({ type: "nodes", nodes: citations });

  const { answer } = composeLocalAnswer(question, sections, matched);
  send({ type: "step", step: "Quoting the sections", detail: "verbatim markdown, no rewriting" });

  // Stream in word-aligned chunks: never half a word, never a whole paragraph
  // at once. The reader sees the answer being read out, not pasted in.
  const words = answer.match(/\n|[^\s\n]+\s*|\s+/g) ?? [answer];
  const chunks: string[] = [];
  let pending = "";
  for (const word of words) {
    pending += word;
    if (pending.length >= 48 || word === "\n") {
      chunks.push(pending);
      pending = "";
    }
  }
  if (pending) chunks.push(pending);
  for (const delta of chunks) send({ type: "token", delta });
  send({ type: "done", engine: "local" });
}

export async function POST(request: Request) {
  let body: ChatRequestBody;
  try {
    body = (await request.json()) as ChatRequestBody;
  } catch {
    return Response.json({ error: "Request body must be JSON." }, { status: 400 });
  }

  const repo = typeof body.repo === "string" ? body.repo : "";
  const messages = readMessages(body.messages);
  const question = [...messages].reverse().find((message) => message.role === "user");

  if (!repo) {
    return Response.json({ error: "A repository is required." }, { status: 400 });
  }
  if (!question) {
    return Response.json({ error: "A user message is required." }, { status: 400 });
  }

  const toc = await getRepoToc(repo);
  if (!toc) {
    return Response.json({ error: `Unknown repository: ${repo}` }, { status: 404 });
  }

  const encoder = new TextEncoder();
  const engine = typeof process.env.ROUTER_API_BASE === "string" ? process.env.ROUTER_API_BASE : "";

  const stream = new ReadableStream<Uint8Array>({
    async start(controller) {
      let closed = false;
      const send = (event: ChatStreamEvent) => {
        if (closed) return;
        controller.enqueue(encoder.encode(encodeEvent(event)));
      };

      send({ type: "step", step: "Selecting the line", detail: `${toc.display_name} · ${toc.pages.length} pages` });

      try {
        if (engine) {
          const answered = await streamFromModel(engine, repo, messages, send);
          if (answered) return;
          send({
            type: "step",
            step: "Reasoning service unreachable",
            detail: "falling back to the local PageIndex reader",
          });
        }
        await streamLocalAnswer(repo, question.content, send);
      } catch (error) {
        send({
          type: "error",
          message: error instanceof Error ? error.message : "The answer stopped unexpectedly.",
        });
      } finally {
        closed = true;
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
}
