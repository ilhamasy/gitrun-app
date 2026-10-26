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

interface ChatContainerProps {
  lines: ChatRepoSummary[];
  initialRepo: string;
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
 * The thread. One repository per conversation, stated in the header, so no
 * answer can quietly drift onto another line's corpus.
 */
export function ChatContainer({ lines, initialRepo }: ChatContainerProps) {
  const router = useRouter();
  const [repo, setRepo] = useState(initialRepo);
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const endRef = useRef<HTMLDivElement | null>(null);

  const line = lines.find((entry) => entry.repo_name === repo) ?? lines[0];

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end", behavior: "smooth" });
  }, [turns]);

  useEffect(() => () => abortRef.current?.abort(), []);

  const selectRepo = useCallback(
    (next: string) => {
      if (next === repo) return;
      abortRef.current?.abort();
      setRepo(next);
      setTurns([]);
      setError(null);
      setStreaming(false);
      const url = new URL(window.location.href);
      url.searchParams.set("repo", next);
      window.history.replaceState(null, "", url);
      router.refresh();
    },
    [repo, router]
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
            repo,
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
    [repo, streaming, turns]
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

  if (!line) return null;

  return (
    <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_20rem] lg:gap-10">
      <section aria-label="Conversation" className="min-w-0">
        <div className="flex flex-wrap items-end justify-between gap-x-4 gap-y-2 border-b border-hairline pb-3">
          <label className="flex min-w-0 flex-col gap-1">
            <span className="label-wide text-ink-3">Line under question</span>
            <select
              value={repo}
              onChange={(event) => selectRepo(event.target.value)}
              className="h-10 max-w-full border border-hairline-strong bg-surface px-2.5 font-[family-name:var(--font-signage)] text-[0.9375rem] font-semibold tracking-[0.04em] text-ink"
            >
              {lines.map((entry) => (
                <option key={entry.repo_name} value={entry.repo_name}>
                  {entry.display_name}
                </option>
              ))}
            </select>
          </label>

          <div className="flex items-center gap-3">
            <span className="data text-ink-3">
              {line.nodes.length} nodes · {line.pageCount}{" "}
              {line.pageCount === 1 ? "page" : "pages"}
            </span>
            {turns.length > 0 && (
              <button type="button" onClick={clear} className="btn btn-quiet h-9 px-3">
                <Eraser className="size-3.5" aria-hidden="true" />
                Clear thread
              </button>
            )}
          </div>
        </div>

        {turns.length === 0 ? (
          <StarterPrompts
            repo={line.repo_name}
            displayName={line.display_name}
            prompts={line.starters}
            onPick={ask}
          />
        ) : (
          <ol className="mt-6 flex flex-col gap-7">
            {turns.map((turn) =>
              turn.role === "user" ? (
                <QuestionEntry key={turn.id} turn={turn} hue={line.hue} />
              ) : (
                <AnswerEntry
                  key={turn.id}
                  turn={turn}
                  repo={line.repo_name}
                  hue={line.hue}
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
          repoName={line.display_name}
        />
      </section>

      <aside aria-labelledby="index-heading" className="flex flex-col gap-4 lg:pt-1">
        <div className="border border-hairline bg-surface">
          <div className="border-b border-hairline px-4 py-2.5">
            <h2 id="index-heading" className="label text-ink">
              The index it reads
            </h2>
          </div>
          <ol className="max-h-[26rem] overflow-y-auto">
            {line.nodes.map((node, index) => (
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
            {line.nodes.length === 0 && (
              <li className="px-4 py-3 text-[0.9375rem] text-ink-2">
                No tree index on disk for this line.
              </li>
            )}
          </ol>
        </div>

        <div className="border border-hairline bg-paper-2 p-4">
          <h2 className="label mb-2 text-ink">How an answer is built</h2>
          <ol className="flex list-none flex-col gap-2 text-[0.9375rem] leading-snug text-ink-2">
            <li>
              <span className="data mr-1.5 text-ink-3">01</span>
              Rank node titles, summaries, and sections against the question.
            </li>
            <li>
              <span className="data mr-1.5 text-ink-3">02</span>
              Open the sections the ranking selects.
            </li>
            <li>
              <span className="data mr-1.5 text-ink-3">03</span>
              Quote them, and cite the node each passage came from.
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
