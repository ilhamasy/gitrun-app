import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { Masthead } from "@/components/masthead";
import { RouteStrip } from "@/components/route-strip";
import { ChatContainer } from "@/components/chat/chat-container";
import { starterPrompts } from "@/lib/chat";
import type { ChatRepoSummary } from "@/lib/chat";
import {
  formatGenerationDate,
  getAllRepos,
  getLineHue,
  getRepoPageIndexTree,
  getRepoToc,
} from "@/lib/wiki";

export const metadata: Metadata = {
  title: "Reasoning chat",
  description:
    "Ask a repository question and watch the PageIndex tree get walked. Every answer names and links the section it was read from.",
};

export const instant = false;

interface ChatPageProps {
  searchParams: Promise<{ repo?: string | string[] }>;
}

export default async function ChatPage({ searchParams }: ChatPageProps) {
  const params = await searchParams;
  const requested = Array.isArray(params.repo) ? params.repo[0] : params.repo;

  const repos = await getAllRepos();
  if (repos.length === 0) {
    return (
      <div className="flex min-h-screen flex-col bg-paper">
        <Masthead />
        <main className="mx-auto flex w-full max-w-[980px] flex-1 flex-col items-center justify-center px-4 py-16 text-center">
          <p className="signage text-[1.75rem]">No lines compiled yet</p>
          <p className="mx-auto mt-2 max-w-[46ch] text-ink-2">
            Ingest a repository first to reason over its architecture and code with PageIndex.
          </p>
          <Link href="/generate" className="btn btn-primary mt-6">
            Document a repository
          </Link>
        </main>
      </div>
    );
  }

  const lines: ChatRepoSummary[] = await Promise.all(
    repos.map(async (repo) => {
      const tree = await getRepoPageIndexTree(repo.repo_name);
      return {
        repo_name: repo.repo_name,
        display_name: repo.display_name,
        description: repo.description,
        language: repo.language,
        pageCount: repo.pages.length,
        generated: formatGenerationDate(tree?.generated_at),
        hue: getLineHue(repo.repo_name).key,
        nodes: tree?.nodes ?? [],
        starters: starterPrompts(repo),
      };
    })
  );

  const active =
    lines.find((line) => line.repo_name === requested) ?? lines[0];
  const toc = await getRepoToc(active.repo_name);
  const hue = getLineHue(active.repo_name);

  return (
    <div className="flex min-h-screen flex-col bg-paper">
      <a href="#content" className="skip-link">
        Skip to the conversation
      </a>
      <Masthead />

      {toc && (
        <RouteStrip
          repo={toc}
          hue={hue}
          generated={active.generated}
          nodeCount={active.nodes.length}
        />
      )}

      <main
        id="content"
        className="mx-auto w-full max-w-[1180px] flex-1 px-4 py-8 sm:px-6 lg:py-10"
      >
        <header className="mb-7 border-b-2 border-ink pb-4">
          <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
            <div className="min-w-0">
              <h1 className="signage text-[2.25rem] leading-[1.04] sm:text-[2.875rem]">
                Reasoning chat
              </h1>
              <p className="mt-2 max-w-[62ch] text-[1.0625rem] leading-relaxed text-ink-2">
                Questions are routed by reading the tree index — titles,
                summaries, then sections — and answered by quoting the sections
                it stops on. Each claim carries the node it came from.
              </p>
            </div>
            <p className="label-wide flex shrink-0 flex-col items-start gap-1 text-ink-3">
              <span>One line per conversation</span>
              <span className="data text-ink-3">
                {active.nodes.length} indexed nodes
              </span>
            </p>
          </div>
        </header>

        <ChatContainer lines={lines} initialRepo={active.repo_name} />

        <nav
          aria-label="Continue reading"
          className="mt-10 grid border-t-2 border-ink sm:grid-cols-2"
        >
          {toc && (
            <Link
              href={`/wiki/${toc.repo_name}/${toc.pages[0]?.slug ?? "overview"}`}
              className="group flex flex-col gap-1 bg-paper py-4 transition-colors hover:bg-surface sm:pr-6"
            >
              <span className="label-wide inline-flex items-center gap-1.5 text-ink-3">
                Read the source page
                <ArrowRight className="size-3" aria-hidden="true" />
              </span>
              <span className="signage text-[1.125rem] text-ink group-hover:underline">
                Open {toc.display_name}
              </span>
            </Link>
          )}
          <Link
            href="/wiki"
            className="group flex flex-col gap-1 border-t border-hairline bg-paper py-4 transition-colors hover:bg-surface sm:border-l sm:border-t-0 sm:items-end sm:pl-6"
          >
            <span className="label-wide inline-flex items-center gap-1.5 text-ink-3">
              Another line
              <ArrowRight className="size-3" aria-hidden="true" />
            </span>
            <span className="signage text-[1.125rem] text-ink group-hover:underline">
              Open the line board
            </span>
          </Link>
        </nav>
      </main>
    </div>
  );
}
