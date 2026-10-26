import Link from "next/link";
import { ArrowRight } from "lucide-react";
import {
  firstParagraph,
  formatGenerationDate,
  getAllRepos,
  getLineHue,
  getRepoPageIndexTree,
  getRepoPageMarkdown,
  stationCode,
} from "@/lib/wiki";
import { Masthead } from "@/components/masthead";

export const metadata = {
  title: "GoWiki — generated wikis for department codebases",
};

export default async function Home() {
  const repos = await getAllRepos();

  const richest = [...repos].sort((a, b) => b.pages.length - a.pages.length)[0];
  const featured = await Promise.all(
    (richest ? [richest] : []).map(async (repo) => {
      const slug = repo.pages[0]?.slug ?? "overview";
      const [tree, overview] = await Promise.all([
        getRepoPageIndexTree(repo.repo_name),
        getRepoPageMarkdown(repo.repo_name, slug),
      ]);
      const stationRows = repo.pages.map((page, index) => ({
        title: page.title,
        code: stationCode(index),
        summary: page.description,
      }));
      return {
        repo,
        hue: getLineHue(repo.repo_name),
        slug,
        opening: firstParagraph(overview),
        generated: formatGenerationDate(tree?.generated_at),
        nodes: tree?.nodes.length ?? 0,
        outline: stationRows,
      };
    })
  );

  return (
    <div className="flex min-h-screen flex-col bg-paper">
      <a href="#content" className="skip-link">
        Skip to content
      </a>
      <Masthead />

      <main id="content" className="flex-1">
        {/* The thesis: a repository becomes a line, and its pages become
            numbered stations you can cite. */}
        <section className="border-b border-hairline">
          <div className="mx-auto grid max-w-[1280px] gap-10 px-4 py-12 sm:px-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,30rem)] lg:gap-16 lg:py-16">
            <div className="max-w-[34rem] lg:py-2">
              <h1 className="signage text-[2.75rem] leading-[0.98] sm:text-[3.75rem] lg:text-[4.25rem]">
                A codebase with no documentation becomes a line you can ride.
              </h1>

              <p className="mt-5 max-w-[52ch] text-[1.0625rem] leading-relaxed text-ink-2">
                GoWiki bundles a repository, compiles the same four pages every
                time, and indexes their headings into a tree. Answers navigate
                that tree, so each claim arrives with the section — and only
                that section — it was read from.
              </p>

              <div className="mt-7 flex flex-wrap items-center gap-3">
                <Link href="/wiki" className="btn btn-primary">
                  Open the line board
                  <ArrowRight className="size-4" aria-hidden="true" />
                </Link>
                <Link href="/generate" className="btn btn-quiet">
                  Document a repository
                </Link>
              </div>

              <dl className="mt-10 grid grid-cols-3 gap-px border-t border-hairline bg-hairline">
                {[
                  ["Pages", "Four, always"],
                  ["Routing", "Tree, not vectors"],
                  ["Answer", "Cited by section"],
                ].map(([term, detail]) => (
                  <div key={term} className="bg-paper pt-3 pr-3">
                    <dt className="label-wide text-ink-3">{term}</dt>
                    <dd className="mt-1 text-[0.9375rem] leading-snug text-ink">
                      {detail}
                    </dd>
                  </div>
                ))}
              </dl>
            </div>

            {/* Mechanism, shown rather than described. */}
            <div
              className="self-start border border-ink bg-surface"
              data-line={featured[0]?.hue.key}
            >
              {featured[0] ? (
                <div className="flex h-full flex-col">
                  <div
                    className="flex items-center justify-between gap-3 px-4 py-2.5 text-white"
                    data-line={featured[0].hue.key}
                    style={{ background: "var(--line)" }}
                  >
                    <span className="label-wide inline-flex items-center gap-2">
                      <span className="h-2 w-6 bg-white/85" aria-hidden="true" />
                      Line {featured[0].repo.repo_name}
                    </span>
                    <span className="label-wide opacity-85">
                      {featured[0].nodes} nodes indexed
                    </span>
                  </div>

                  <div className="border-b border-hairline px-4 py-4">
                    <p className="signage text-[1.5rem] leading-tight">
                      {featured[0].repo.display_name}
                    </p>
                    <p className="mt-1.5 text-[0.875rem] leading-snug text-ink-2">
                      {featured[0].opening ?? featured[0].repo.description}
                    </p>
                  </div>

                  <ol className="flex-1 divide-y divide-hairline">
                    {featured[0].outline.map((node) => (
                      <li key={node.code}>
                        <Link
                          href={`/wiki/${featured[0].repo.repo_name}/${featured[0].slug}#${node.title
                            .toLowerCase()
                            .replace(/[^\w\s-]/g, "")
                            .replace(/\s+/g, "-")}`}
                          className="group flex items-start gap-3 px-4 py-2.5 transition-colors hover:bg-paper-2"
                        >
                          <span
                            className="mt-1 h-2.5 w-2.5 shrink-0 border-2"
                            style={{
                              borderColor: "var(--line)",
                              background:
                                node.code === "01" ? "var(--line)" : "transparent",
                            }}
                            aria-hidden="true"
                          />
                          <span className="min-w-0">
                            <span className="label block text-ink">
                              <span className="mr-2 text-ink-3 tabular-nums">
                                {node.code}
                              </span>
                              {node.title}
                            </span>
                            <span className="mt-0.5 line-clamp-1 block text-[0.8125rem] text-ink-2">
                              {node.summary}
                            </span>
                          </span>
                        </Link>
                      </li>
                    ))}
                  </ol>

                  <div className="mt-auto flex items-center justify-between gap-3 border-t border-hairline bg-paper-2 px-4 py-2.5">
                    <p className="label-wide text-ink-3">Seeded demo line</p>
                    <Link
                      href={`/wiki/${featured[0].repo.repo_name}/${featured[0].slug}`}
                      className="label inline-flex items-center gap-1.5 text-ink hover:underline"
                    >
                      Read the line
                      <ArrowRight className="size-3.5" aria-hidden="true" />
                    </Link>
                  </div>
                </div>
              ) : (
                <div className="px-4 py-16 text-center">
                  <p className="signage text-[1.375rem]">No lines compiled yet</p>
                  <p className="mt-2 text-[0.9375rem] text-ink-2">
                    Document a repository to put the first line on the board.
                  </p>
                </div>
              )}
            </div>
          </div>
        </section>

        {/* The pipeline, as a line diagram: five stages the work actually goes
            through, in order. */}
        <section className="mx-auto max-w-[1280px] px-4 py-12 sm:px-6 lg:py-16">
          <div className="mb-8 flex flex-wrap items-end justify-between gap-4 border-b-2 border-ink pb-3">
            <h2 className="signage text-[1.75rem] sm:text-[2.125rem]">
              From bare repository to citable line
            </h2>
            <p className="label-wide pb-1 text-ink-3">Five stages</p>
          </div>

          <ol className="grid gap-px bg-hairline md:grid-cols-5">
            {[
              {
                stage: "Clone",
                body: "Shallow clone of the repository at its default branch.",
              },
              {
                stage: "Bundle",
                body: "Repomix packs the source, dropping tests, lockfiles, binaries.",
              },
              {
                stage: "Outline",
                body: "First pass writes the table of contents for the fixed page set.",
              },
              {
                stage: "Pages",
                body: "Second pass writes each page in parallel from the bundle.",
              },
              {
                stage: "Index",
                body: "Headings become a tree; each node gets a one-line summary.",
              },
            ].map((step, index) => (
              <li key={step.stage} className="bg-paper px-4 py-5">
                <p className="data mb-2 text-ink-3">
                  {String(index + 1).padStart(2, "0")}
                </p>
                <h3 className="label mb-1.5 text-ink">{step.stage}</h3>
                <p className="text-[0.875rem] leading-snug text-ink-2">
                  {step.body}
                </p>
              </li>
            ))}
          </ol>
        </section>

        {/* Where to go next, as three destinations rather than a repeat of the
            marketing promise. */}
        <section className="border-t border-hairline bg-paper-2">
          <div className="mx-auto grid max-w-[1280px] gap-px px-4 py-12 sm:px-6 md:grid-cols-3 md:gap-8 lg:py-14">
            {[
              {
                href: "/wiki",
                title: "Line board",
                body: "Every compiled repository, its stations, and when it was generated.",
                action: "See the lines",
              },
              {
                href: "/chat",
                title: "Reasoning chat",
                body: "Ask about one repository; answers arrive with the sections they came from.",
                action: "Open chat",
              },
              {
                href: "/generate",
                title: "Document a repo",
                body: "The ingestion pipeline and what it would run. Not wired to a backend in this build.",
                action: "See the pipeline",
              },
            ].map((destination) => (
              <Link
                key={destination.href}
                href={destination.href}
                className="group flex flex-col justify-between gap-4 py-5 md:py-0"
              >
                <div>
                  <h3 className="signage text-[1.375rem] group-hover:underline">
                    {destination.title}
                  </h3>
                  <p className="mt-1.5 text-[0.9375rem] leading-snug text-ink-2">
                    {destination.body}
                  </p>
                </div>
                <span className="label inline-flex items-center gap-1.5 text-ink">
                  {destination.action}
                  <ArrowRight className="size-3.5" aria-hidden="true" />
                </span>
              </Link>
            ))}
          </div>
        </section>
      </main>

      <footer className="border-t border-hairline bg-paper">
        <div className="mx-auto flex max-w-[1280px] flex-wrap items-center justify-between gap-3 px-4 py-5 sm:px-6">
          <p className="label-wide text-ink-3">
            GoWiki · Department hackathon build
          </p>
          <p className="text-[0.8125rem] text-ink-3">
            Seeded repositories are demo fixtures, not organizational services.
          </p>
        </div>
      </footer>
    </div>
  );
}
