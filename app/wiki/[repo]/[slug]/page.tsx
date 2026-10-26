import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, ArrowRight } from "lucide-react";
import {
  extractHeadings,
  getAllRepos,
  getLineHue,
  getRepoPageIndexTree,
  getRepoPageMarkdown,
  getRepoToc,
  numberHeadings,
  formatGenerationDate,
} from "@/lib/wiki";
import { ReadingColumn } from "@/components/reading-column";
import { StationIndex } from "@/components/station-index";
import { RouteStrip } from "@/components/route-strip";

export const instant = false;

export async function generateStaticParams() {
  const repos = await getAllRepos();
  return repos.flatMap((repo) =>
    repo.pages.map((page) => ({ repo: repo.repo_name, slug: page.slug }))
  );
}

interface WikiDocPageProps {
  params: Promise<{ repo: string; slug: string }>;
}

export async function generateMetadata({
  params,
}: WikiDocPageProps): Promise<Metadata> {
  const { repo, slug } = await params;
  const toc = await getRepoToc(repo);
  const page = toc?.pages.find((entry) => entry.slug === slug);
  if (!toc || !page) return { title: "No such station" };
  return {
    title: `${page.title} — ${toc.display_name}`,
    description: page.description,
  };
}

/** The page title is the station name, so the body's own H1 is folded into it. */
function withoutLeadingH1(markdown: string): string {
  return markdown.replace(/^#\s+.+\n+/, "");
}

export default async function WikiDocPage({ params }: WikiDocPageProps) {
  const { repo, slug } = await params;
  const [toc, markdown, tree] = await Promise.all([
    getRepoToc(repo),
    getRepoPageMarkdown(repo, slug),
    getRepoPageIndexTree(repo),
  ]);

  if (!toc || !markdown) {
    notFound();
  }

  const hue = getLineHue(repo);
  const generated = formatGenerationDate(tree?.generated_at);
  const index = toc.pages.findIndex((page) => page.slug === slug);
  const station = toc.pages[index];
  const headings = numberHeadings(extractHeadings(markdown));
  const prev = index > 0 ? toc.pages[index - 1] : null;
  const next =
    index >= 0 && index < toc.pages.length - 1 ? toc.pages[index + 1] : null;

  const pageNodes =
    tree?.nodes.filter((node) => node.file === `${slug}.md`) ?? [];
  const summary = pageNodes.find((node) => node.level === 2)?.summary ?? null;

  return (
    <div className="flex min-h-screen flex-col">
      <RouteStrip
        repo={toc}
        hue={hue}
        stationCode={String(index + 1).padStart(2, "0")}
        stationTitle={station.title}
        generated={generated}
        nodeCount={tree?.nodes.length ?? null}
      />

      <div className="mx-auto flex w-full max-w-[1520px] flex-1 flex-col xl:flex-row">
        <main className="min-w-0 flex-1 px-5 py-8 sm:px-8 lg:px-12 lg:py-10">
          <div className="max-w-[64ch]">
            <header className="mb-9">
              <h1 className="signage text-[2.25rem] leading-[1.04] text-ink sm:text-[2.875rem]">
                {station.title}
              </h1>
              <p className="mt-3 max-w-[58ch] text-[1.0625rem] leading-relaxed text-ink-2">
                {station.description}
              </p>
              <p className="label-wide mt-4 flex flex-wrap items-center gap-x-3 gap-y-1 text-ink-3">
                <span>{hue.name} line</span>
                <span aria-hidden="true" className="h-3 w-px bg-hairline-strong" />
                <span>
                  Station {String(index + 1).padStart(2, "0")} of{" "}
                  {String(toc.pages.length).padStart(2, "0")}
                </span>
                {pageNodes.length > 0 && (
                  <>
                    <span
                      aria-hidden="true"
                      className="h-3 w-px bg-hairline-strong"
                    />
                    <span>{pageNodes.length} indexed sections</span>
                  </>
                )}
              </p>
            </header>

            <ReadingColumn content={withoutLeadingH1(markdown)} />

            <nav
              aria-label="Adjacent stations"
              className="mt-14 grid gap-px border-t-2 border-ink bg-hairline sm:grid-cols-2"
            >
              {prev ? (
                <Link
                  href={`/wiki/${repo}/${prev.slug}`}
                  className="group flex flex-col gap-1 bg-paper py-4 pr-4 transition-colors hover:bg-surface"
                >
                  <span className="label-wide inline-flex items-center gap-1.5 text-ink-3">
                    <ArrowLeft className="size-3" aria-hidden="true" />
                    Previous station
                  </span>
                  <span className="signage text-[1.125rem] text-ink group-hover:underline">
                    {prev.title}
                  </span>
                </Link>
              ) : (
                <div className="hidden bg-paper sm:block" aria-hidden="true" />
              )}

              {next && (
                <Link
                  href={`/wiki/${repo}/${next.slug}`}
                  className="group flex flex-col gap-1 bg-paper py-4 pl-0 transition-colors hover:bg-surface sm:items-end sm:pl-4"
                >
                  <span className="label-wide inline-flex items-center gap-1.5 text-ink-3">
                    Next station
                    <ArrowRight className="size-3" aria-hidden="true" />
                  </span>
                  <span className="signage text-[1.125rem] text-ink group-hover:underline">
                    {next.title}
                  </span>
                </Link>
              )}
            </nav>

            <p className="mt-6 text-[0.8125rem] leading-relaxed text-ink-3">
              Generated from the repository by GoWiki. Seeded demo content —
              not a real organizational service.
            </p>
          </div>
        </main>

        <StationIndex headings={headings} summary={summary} />
      </div>
    </div>
  );
}
