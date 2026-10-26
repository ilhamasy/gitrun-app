import type { ChatTurn } from "@/lib/chat";

interface QuestionEntryProps {
  turn: ChatTurn;
  hue: string;
}

/** A question is a printed heading on the thread, not a chat bubble. */
export function QuestionEntry({ turn, hue }: QuestionEntryProps) {
  return (
    <li className="grid grid-cols-[2.25rem_minmax(0,1fr)] gap-3" data-line={hue}>
      <span
        className="mt-1.5 h-3 w-3 self-start"
        style={{ background: "var(--line)" }}
        aria-hidden="true"
      />
      <div className="min-w-0">
        <p className="label-wide text-ink-3">Question</p>
        <p className="signage mt-1 text-[1.5rem] leading-[1.18] text-ink sm:text-[1.75rem]">
          {turn.content}
        </p>
      </div>
    </li>
  );
}
