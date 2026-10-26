"use client";

import { useEffect, useState } from "react";
import type { NumberedHeading } from "@/lib/stations";

interface StationIndexProps {
  headings: NumberedHeading[];
  summary: string | null;
}

/**
 * The station index in the right margin. Where you are is marked by the same
 * signal yellow the rail uses, so one state means one thing everywhere.
 */
export function StationIndex({ headings, summary }: StationIndexProps) {
  const [active, setActive] = useState<string | null>(headings[0]?.id ?? null);

  useEffect(() => {
    const elements = headings
      .map((heading) => document.getElementById(heading.id))
      .filter((element): element is HTMLElement => element !== null);
    if (elements.length === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (visible[0]) setActive(visible[0].target.id);
      },
      { rootMargin: "-88px 0px -60% 0px", threshold: 0 }
    );

    for (const element of elements) observer.observe(element);
    return () => observer.disconnect();
  }, [headings]);

  if (headings.length === 0) return null;

  return (
    <div className="hidden w-64 shrink-0 xl:block">
      <div className="sticky top-[6.25rem] flex flex-col gap-4 py-8 pl-6 pr-6">
        {summary && (
          <div>
            <p className="label-wide mb-2 text-ink-3">Station summary</p>
            <p className="text-[0.8125rem] leading-relaxed text-ink-2">{summary}</p>
          </div>
        )}

        <nav aria-label="Stations on this page">
          <p className="label-wide mb-2 border-b border-hairline pb-1.5 text-ink-3">
            On this page
          </p>
          <ul className="flex flex-col">
            {headings.map((heading) => (
              <li key={heading.id}>
                <a
                  href={`#${heading.id}`}
                  data-active={active === heading.id || undefined}
                  className="toc-link"
                  style={{
                    paddingLeft: `${0.625 + (heading.level - 2) * 0.75}rem`,
                  }}
                >
                  <span className="station-index pt-0.5">{heading.code}</span>
                  <span>{heading.text}</span>
                </a>
              </li>
            ))}
          </ul>
        </nav>
      </div>
    </div>
  );
}
