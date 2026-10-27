import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import {
  firstParagraph,
  formatGenerationDate,
  getAllRepos,
  getLineHue,
  getRepoPageIndexTree,
  getRepoPageMarkdown,
  stationsOf,
} from "@/lib/wiki";
import { Masthead } from "@/components/masthead";

export const metadata = {
  title: "Wiki lines",
  description: "Every repository GitRun has compiled into a browsable wiki line.",
};

export default async function WikiDirectoryPage() {
  const repos = await getAllRepos();

  const rows = await Promise.all(
    repos.map(async (repo) => {
      const [tree, overview] = await Promise.all([
        getRepoPageIndexTree(repo.repo_name),
        getRepoPageMarkdown(
          repo.repo_name,
          repo.pages[0]?.slug ?? "overview"
        ),
      ]);
      return {
        repo,
        hue: getLineHue(repo.repo_name),
        stations: stationsOf(repo),
        generated: formatGenerationDate(tree?.generated_at),
        opening: firstParagraph(overview),
      };
    })
  );

  return (
    <div className="flex min-h-screen flex-col bg-paper">
      <a href="#content" className="skip-link">
        Skip to the line board
      </a>
      <Masthead />

      <main id="content" className="mx-auto w-full max-w-[980px] px-4 py-10 sm:px-6 lg:py-14">
        <header className="mb-9 border-b-2 border-ink pb-5">
          <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-2">
            <h1 className="signage text-[2.5rem] sm:text-[3.25rem]">
              Line board
            </h1>
            <p className="data max-w-[34ch] pb-1.5 text-ink-2">
              {String(repos.length).padStart(2, "0")} lines ·{" "}
              {String(
                repos.reduce((total, repo) => total + repo.pages.length, 0)
              ).padStart(2, "0")}{" "}
              stations compiled
            </p>
          </div>
        </header>

        {repos.length === 0 ? (
          <div className="border border-dashed border-hairline-strong px-6 py-16 text-center">
            <p className="signage text-[1.5rem]">No lines on the board yet</p>
            <p className="mx-auto mt-2 max-w-[46ch] text-ink-2">
              A line appears here once GitRun has compiled a repository into
              pages. Nothing is generated at request time, so this board stays
              accurate when the network does not.
            </p>
            <Link href="/generate" className="btn btn-primary mt-6">
              Document a repository
            </Link>
          </div>
        ) : (
          <div className="border-t border-hairline">
            <div
              aria-hidden="true"
              className="board-grid hidden border-b border-ink bg-paper-2 px-5 py-2 sm:grid"
            >
              <span className="label-wide text-ink-2">Line</span>
              <span className="label-wide text-ink-2">Destination</span>
              <span className="label-wide text-ink-2">Stations</span>
              <span className="label-wide text-right text-ink-2">Compiled</span>
            </div>

            <ul>
              {rows.map(({ repo, hue, stations, generated, opening }) => {
                const href = `/wiki/${repo.repo_name}/${stations[0]?.slug ?? "overview"}`;
                return (
                  <li key={repo.repo_name}>
                    <Link href={href} className="board-row group">
                      <span className="board-line">
                        <span
                          className="board-line-swatch"
                          data-line={hue.key}
                          style={{ background: "var(--line)" }}
                          aria-hidden="true"
                        />
                        <span className="label text-ink">
                          {hue.name}
                          <span className="sr-only"> line</span>
                        </span>
                      </span>

                      <span className="min-w-0">
                        <span className="board-destination block text-ink">
                          {repo.display_name}
                        </span>
                        <span className="mt-1 block max-w-[54ch] text-[0.875rem] leading-snug text-ink-2">
                          {opening ?? repo.description}
                        </span>
                        <span className="mt-2 flex flex-wrap gap-1.5 sm:hidden">
                          {stations.map((station) => (
                            <span key={station.slug} className="tag text-ink-2">
                              {station.code}
                            </span>
                          ))}
                          <span className="tag text-ink-2">
                            {repo.language ?? "Mixed"}
                          </span>
                        </span>
                      </span>

                      <span className="hidden sm:block">
                        <span className="signage block text-[1.375rem] leading-none text-ink tabular-nums">
                          {String(stations.length).padStart(2, "0")}
                        </span>
                        <span className="board-meta mt-1 block text-ink-3">
                          {repo.language ?? "Mixed"}
                        </span>
                      </span>

                      <span className="text-right">
                        <span className="data hidden text-ink-2 sm:block">
                          {generated ?? "—"}
                        </span>
                        <span className="label-wide mt-1 inline-flex items-center gap-1 text-ink-3 transition-colors group-hover:text-ink">
                          Open line
                          <ArrowUpRight
                            className="size-3"
                            aria-hidden="true"
                          />
                        </span>
                      </span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        )}

        <div className="mt-10 grid gap-px border-t border-hairline bg-hairline sm:grid-cols-3">
          <div className="bg-paper pt-4 pr-4">
            <h2 className="label mb-1.5 text-ink">One line per repository</h2>
            <p className="text-[0.875rem] leading-snug text-ink-2">
              The colour is assigned from the repository name, so a line keeps
              its identity between visits and two repositories never swap.
            </p>
          </div>
          <div className="bg-paper pt-4 pr-4">
            <h2 className="label mb-1.5 text-ink">A station per page</h2>
            <p className="text-[0.875rem] leading-snug text-ink-2">
              Every repository gets the same page skeleton, so you learn the
              shape once and read the second repository faster.
            </p>
          </div>
          <div className="bg-paper pt-4">
            <h2 className="label mb-1.5 text-ink">A node per section</h2>
            <p className="text-[0.875rem] leading-snug text-ink-2">
              Section numbers are the addresses a citation resolves to. Open one
              and you land on the exact claim that was cited.
            </p>
          </div>
        </div>

        <p className="mt-6 max-w-[62ch] text-[0.8125rem] leading-relaxed text-ink-3">
          Every line above was compiled from a seeded demo repository. GitRun
          does not host or fetch source on this machine, so the board is a
          fixture for the pitch rather than a mirror of an organization.
        </p>
      </main>
    </div>
  );
}
