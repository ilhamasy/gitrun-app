"use client";

import Link from "next/link";
import { ArrowUpRight, ChevronDown } from "lucide-react";
import { ReadingColumn } from "@/components/reading-column";
import { citationHref } from "@/lib/chat";
import type { ChatEngine, ChatTurn } from "@/lib/chat";
import { stationCode } from "@/lib/stations";

const ENGINE_LABEL: Record<ChatEngine, string> = {
  local: "Local index reader",
  model: "Reasoning service",
};

interface AnswerEntryProps {
  turn: ChatTurn;
  /** Scope of the thread; citations may override it with their own line. */
  repo: string;
  hue: string;
}

/**
 * One answer, printed. The header names the engine that wrote it, the drawer
 * shows the tree walk that produced it, and every citation opens the exact
 * section the quoted text came from.
 */
export function AnswerEntry({ turn, repo, hue }: AnswerEntryProps) {
  const streaming = turn.status === "streaming";
  const failed = turn.status === "failed";
  const cited = turn.citations;
  const citedLines = new Set(cited.map((c) => c.repo ?? repo).filter(Boolean));
  const spansLines = citedLines.size > 1;

  return (
    <article className="border-t-2 border-ink pt-4" data-line={hue}>
      <header className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <h2 className="label inline-flex items-center gap-2 text-ink">
          <span
            className="h-2.5 w-4 shrink-0"
            style={{ background: "var(--line)" }}
            aria-hidden="true"
          />
          Answer
        </h2>
        <p className="label-wide flex items-center gap-2 text-ink-3">
          {streaming ? (
            <>
              <span className="sq-lamp" aria-hidden="true" />
              Reading the tree
            </>
          ) : failed ? (
            <span className="text-fault">Stopped</span>
          ) : (
            <>
              {turn.engine ? ENGINE_LABEL[turn.engine] : "No engine"} ·{" "}
              {String(cited.length).padStart(2, "0")} cited
              {spansLines ? ` across ${citedLines.size} lines` : ""}
            </>
          )}
        </p>
      </header>

      {turn.steps.length > 0 && (
        <details open={streaming} className="step-drawer mt-3">
          <summary className="step-summary">
            <span className="label inline-flex items-center gap-2 text-ink">
              <ChevronDown className="size-3.5" aria-hidden="true" />
              {streaming
                ? "Walking the PageIndex tree"
                : `Inspected ${turn.steps.length} PageIndex ${turn.steps.length === 1 ? "step" : "steps"}`}
            </span>
            <span className="data text-ink-3">
              {String(turn.steps.length).padStart(2, "0")}
            </span>
          </summary>
          <ol className="mt-2 border-t border-hairline">
            {turn.steps.map((step, index) => (
              <li
                key={`${step.step}-${index}`}
                className="grid grid-cols-[2rem_minmax(0,1fr)] gap-2 border-b border-hairline py-1.5"
              >
                <span className="station-index pt-0.5">{stationCode(index)}</span>
                <div className="min-w-0">
                  <p className="text-[0.875rem] font-semibold leading-snug text-ink">
                    {step.step}
                  </p>
                  {step.detail && (
                    <p className="data mt-0.5 break-words text-ink-3">{step.detail}</p>
                  )}
                </div>
              </li>
            ))}
          </ol>
        </details>
      )}

      {turn.content ? (
        <div className="mt-4">
          <ReadingColumn content={turn.content} />
        </div>
      ) : (
        streaming && (
          <p className="mt-4 flex items-center gap-2 text-[1.0625rem] text-ink-2">
            <span className="sq-lamp" aria-hidden="true" />
            Reading the sections the index selected…
          </p>
        )
      )}

      {failed && !turn.content && (
        <p className="mt-4 border border-hairline-strong border-l-0 border-r-0 bg-paper-2 px-3 py-2 text-[0.9375rem] text-ink">
          The answer did not reach the page. Ask again, or read the index beside
          this thread.
        </p>
      )}

      {cited.length > 0 && (
        <div className="mt-5">
          <p className="label-wide mb-2 text-ink-3">
            Cited nodes · open the section
          </p>
          <ul className="grid gap-px border border-hairline bg-hairline">
            {cited.map((citation, index) => (
              <li
                key={`${citation.repo ?? repo}:${citation.node_id}`}
                className="bg-paper"
              >
                <Link
                  href={citationHref(repo, citation)}
                  className="group grid grid-cols-[2rem_minmax(0,1fr)_auto] items-start gap-2.5 px-3 py-2.5 transition-colors hover:bg-surface"
                >
                  <span className="station-index pt-1">
                    {stationCode(index)}
                  </span>
                  <span className="min-w-0">
                    <span className="block text-[0.9375rem] font-semibold leading-snug text-ink group-hover:underline">
                      {citation.title}
                    </span>
                    <span className="data mt-0.5 block break-all text-ink-3">
                      {citation.repo ? `${citation.repo} · ` : ""}
                      {citation.node_id}
                    </span>
                  </span>
                  <ArrowUpRight
                    className="mt-1 size-3.5 shrink-0 text-ink-3 group-hover:text-ink"
                    aria-hidden="true"
                  />
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}
    </article>
  );
}
