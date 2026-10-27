"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Eraser } from "lucide-react";

import { parseEvent } from "@/lib/chat";
import type {
  ChatCitation,
  ChatEngine,
  ChatRepoSummary,
  ChatStep,
  ChatStreamEvent,
  ChatTurn,
} from "@/lib/chat";
import { AnswerEntry } from "@/components/chat/answer-entry";
import { StarterPrompts } from "@/components/chat/starter-prompts";
import { QuestionEntry } from "@/components/chat/question-entry";
import { ChatInput } from "@/components/chat/chat-input";

/** `null` means "search every line": the default for finding problems. */
type Scope = string | null;

interface ChatContainerProps {
  lines: ChatRepoSummary[];
  initialRepo: string | null;
}

function newTurn(role: ChatTurn["role"], content: string): ChatTurn {
  return {
    id: `${role}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    role,
    content,
    steps: [],
    citations: [],
    engine: null,
    status: "done",
  };
}

/**
 * The thread.
 *
 * Scope defaults to the whole board, because looking for a problem usually
 * means not knowing which line owns it. A reader who already knows where to
 * look can narrow the search to one line; the header always states which scope
 * the current thread is searching.
 */
export function ChatContainer({ lines, initialRepo }: ChatContainerProps) {
  const router = useRouter();
  const [scope, setScope] = useState<Scope>(initialRepo);
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const endRef = useRef<HTMLDivElement | null>(null);

  const activeLine =
    scope === null ? null : lines.find((entry) => entry.repo_name === scope) ?? null;
  const scopeLabel = activeLine ? activeLine.display_name : "All lines";
  const nodeCount = activeLine
    ? activeLine.nodes.length
    : lines.reduce((total, entry) => total + entry.nodes.length, 0);
  const pageCount = activeLine
    ? activeLine.pageCount
    : lines.reduce((total, entry) => total + entry.pageCount, 0);

  /**
   * Narrowing keeps the curated questions for that line. The whole-board scope
   * gets cross-cutting questions instead, which is the point of searching every
   * project: comparing services and finding problems that span lines.
   */
  const scopePrompts = activeLine
    ? activeLine.starters
    : [
        "Which services talk to each other, and over what?",
        "Where is the same responsibility implemented more than once?",
        "Which service has no documented health check?",
        "Where do these services disagree on configuration or contracts?",
      ];

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end", behavior: "smooth" });
  }, [turns]);

  useEffect(() => () => abortRef.current?.abort(), []);

  const selectScope = useCallback(
    (next: string) => {
      const nextScope: Scope = next === "" ? null : next;
      if (nextScope === scope) return;
      abortRef.current?.abort();
      setScope(nextScope);
      setTurns([]);
      setError(null);
      setStreaming(false);

      // Keep the URL honest so a narrowed search can be shared or bookmarked.
      const url = new URL(window.location.href);
      if (nextScope === null) {
        url.searchParams.delete("repo");
      } else {
        url.searchParams.set("repo", nextScope);
      }
      window.history.replaceState(null, "", url);
      if (nextScope !== null) router.refresh();
    },
    [scope, router]
  );

  const ask = useCallback(
    async (question: string) => {
      const text = question.trim();
      if (!text || streaming) return;

      const asked = newTurn("user", text);
      const answer: ChatTurn = {
        ...newTurn("assistant", ""),
        status: "streaming",
      };
      const history = [...turns, asked];
      setTurns([...history, answer]);
      setError(null);
      setStreaming(true);

      const patch = (update: (turn: ChatTurn) => ChatTurn) =>
        setTurns((current) =>
          current.map((turn) => (turn.id === answer.id ? update(turn) : turn))
        );

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const response = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            // Omit `repo` entirely for the whole-board search; the backend
            // treats an absent scope as "every indexed line".
            repo: scope ?? undefined,
            messages: history.map((turn) => ({
              role: turn.role,
              content: turn.content,
            })),
          }),
          signal: controller.signal,
        });

        if (!response.ok || !response.body) {
          const payload = (await response.json().catch(() => null)) as
            | { error?: string }
            | null;
          throw new Error(payload?.error ?? `The service replied ${response.status}.`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        for (;;) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });

          let split = buffer.indexOf("\n\n");
          while (split >= 0) {
            const frame = buffer.slice(0, split);
            buffer = buffer.slice(split + 2);
            split = buffer.indexOf("\n\n");

            const event = parseEvent(frame);
            if (!event) continue;
            applyEvent(event, patch);
          }
        }

        patch((turn) =>
          turn.status === "streaming" ? { ...turn, status: "done" } : turn
        );
      } catch (cause) {
        if (controller.signal.aborted) {
          patch((turn) => ({ ...turn, status: "done" }));
        } else {
          const message =
            cause instanceof Error ? cause.message : "The answer stopped unexpectedly.";
          setError(message);
          patch((turn) => ({ ...turn, status: "failed" }));
        }
      } finally {
        abortRef.current = null;
        setStreaming(false);
      }
    },
    [scope, streaming, turns]
  );

  function stop() {
    abortRef.current?.abort();
    setStreaming(false);
  }

  function clear() {
    abortRef.current?.abort();
    setTurns([]);
    setError(null);
    setStreaming(false);
  }

  if (lines.length === 0) return null;

  const scopeHue = activeLine?.hue ?? "neutral";

  return (
    <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_20rem] lg:gap-10">
      <section aria-label="Conversation" className="min-w-0">
        <div className="flex flex-wrap items-end justify-between gap-x-4 gap-y-2 border-b border-hairline pb-3">
          <label className="flex min-w-0 flex-col gap-1">
            <span className="label-wide text-ink-3">Search scope</span>
            <select
              value={scope ?? ""}
              onChange={(event) => selectScope(event.target.value)}
              className="h-10 max-w-full border border-hairline-strong bg-surface px-2.5 font-[family-name:var(--font-signage)] text-[0.9375rem] font-semibold tracking-[0.04em] text-ink"
            >
              <option value="">All lines — {lines.length} wikis</option>
              {lines.map((entry) => (
                <option key={entry.repo_name} value={entry.repo_name}>
                  {entry.display_name}
                </option>
              ))}
            </select>
          </label>

          <div className="flex items-center gap-3">
            <span className="data text-ink-3">
              {nodeCount} nodes · {pageCount} {pageCount === 1 ? "page" : "pages"}
            </span>
            {turns.length > 0 && (
              <button type="button" onClick={clear} className="btn btn-quiet h-9 px-3">
                <Eraser className="size-3.5" aria-hidden="true" />
                Clear thread
              </button>
            )}
          </div>
        </div>

        <p className="mt-3 max-w-[64ch] text-[0.9375rem] leading-relaxed text-ink-2">
          {activeLine ? (
            <>
              Searching <strong className="font-semibold text-ink">{scopeLabel}</strong> only.
              Choose <em>All lines</em> to search every project.
            </>
          ) : (
            <>
              Searching{" "}
              <strong className="font-semibold text-ink">
                all {lines.length} lines
              </strong>{" "}
              at once. Answers may cite sections from more than one project, and
              every citation names the line it came from.
            </>
          )}
        </p>

        {turns.length === 0 ? (
          <StarterPrompts
            repo={scope ?? "all-lines"}
            displayName={scopeLabel}
            prompts={scopePrompts}
            onPick={ask}
            global={activeLine === null}
          />
        ) : (
          <ol className="mt-6 flex flex-col gap-7">
            {turns.map((turn) =>
              turn.role === "user" ? (
                <QuestionEntry key={turn.id} turn={turn} hue={scopeHue} />
              ) : (
                <AnswerEntry
                  key={turn.id}
                  turn={turn}
                  repo={scope ?? ""}
                  hue={scopeHue}
                />
              )
            )}
          </ol>
        )}

        <div ref={endRef} />

        {error && (
          <p
            role="alert"
            className="mt-4 border border-fault bg-paper px-3 py-2 text-[0.9375rem] text-fault"
          >
            {error}
          </p>
        )}

        <ChatInput
          onSend={ask}
          onStop={stop}
          streaming={streaming}
          repoName={scopeLabel}
        />
      </section>

      <aside aria-labelledby="index-heading" className="flex flex-col gap-4 lg:pt-1">
        <div className="border border-hairline bg-surface">
          <div className="border-b border-hairline px-4 py-2.5">
            <h2 id="index-heading" className="label text-ink">
              {activeLine ? "The index it reads" : "Lines in scope"}
            </h2>
          </div>
          {activeLine ? (
            <ol className="max-h-[26rem] overflow-y-auto">
              {activeLine.nodes.map((node, index) => (
                <li
                  key={node.node_id}
                  className="grid grid-cols-[1.75rem_minmax(0,1fr)] gap-2 border-b border-hairline px-4 py-2 last:border-b-0"
                >
                  <span className="station-index pt-0.5">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                  <div className="min-w-0">
                    <p className="text-[0.875rem] font-semibold leading-snug text-ink">
                      {node.title}
                    </p>
                    <p className="data mt-0.5 break-all text-ink-3">{node.node_id}</p>
                  </div>
                </li>
              ))}
              {activeLine.nodes.length === 0 && (
                <li className="px-4 py-3 text-[0.9375rem] text-ink-2">
                  No tree index on disk for this line.
                </li>
              )}
            </ol>
          ) : (
            <ol className="max-h-[26rem] overflow-y-auto">
              {lines.map((entry, index) => (
                <li
                  key={entry.repo_name}
                  className="grid grid-cols-[1.75rem_minmax(0,1fr)] gap-2 border-b border-hairline px-4 py-2 last:border-b-0"
                >
                  <span className="station-index pt-0.5">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                  <div className="min-w-0">
                    <p className="text-[0.875rem] font-semibold leading-snug text-ink">
                      {entry.display_name}
                    </p>
                    <p className="data mt-0.5 text-ink-3">
                      {entry.nodes.length} nodes · {entry.pageCount}{" "}
                      {entry.pageCount === 1 ? "page" : "pages"}
                    </p>
                  </div>
                </li>
              ))}
            </ol>
          )}
        </div>

        <div className="border border-hairline bg-paper-2 p-4">
          <h2 className="label mb-2 text-ink">How an answer is built</h2>
          <ol className="flex list-none flex-col gap-2 text-[0.9375rem] leading-snug text-ink-2">
            <li>
              <span className="data mr-1.5 text-ink-3">01</span>
              Rank node titles, summaries, and sections against the question
              {activeLine ? " in the selected line" : " across every line"}.
            </li>
            <li>
              <span className="data mr-1.5 text-ink-3">02</span>
              Open the sections the ranking selects.
            </li>
            <li>
              <span className="data mr-1.5 text-ink-3">03</span>
              Quote them, and cite the line and node each passage came from.
            </li>
          </ol>
          <p className="mt-3 text-[0.8125rem] leading-relaxed text-ink-3">
            No embeddings, no similarity threshold. The local reader quotes the
            generated page verbatim, so nothing is paraphrased on the way out.
          </p>
        </div>
      </aside>
    </div>
  );
}

/** One place that knows how a server event changes a turn. */
function applyEvent(
  event: ChatStreamEvent,
  patch: (update: (turn: ChatTurn) => ChatTurn) => void
) {
  switch (event.type) {
    case "step":
      patch((turn) => ({
        ...turn,
        steps: [
          ...turn.steps,
          { step: event.step, detail: event.detail } satisfies ChatStep,
        ],
      }));
      return;
    case "nodes":
      patch((turn) => ({
        ...turn,
        citations: event.nodes satisfies ChatCitation[],
      }));
      return;
    case "token":
      patch((turn) => ({ ...turn, content: turn.content + event.delta }));
      return;
    case "done":
      patch((turn) => ({
        ...turn,
        engine: event.engine satisfies ChatEngine,
        status: "done",
      }));
      return;
    case "error":
      patch((turn) => ({
        ...turn,
        status: "failed",
        content: turn.content || event.message,
      }));
      return;
    default:
      return;
  }
}
