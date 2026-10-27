import { NextRequest } from "next/server";

/** SSE headers shared by every stream this route returns. */
const SSE_HEADERS = {
  "Content-Type": "text/event-stream; charset=utf-8",
  "Cache-Control": "no-cache, no-transform",
  Connection: "keep-alive",
  "X-Accel-Buffering": "no",
} as const;

function backendBaseUrl(): string {
  return (
    process.env.NEXT_PUBLIC_API_URL ||
    process.env.BACKEND_API_URL ||
    "http://localhost:8000"
  );
}

/**
 * The ingestion pipeline lives in the FastAPI backend because that is where the
 * clone, bundle, synthesis, and PageIndex stages actually run. If the backend is
 * unreachable we report that; we never synthesize a wiki locally.
 *
 * An earlier version wrote invented pages to disk as a "demo fallback". That
 * published documentation for code nobody had read, which is worse than an
 * outage: it produced a wiki line describing services, brokers, and endpoints
 * the repository did not contain.
 */
function backendUnavailableStream(detail: string): Response {
  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    start(controller) {
      const payload = {
        step: "error",
        error:
          "Ingestion backend is unreachable, so no documentation was generated. " +
          "Start the backend (npm run dev:backend) and retry.",
        detail,
      };
      controller.enqueue(
        encoder.encode(`event: error\ndata: ${JSON.stringify(payload)}\n\n`)
      );
      controller.close();
    },
  });

  return new Response(stream, { headers: SSE_HEADERS });
}

async function proxyIngestion(
  path: string,
  body: Record<string, unknown>
): Promise<Response> {
  const backendUrl = backendBaseUrl();

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000);

    const backendResponse = await fetch(`${backendUrl}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (backendResponse.ok && backendResponse.body) {
      return new Response(backendResponse.body, { headers: SSE_HEADERS });
    }

    return backendUnavailableStream(
      `Backend responded ${backendResponse.status} ${backendResponse.statusText}`
    );
  } catch (error) {
    return backendUnavailableStream(String(error));
  }
}

async function handleGenerate(url: string, branch?: string, name?: string) {
  return proxyIngestion("/api/generate", { url, branch, name });
}

async function handleGenerateSystem(
  systemName: string,
  repos: Array<{ name: string; url: string; branch?: string }>,
  displayName?: string
) {
  const dispName =
    displayName ||
    systemName.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

  // Same rule as single-repo ingestion: the mesh is only ever built from
  // repositories the backend actually cloned and read.
  return proxyIngestion("/api/generate/system", {
    system_name: systemName,
    repos,
    display_name: dispName,
  });
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();

    // Multi-Repo Microservice System request
    if (body.system_name && Array.isArray(body.repos)) {
      return handleGenerateSystem(body.system_name, body.repos, body.display_name);
    }

    // Single repository request
    const url = body.url;
    const branch = body.branch;
    // Optional: overrides the wiki line name, which otherwise is qualified
    // with the repository's owner to avoid same-name collisions.
    const name = typeof body.name === "string" ? body.name : undefined;

    if (!url || typeof url !== "string") {
      return new Response(
        JSON.stringify({ error: "Missing or invalid 'url' or 'system_name' parameter" }),
        { status: 400, headers: { "Content-Type": "application/json" } }
      );
    }

    return handleGenerate(url, branch, name);
  } catch {
    return new Response(
      JSON.stringify({ error: "Invalid JSON request body" }),
      { status: 400, headers: { "Content-Type": "application/json" } }
    );
  }
}

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const url = searchParams.get("url");
  const branch = searchParams.get("branch") || undefined;
  const name = searchParams.get("name") || undefined;

  if (!url) {
    return new Response(
      JSON.stringify({ error: "Missing 'url' query parameter" }),
      { status: 400, headers: { "Content-Type": "application/json" } }
    );
  }

  return handleGenerate(url, branch, name);
}
