import { NextRequest } from "next/server";

function backendBaseUrl(): string {
  return (
    process.env.NEXT_PUBLIC_API_URL ||
    process.env.BACKEND_API_URL ||
    "http://localhost:8000"
  );
}

/**
 * Ref discovery for the ingest form's branch picker.
 *
 * Listing refs runs `git ls-remote` on the backend, which is where git and the
 * network live. Nothing is cloned: this answers "what can I check out?" before
 * the reader commits to an ingestion run.
 */
export async function GET(req: NextRequest) {
  const url = req.nextUrl.searchParams.get("url");
  if (!url || !url.trim()) {
    return Response.json({ error: "Missing 'url' query parameter" }, { status: 400 });
  }

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 25000);

    const response = await fetch(
      `${backendBaseUrl()}/api/refs?url=${encodeURIComponent(url.trim())}`,
      { signal: controller.signal, cache: "no-store" }
    );
    clearTimeout(timeoutId);

    if (!response.ok) {
      // A private repo or a typo is expected here; the form shows the message
      // and falls back to a plain text field rather than blocking ingestion.
      const body = await response.json().catch(() => null);
      const detail =
        (body && (body.detail || body.error)) ||
        `Backend responded ${response.status}`;
      return Response.json({ error: String(detail) }, { status: response.status });
    }

    return Response.json(await response.json());
  } catch (error) {
    return Response.json(
      { error: "Could not reach the backend to list refs", detail: String(error) },
      { status: 503 }
    );
  }
}
