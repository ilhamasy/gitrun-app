"use client";

import { useEffect, useRef, useState } from "react";
import type { NumberedHeading } from "@/lib/stations";

interface StationIndexProps {
  headings: NumberedHeading[];
}

/**
 * The station index in the right margin. Where you are is marked by the same
 * signal yellow the rail uses, so one state means one thing everywhere.
 */
export function StationIndex({ headings }: StationIndexProps) {
  const [active, setActive] = useState<string | null>(headings[0]?.id ?? null);
  const [fadeBottom, setFadeBottom] = useState(false);
  const listRef = useRef<HTMLUListElement | null>(null);

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

  // A long index scrolls inside the margin instead of running past the bottom
  // of the window. Fade the cut edge only while there is more to reach.
  useEffect(() => {
    const list = listRef.current;
    if (!list) return;

    const measure = () =>
      setFadeBottom(list.scrollTop + list.clientHeight < list.scrollHeight - 1);
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(list);
    list.addEventListener("scroll", measure, { passive: true });
    return () => {
      observer.disconnect();
      list.removeEventListener("scroll", measure);
    };
  }, [headings]);

  // The index scrolls on its own once a page has more sections than fit beside
  // it, so the current station is kept in view rather than left below the fold.
  useEffect(() => {
    const list = listRef.current;
    const current = list?.querySelector<HTMLElement>('[data-active="true"]');
    if (!list || !current) return;

    const listBox = list.getBoundingClientRect();
    const currentBox = current.getBoundingClientRect();
    if (currentBox.top < listBox.top) {
      list.scrollTop -= listBox.top - currentBox.top;
    } else if (currentBox.bottom > listBox.bottom) {
      list.scrollTop += currentBox.bottom - listBox.bottom;
    }
  }, [active]);

  if (headings.length === 0) return null;

  return (
    <div className="station-aside hidden shrink-0 xl:block xl:w-[248px] xl:pl-10">
      <div className="sticky top-[6.25rem] flex max-h-[calc(100vh-8.75rem)] flex-col py-8 pl-6 pr-6">
        <nav
          aria-label="Stations on this page"
          className="flex min-h-0 flex-col"
        >
          <p className="label-wide mb-2 shrink-0 border-b border-hairline pb-1.5 text-ink-3">
            On this page
          </p>
          <ul
            ref={listRef}
            className="flex min-h-0 flex-col overflow-y-auto overscroll-contain pb-8 pr-1 [scrollbar-width:thin] [&::-webkit-scrollbar]:w-1.5"
            style={
              fadeBottom
                ? {
                    maskImage:
                      "linear-gradient(to bottom, #000 calc(100% - 1.75rem), transparent 100%)",
                  }
                : undefined
            }
          >
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
                  <span className="leading-snug">{heading.text}</span>
                </a>
              </li>
            ))}
          </ul>
        </nav>
      </div>
    </div>
  );
}
