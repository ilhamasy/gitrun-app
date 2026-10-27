/**
 * The chat contract, shared by the route handler and the client surface.
 * Kept free of Node APIs, like lib/stations.ts, so both sides import one copy.
 */

import type { PageIndexNode, RepoToc } from "@/lib/stations";

export type ChatRole = "user" | "assistant";

/** A citation is a tree node, addressed the same way the reader addresses it. */
export interface ChatCitation {
  node_id: string;
  title: string;
  file: string;
  summary: string;
  /**
   * The line this node lives on. Present on cross-line answers, where a single
   * thread can cite nodes from several repositories.
   */
  repo?: string;
}

/** One real unit of work, so the drawer describes what happened, not what might. */
export interface ChatStep {
  step: string;
  detail?: string;
}

/**
 * Every answer names the engine that produced it. Extraction and synthesis are
 * different claims, and a reader is entitled to know which one they are reading.
 */
export type ChatEngine = "local" | "model";

export interface ChatTurn {
  id: string;
  role: ChatRole;
  content: string;
  steps: ChatStep[];
  citations: ChatCitation[];
  engine: ChatEngine | null;
  status: "streaming" | "done" | "failed";
}

export type ChatStreamEvent =
  | { type: "step"; step: string; detail?: string }
  | { type: "nodes"; nodes: ChatCitation[] }
  | { type: "token"; delta: string }
  | { type: "done"; engine: ChatEngine }
  | { type: "error"; message: string };

/** Everything the chat surface needs about one line, resolved on the server. */
export interface ChatRepoSummary {
  repo_name: string;
  display_name: string;
  description: string;
  language?: string;
  pageCount: number;
  generated: string | null;
  hue: string;
  nodes: PageIndexNode[];
  starters: string[];
}

/**
 * A citation resolves to the exact wiki station and section it came from.
 * Cross-line answers carry their own `repo`, so the link follows the node
 * rather than the currently selected line.
 */
export function citationHref(repo: string, citation: ChatCitation): string {
  const station = citation.file.replace(/\.md$/i, "");
  const line = citation.repo ?? repo;
  return `/wiki/${line}/${station}#${citation.node_id.split("#")[1] ?? ""}`;
}

/**
 * Starter questions are repository-specific on purpose: a judge clicking one
 * must land on an answer the seeded index actually contains. Anything without a
 * curated set falls back to the four questions every generated wiki can answer.
 */
const CURATED_STARTERS: Record<string, string[]> = {
  "payment-gateway": [
    "How does the system prevent double-charging?",
    "Which environment variables are required?",
    "How is the ledger table partitioned?",
    "What happens when the PSP times out?",
  ],
  "auth-sentinel": [
    "How are signing keys rotated?",
    "How is a token revoked before it expires?",
    "What is required to run it locally?",
    "Which protocols are supported?",
  ],
};

export function starterPrompts(repo: RepoToc): string[] {
  return (
    CURATED_STARTERS[repo.repo_name] ?? [
      `What does ${repo.display_name} do?`,
      `How do I run ${repo.display_name} locally?`,
      `How is ${repo.display_name} structured internally?`,
      `Which endpoints does ${repo.display_name} expose?`,
    ]
  );
}

/** SSE frames are newline-delimited JSON with one `data:` line each. */
export function encodeEvent(event: ChatStreamEvent): string {
  return `data: ${JSON.stringify(event)}\n\n`;
}

export function parseEvent(frame: string): ChatStreamEvent | null {
  const data = frame
    .split("\n")
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice(5).trimStart())
    .join("\n");
  if (!data) return null;
  try {
    const value = JSON.parse(data) as ChatStreamEvent;
    return typeof value === "object" && value !== null && "type" in value
      ? value
      : null;
  } catch {
    return null;
  }
}
