import Link from "next/link";
import { ArrowRight } from "lucide-react";
import {
  getAllRepos,
  getLineHue,
  getRepoPageIndexTree,
  stationCode,
} from "@/lib/wiki";
import { Masthead } from "@/components/masthead";

export const metadata = {
  title: "Reasoning chat — not connected",
  description:
    "The PageIndex reasoning chat surface specified for GoWiki. It needs the FastAPI service, which is not running in this build.",
};

/**
 * This surface is honest about its state: the chat requires a reasoning service
 * that this build does not ship. Rather than fake a conversation, it shows the
 * real tree the service would navigate, so the mechanism is legible before the
 * service exists.
 */
export default async function ChatPage() {
  const repos = await getAllRepos();

  const lines = await Promise.all(
    repos.map(async (repo) => {
      const tree = await getRepoPageIndexTree(repo.repo_name);
      return {
        repo,
        hue: getLineHue(repo.repo_name),
        nodes: tree?.nodes ?? [],
      };
    })
  );

  return (
    <div className="flex min-h-screen flex-col bg-paper">
      <a href="#content" className="skip-link">
        Skip to content
      </a>
      <Masthead />

      <main id="content" className="mx-auto w-full max-w-[1100px] flex-1 px-4 py-10 sm:px-6 lg:py-14">
        <header className="mb-8 border-b-2 border-ink pb-5">
          <h1 className="signage text-[2.5rem] sm:text-[3.25rem]">
            Reasoning chat
          </h1>
          <p className="mt-3 max-w-[62ch] text-[1.0625rem] leading-relaxed text-ink-2">
            Answers are produced by a reasoning service that walks the tree
            index and streams the nodes it inspected. That service is not part
            of this build, so no question can be answered here yet. Nothing
            below will pretend otherwise.
          </p>
          <p className="mt-4 flex flex-wrap items-center gap-3">
            <span className="tag tag-on-signal">Not connected</span>
            <span className="label-wide text-ink-3">
              Waiting on the reasoning service
            </span>
          </p>
        </header>

        <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_20rem]">
          <section aria-labelledby="tree-heading">
            <h2 id="tree-heading" className="label mb-3 text-ink">
              The index it would navigate
            </h2>
            <p className="mb-5 max-w-[62ch] text-[0.9375rem] leading-relaxed text-ink-2">
              Every node below is a real heading from the compiled wiki with its
              own summary. A question would be routed by reading these summaries
              top-down — not by comparing embeddings — and the answer would cite
              the node it stopped on.
            </p>

            <div className="flex flex-col gap-6">
              {lines.map(({ repo, hue, nodes }) => (
                <section key={repo.repo_name}>
                  <div className="mb-2 flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1 border-b border-hairline pb-1.5">
                    <h3 className="label inline-flex items-center gap-2 text-ink">
                      <span
                        className="h-2.5 w-5 shrink-0"
                        data-line={hue.key}
                        style={{ background: "var(--line)" }}
                        aria-hidden="true"
                      />
                      {repo.display_name}
                    </h3>
                    <span className="data text-ink-3">
                      {String(nodes.length).padStart(2, "0")} nodes
                    </span>
                  </div>

                  {nodes.length === 0 ? (
                    <p className="py-2 text-[0.9375rem] text-ink-2">
                      No tree index on disk for this line.
                    </p>
                  ) : (
                    <ol className="flex flex-col">
                      {nodes.map((node, index) => (
                        <li
                          key={node.node_id}
                          className="grid grid-cols-[2.25rem_minmax(0,1fr)] gap-2 border-b border-hairline py-2"
                        >
                          <span className="station-index pt-0.5">
                            {stationCode(index)}
                          </span>
                          <div className="min-w-0">
                            <p className="text-[0.9375rem] font-semibold leading-snug text-ink">
                              {node.title}
                            </p>
                            <p className="mt-0.5 text-[0.8125rem] leading-snug text-ink-2">
                              {node.summary}
                            </p>
                            <p className="data mt-1 text-ink-3">
                              {node.node_id}
                            </p>
                          </div>
                        </li>
                      ))}
                    </ol>
                  )}
                </section>
              ))}
            </div>
          </section>

          <aside className="flex flex-col gap-5">
            <div className="border border-hairline bg-surface p-4">
              <h2 className="label mb-2 text-ink">What this needs</h2>
              <ul className="flex flex-col gap-2 text-[0.9375rem] leading-snug text-ink-2">
                <li>A reasoning service on localhost:8000.</li>
                <li>
                  <span className="data">POST /api/chat</span> streaming steps,
                  nodes, and tokens.
                </li>
                <li>One repository selected per conversation.</li>
              </ul>
            </div>

            <div className="border border-hairline bg-paper-2 p-4">
              <h2 className="label mb-2 text-ink">Read instead</h2>
              <p className="mb-3 text-[0.9375rem] leading-snug text-ink-2">
                The wiki is complete on disk and needs no service. Start with a
                line and read the section a citation would point at.
              </p>
              <Link href="/wiki" className="btn btn-primary w-full">
                Open the line board
                <ArrowRight className="size-4" aria-hidden="true" />
              </Link>
            </div>

            <p className="text-[0.8125rem] leading-relaxed text-ink-3">
              Seeded repositories are demo fixtures and are not organizational
              services.
            </p>
          </aside>
        </div>
      </main>
    </div>
  );
}
