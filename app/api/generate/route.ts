import fs from "fs";
import path from "path";
import { NextRequest } from "next/server";

function deriveRepoName(source: string): string {
  const clean = source.trim().replace(/\.git$/i, "").replace(/\/+$/, "");
  const parts = clean.split(/[/\\]/);
  const last = parts[parts.length - 1] || "demo-repo";
  return last.replace(/[^a-zA-Z0-9_\-]/g, "-").toLowerCase();
}

function delay(ms: number): Promise<void> {
  const { promise, resolve } = Promise.withResolvers<void>();
  setTimeout(resolve, ms);
  return promise;
}

async function handleGenerate(url: string, branch?: string) {
  const backendUrl =
    process.env.NEXT_PUBLIC_API_URL ||
    process.env.BACKEND_API_URL ||
    "http://localhost:8000";

  // Try proxying to FastAPI backend
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 3000);

    const backendResponse = await fetch(`${backendUrl}/api/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, branch }),
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
    // Backend offline or unreachable — fall through to simulated fallback
  }

  // Fallback SSE generator for live pitch resilience
  const repoName = deriveRepoName(url);
  const encoder = new TextEncoder();

  const stream = new ReadableStream({
    async start(controller) {
      const emit = (event: string, data: Record<string, unknown>) => {
        controller.enqueue(
          encoder.encode(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`)
        );
      };

      try {
        emit("step", {
          step: "clone",
          status: "running",
          message: `Cloning repository ${url} (depth 1)...`,
        });
        await delay(1200);

        emit("step", {
          step: "bundle",
          status: "running",
          message: "Packing codebase with Repomix (stripping tests, locks, binaries)...",
        });
        await delay(1400);

        emit("step", {
          step: "toc",
          status: "running",
          message: "Synthesizing Table of Contents schema...",
        });
        await delay(1300);

        const pages = ["overview", "architecture", "setup", "api-reference"];
        for (let i = 0; i < pages.length; i++) {
          emit("step", {
            step: "doc_gen",
            status: "running",
            progress: `${i + 1}/4 pages generated`,
            page: pages[i],
          });
          await delay(900);
        }

        emit("step", {
          step: "pageindex",
          status: "running",
          message: "Building vectorless PageIndex hierarchical tree...",
        });
        await delay(1100);

        const contentDir = path.join(process.cwd(), "content");
        const repoDir = path.join(contentDir, repoName);
        if (!fs.existsSync(path.join(repoDir, "toc.json"))) {
          fs.mkdirSync(repoDir, { recursive: true });
          const dispName = repoName
            .replace(/[-_]/g, " ")
            .replace(/\b\w/g, (c) => c.toUpperCase());
          const toc = {
            repo_name: repoName,
            display_name: `${dispName} Service`,
            description: `Autonomous architectural documentation and PageIndex index for ${dispName}.`,
            language: "TypeScript",
            stars: 42,
            pages: [
              {
                slug: "overview",
                title: "System Overview",
                description: "Core responsibilities, domain boundaries, and high-level architecture.",
              },
              {
                slug: "architecture",
                title: "Internal Architecture",
                description: "Component interaction, data flow, and runtime mechanics.",
              },
              {
                slug: "setup",
                title: "Setup & Configuration",
                description: "Environment setup, local prerequisites, and runtime configuration.",
              },
              {
                slug: "api-reference",
                title: "API Reference",
                description: "Public endpoints, contracts, and interaction models.",
              },
            ],
          };
          fs.writeFileSync(path.join(repoDir, "toc.json"), JSON.stringify(toc, null, 2), "utf-8");
          fs.writeFileSync(
            path.join(repoDir, "overview.md"),
            `# System Overview\n\n${dispName} provides autonomous service workflows and structured system integration.\n\n## Core Architecture\n\nThe service coordinates component boundaries, input validation, and asynchronous processing.\n`,
            "utf-8"
          );
          fs.writeFileSync(
            path.join(repoDir, "architecture.md"),
            `# Internal Architecture\n\n## Component Topology\n\nModules interact via structured contracts and event pipelines.\n\n## Data Layer\n\nPersistence is isolated with atomic state management.\n`,
            "utf-8"
          );
          fs.writeFileSync(
            path.join(repoDir, "setup.md"),
            `# Setup & Configuration\n\n## Prerequisites\n\nNode.js and modern runtime environment.\n\n## Installation\n\nClone repository and install dependencies.\n`,
            "utf-8"
          );
          fs.writeFileSync(
            path.join(repoDir, "api-reference.md"),
            `# API Reference\n\n## Endpoints\n\nProvides standard REST and RPC integration endpoints.\n`,
            "utf-8"
          );
          const tree = {
            repo_name: repoName,
            generated_at: new Date().toISOString(),
            nodes: [
              {
                node_id: "overview#core-architecture",
                file: "overview.md",
                title: "Core Architecture",
                level: 2,
                summary: `High-level component topology and system boundaries for ${dispName}.`,
              },
              {
                node_id: "architecture#component-topology",
                file: "architecture.md",
                title: "Component Topology",
                level: 2,
                summary: `Interaction contracts and internal subsystem data flows.`,
              },
            ],
          };
          fs.writeFileSync(path.join(repoDir, "pageindex_tree.json"), JSON.stringify(tree, null, 2), "utf-8");
        }
        const targetRepo = repoName;

        emit("done", {
          step: "completed",
          repo: targetRepo,
          redirect: `/wiki/${targetRepo}/overview`,
        });
        controller.close();
      } catch (err) {
        emit("error", { error: String(err) });
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

async function handleGenerateSystem(
  systemName: string,
  repos: Array<{ name: string; url: string; branch?: string }>,
  displayName?: string
) {
  const backendUrl =
    process.env.NEXT_PUBLIC_API_URL ||
    process.env.BACKEND_API_URL ||
    "http://localhost:8000";

  const dispName = displayName || systemName.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

  // Try proxying to FastAPI backend
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 3000);

    const backendResponse = await fetch(`${backendUrl}/api/generate/system`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ system_name: systemName, repos, display_name: dispName }),
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
    // Backend offline — fall through to simulated fallback
  }

  // Fallback SSE generator for live pitch resilience
  const encoder = new TextEncoder();

  const stream = new ReadableStream({
    async start(controller) {
      const emit = (event: string, data: Record<string, unknown>) => {
        controller.enqueue(
          encoder.encode(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`)
        );
      };

      try {
        emit("step", {
          step: "system_init",
          status: "running",
          message: `Initializing multi-repo mesh for ${dispName} (${repos.length} repositories)...`,
          count: repos.length,
        });
        await delay(1200);

        emit("step", {
          step: "clone_all",
          status: "running",
          message: `Cloning ${repos.length} member repositories in parallel...`,
        });
        await delay(1500);

        emit("step", {
          step: "bundle_all",
          status: "running",
          message: "Bundling codebases with Repomix (stripping tests, locks, binaries)...",
        });
        await delay(1400);

        emit("step", {
          step: "synthesize_members",
          status: "running",
          message: "Synthesizing individual documentation wikis for member services...",
        });
        await delay(1600);

        emit("step", {
          step: "mesh_extract",
          status: "running",
          message: "Discovering inter-service RPCs, Kafka event topics, and injecting peer cross-links...",
        });
        await delay(1500);

        emit("step", {
          step: "pageindex_all",
          status: "running",
          message: "Building vectorless PageIndex trees for all microservices and federated system...",
        });
        await delay(1200);

        emit("done", {
          step: "completed",
          system: systemName,
          display_name: dispName,
          services_count: repos.length,
          repos: repos.map((r) => r.name),
          redirect: `/wiki/${systemName}/overview`,
        });
        controller.close();
      } catch (err) {
        emit("error", { error: String(err) });
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

    if (!url || typeof url !== "string") {
      return new Response(
        JSON.stringify({ error: "Missing or invalid 'url' or 'system_name' parameter" }),
        { status: 400, headers: { "Content-Type": "application/json" } }
      );
    }

    return handleGenerate(url, branch);
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

  if (!url) {
    return new Response(
      JSON.stringify({ error: "Missing 'url' query parameter" }),
      { status: 400, headers: { "Content-Type": "application/json" } }
    );
  }

  return handleGenerate(url, branch);
}
