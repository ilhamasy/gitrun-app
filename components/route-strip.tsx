import Link from "next/link";
import { ChevronRight } from "lucide-react";
import type { LineHue, RepoToc } from "@/lib/stations";

interface RouteStripProps {
  repo: RepoToc;
  hue: LineHue;
  stationCode?: string;
  stationTitle?: string;
  generated: string | null;
  nodeCount: number | null;
}

/**
 * The colour field beneath the masthead. It answers the two questions a reader
 * has on arrival: which line, and which station on it.
 */
export function RouteStrip({
  repo,
  hue,
  stationCode,
  stationTitle,
  generated,
  nodeCount,
}: RouteStripProps) {
  return (
    <div
      className="route-strip"
      data-line={hue.key}
    >
      <div className="mx-auto flex max-w-[1600px] flex-wrap items-center gap-x-4 gap-y-1.5 px-4 py-2.5 sm:px-6">
        <span className="sr-only">You are here:</span>
        <Link
          href="/wiki"
          className="label-wide underline-offset-4 hover:underline"
        >
          All lines
        </Link>
        <ChevronRight className="size-3 opacity-60" aria-hidden="true" />
        <Link
          href={`/wiki/${repo.repo_name}/${repo.pages[0]?.slug ?? "overview"}`}
          className="label-wide inline-flex items-center gap-2 underline-offset-4 hover:underline"
        >
          <span className="h-2 w-6 bg-white/85" aria-hidden="true" />
          {repo.display_name}
        </Link>

        {stationCode && stationTitle && (
          <>
            <ChevronRight className="size-3 opacity-60" aria-hidden="true" />
            <span className="label-wide inline-flex items-center gap-1.5">
              <span className="bg-white px-1 py-px text-[0.625rem] font-bold text-[var(--line)] tabular-nums">
                {stationCode}
              </span>
              <span className="opacity-90">{stationTitle}</span>
            </span>
          </>
        )}

        <span className="flex w-full flex-wrap items-center gap-x-4 gap-y-1 sm:ml-auto sm:w-auto">
          {nodeCount !== null && (
            <span className="route-strip-meta">
              {String(nodeCount).padStart(2, "0")} indexed nodes
            </span>
          )}
          {generated && (
            <span className="route-strip-meta">Generated {generated}</span>
          )}
        </span>
      </div>
    </div>
  );
}
