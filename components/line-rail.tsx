"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { LineHue, RepoToc } from "@/lib/stations";
import { getLineHue } from "@/lib/stations";

interface LineRailProps {
  currentRepo: RepoToc;
  allRepos: RepoToc[];
  hue: LineHue;
  generated: string | null;
}

export function LineRail({
  currentRepo,
  allRepos,
  hue,
  generated,
}: LineRailProps) {
  const pathname = usePathname();
  const currentIndex = currentRepo.pages.findIndex(
    (page) => pathname === `/wiki/${currentRepo.repo_name}/${page.slug}`
  );

  return (
    <aside
      className="rail"
      data-line={hue.key}
      aria-label={`${currentRepo.display_name} line`}
    >
      <div className="rail-head flex items-baseline justify-between gap-3 border-b border-hairline px-4 py-3">
        <span className="label text-ink">Line {currentRepo.repo_name}</span>
        <span className="data text-ink-3">
          {String(currentIndex >= 0 ? currentIndex + 1 : 1).padStart(2, "0")}/
          {String(currentRepo.pages.length).padStart(2, "0")}
        </span>
      </div>

      <nav aria-label="Stations on this line">
        <ol className="rail-stations">
          {currentRepo.pages.map((page, index) => {
            const href = `/wiki/${currentRepo.repo_name}/${page.slug}`;
            const active = pathname === href;
            const passed = currentIndex > index;
            return (
              <li key={page.slug} className="rail-station-item">
                <Link
                  href={href}
                  aria-current={active ? "page" : undefined}
                  data-active={active || undefined}
                  data-passed={passed || undefined}
                  className="rail-station"
                >
                  <span className="rail-pip" aria-hidden="true" />
                  <span className="rail-station-name">{page.title}</span>
                  <span className="rail-station-code">
                    {active ? "HERE" : String(index + 1).padStart(2, "0")}
                  </span>
                </Link>
              </li>
            );
          })}
        </ol>
      </nav>

      <div className="rail-extras">
      <div className="border-t border-hairline px-4 py-3">
        <Link
          href={`/wiki/${currentRepo.repo_name}/${currentRepo.pages[0]?.slug ?? "overview"}`}
          className="label text-ink-2 transition-colors hover:text-ink"
        >
          Line overview
        </Link>
      </div>

      {allRepos.length > 1 && (
        <div className="border-t border-hairline px-4 py-3">
          <p className="label-wide mb-2 text-ink-3">Interchange</p>
          <ul className="flex flex-col gap-1">
            {allRepos
              .filter((repo) => repo.repo_name !== currentRepo.repo_name)
              .map((repo) => (
                <li key={repo.repo_name}>
                  <Link
                    href={`/wiki/${repo.repo_name}/${repo.pages[0]?.slug ?? "overview"}`}
                    className="group flex items-center gap-2 py-1 text-sm text-ink-2 transition-colors hover:text-ink"
                  >
                    <span
                      className="h-2.5 w-4 shrink-0"
                      style={{ background: getLineHue(repo.repo_name).field }}
                      aria-hidden="true"
                    />
                    <span className="truncate">{repo.display_name}</span>
                  </Link>
                </li>
              ))}
          </ul>
        </div>
      )}

      {generated && (
        <div className="mt-auto border-t border-hairline px-4 py-3">
          <p className="label-wide text-ink-3">Generated {generated}</p>
        </div>
      )}
      </div>
    </aside>
  );
}
