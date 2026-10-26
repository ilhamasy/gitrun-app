"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowUp, Square } from "lucide-react";

interface ChatInputProps {
  onSend: (question: string) => void;
  onStop: () => void;
  streaming: boolean;
  repoName: string;
}

/**
 * The composer is a form, not a chat widget: Enter sends, Shift+Enter breaks a
 * line, and the hint is a keyboard contract rather than decoration.
 */
export function ChatInput({ onSend, onStop, streaming, repoName }: ChatInputProps) {
  const [value, setValue] = useState("");
  const fieldRef = useRef<HTMLTextAreaElement | null>(null);

  // The field grows with the question but stops before it eats the thread.
  useEffect(() => {
    const field = fieldRef.current;
    if (!field) return;
    field.style.height = "auto";
    field.style.height = `${Math.min(field.scrollHeight, 200)}px`;
  }, [value]);

  function submit() {
    const question = value.trim();
    if (!question || streaming) return;
    onSend(question);
    setValue("");
  }

  return (
    <form
      className="mt-7 border border-hairline-strong bg-surface"
      onSubmit={(event) => {
        event.preventDefault();
        submit();
      }}
    >
      <label htmlFor="chat-question" className="label-wide block px-3.5 pt-2.5 text-ink-3">
        Ask about {repoName}
      </label>
      <textarea
        id="chat-question"
        ref={fieldRef}
        rows={2}
        value={value}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            submit();
          }
        }}
        placeholder="How does idempotency work?"
        className="block max-h-[200px] w-full resize-none bg-surface px-3.5 pb-2 pt-1.5 text-[1.0625rem] leading-relaxed text-ink placeholder:text-ink-3 focus:outline-none"
      />
      <div className="flex flex-wrap items-center justify-between gap-2 border-t border-hairline px-3.5 py-2">
        <p className="label-wide text-ink-3">
          Enter sends · Shift + Enter breaks a line
        </p>
        {streaming ? (
          <button type="button" onClick={onStop} className="btn btn-quiet h-9 px-3">
            <Square className="size-3" aria-hidden="true" />
            Stop
          </button>
        ) : (
          <button
            type="submit"
            disabled={value.trim().length === 0}
            className="btn btn-primary h-9 px-3.5"
          >
            Ask
            <ArrowUp className="size-3.5" aria-hidden="true" />
          </button>
        )}
      </div>
    </form>
  );
}
