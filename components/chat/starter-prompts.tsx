"use client";

import { CornerDownLeft } from "lucide-react";

interface StarterPromptsProps {
  repo: string;
  displayName: string;
  prompts: string[];
  onPick: (prompt: string) => void;
  global?: boolean;
}

/**
 * The thread opens on what this line can actually answer. A question that the
 * index cannot route is a bad first impression in a three-minute demo.
 */
export function StarterPrompts({
  repo,
  displayName,
  prompts,
  onPick,
  global = false,
}: StarterPromptsProps) {
  return (
    <div className="mt-7">
      <h2 className="label mb-1 text-ink">
        {global ? "Ask across every line" : `Ask ${displayName}`}
      </h2>
      <p className="mb-4 max-w-[58ch] text-[1.0625rem] leading-relaxed text-ink-2">
        {global ? (
          <>
            These questions are routed through the node index of every project on
            the board, so an answer can draw on more than one line. Pick one, or
            write your own.
          </>
        ) : (
          <>
            Every question below is routed through the {repo} node index and
            answered from the section it selects. Pick one, or write your own.
          </>
        )}
      </p>

      <ul className="grid gap-px border border-hairline bg-hairline">
        {prompts.map((prompt, index) => (
          <li key={prompt} className="bg-paper">
            <button
              type="button"
              onClick={() => onPick(prompt)}
              className="group grid w-full grid-cols-[2.25rem_minmax(0,1fr)_auto] items-start gap-3 px-3.5 py-3 text-left transition-colors hover:bg-surface"
            >
              <span className="station-index pt-1">
                {String(index + 1).padStart(2, "0")}
              </span>
              <span className="text-[1.0625rem] leading-snug text-ink group-hover:underline">
                {prompt}
              </span>
              <CornerDownLeft
                className="mt-1 size-3.5 shrink-0 text-ink-3 group-hover:text-ink"
                aria-hidden="true"
              />
            </button>
          </li>
        ))}
      </ul>

      <p className="mt-3 text-[0.8125rem] leading-relaxed text-ink-3">
        Answers quote the generated wiki verbatim and name the node they came
        from. Seeded repositories are demo fixtures.
      </p>
    </div>
  );
}
