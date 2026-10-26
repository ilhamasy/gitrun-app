"use client";

import { useState } from "react";
import { Check, Copy } from "lucide-react";

interface CodeCellProps {
  className?: string;
  children: React.ReactNode;
}

/**
 * A code sample is a timetable window inside the reading column: enamel header
 * naming the language, the sample on a dark field, copy in the header's corner.
 */
export function CodeCell({ className, children }: CodeCellProps) {
  const [copied, setCopied] = useState(false);
  const textContent = String(children).replace(/\n$/, "");
  const language = className?.replace("language-", "") ?? "code";

  async function copy() {
    try {
      await navigator.clipboard.writeText(textContent);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      setCopied(false);
    }
  }

  return (
    <figure className="code-cell my-6">
      <figcaption className="code-cell-head">
        <span className="label-wide">{language}</span>
        <button
          type="button"
          onClick={copy}
          className="label-wide inline-flex items-center gap-1.5 px-1 py-0.5 transition-opacity hover:opacity-70"
        >
          {copied ? (
            <>
              <Check className="size-3" aria-hidden="true" />
              Copied
            </>
          ) : (
            <>
              <Copy className="size-3" aria-hidden="true" />
              Copy
            </>
          )}
          <span className="sr-only">{`the ${language} sample`}</span>
        </button>
      </figcaption>
      <pre className="code-cell-pre">
        <code>{children}</code>
      </pre>
    </figure>
  );
}
