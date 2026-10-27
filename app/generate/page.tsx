import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Masthead } from "@/components/masthead";

export const metadata = {
  title: "Document a repository — pipeline not connected",
  description:
    "The five-stage GitRun ingestion pipeline. The runner is not part of this build; this surface documents what it would execute.",
};

const STAGES = [
  {
    stage: "Clone",
    detail: "git clone --depth 1",
    body: "A shallow clone of the repository at its default branch, discarded after the run.",
  },
  {
    stage: "Bundle",
    detail: "repomix --ignore",
    body: "Source packed into one token-efficient file with tests, lockfiles, and binaries excluded.",
  },
  {
    stage: "Outline",
    detail: "pass 1 · table of contents",
    body: "One model call writes the contents for the fixed page set: overview, architecture, setup, API reference.",
  },
  {
    stage: "Pages",
    detail: "pass 2 · parallel generation",
    body: "One call per page, run concurrently, each written from the bundle and the outline.",
  },
  {
    stage: "Index",
    detail: "headings → tree",
    body: "Headings become nodes with one-line summaries — the structure the chat reasons over.",
  },
];

export default function GeneratePage() {
  return (
    <div className="flex min-h-screen flex-col bg-paper">
      <a href="#content" className="skip-link">
        Skip to the pipeline
      </a>
      <Masthead />

      <main id="content" className="mx-auto w-full max-w-[1100px] flex-1 px-4 py-10 sm:px-6 lg:py-14">
        <header className="mb-9 border-b-2 border-ink pb-5">
          <h1 className="signage text-[2.5rem] sm:text-[3.25rem]">
            Document a repository
          </h1>
          <p className="mt-3 max-w-[62ch] text-[1.0625rem] leading-relaxed text-ink-2">
            The ingestion runner is a separate Python service. It is not part of
            this build, so no repository can be submitted here. The five stages
            below are what it executes, in order, and what a live run would
            stream back as progress.
          </p>
          <p className="mt-4 flex flex-wrap items-center gap-3">
            <span className="tag tag-on-signal">Not connected</span>
            <span className="label-wide text-ink-3">
              Waiting on the ingestion runner
            </span>
          </p>
        </header>

        <div className="grid gap-10 lg:grid-cols-[minmax(0,1fr)_22rem]">
          <section aria-labelledby="stages-heading">
            <h2 id="stages-heading" className="label mb-4 text-ink">
              Pipeline stages
            </h2>

            <ol className="relative">
              <span
                aria-hidden="true"
                className="absolute bottom-6 left-[0.6875rem] top-3 w-[3px] bg-ink/15"
              />
              {STAGES.map((step, index) => (
                <li
                  key={step.stage}
                  className="relative grid grid-cols-[1.5rem_minmax(0,1fr)] gap-4 pb-7"
                >
                  <span
                    className="relative z-10 mt-1 h-6 w-6 border-2 border-ink bg-paper"
                    aria-hidden="true"
                  >
                    <span className="absolute inset-[5px] bg-ink/20" />
                  </span>
                  <div>
                    <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                      <h3 className="signage text-[1.375rem]">{step.stage}</h3>
                      <span className="data text-ink-3">{step.detail}</span>
                    </div>
                    <p className="mt-1 max-w-[56ch] text-[0.9375rem] leading-relaxed text-ink-2">
                      {step.body}
                    </p>
                    <p className="label-wide mt-2 text-ink-3">
                      Stage {String(index + 1).padStart(2, "0")} of 05
                    </p>
                  </div>
                </li>
              ))}
            </ol>
          </section>

          <aside className="flex flex-col gap-5">
            <div className="border border-hairline bg-surface">
              <div className="border-b border-hairline px-4 py-2.5">
                <h2 className="label text-ink">Submission is disabled</h2>
              </div>
              <div className="px-4 py-4">
                <label
                  htmlFor="repo-url"
                  className="label-wide mb-1.5 block text-ink-2"
                >
                  Repository URL or local path
                </label>
                <input
                  id="repo-url"
                  type="text"
                  disabled
                  placeholder="https://github.com/org/service"
                  aria-describedby="repo-url-help"
                  className="h-10 w-full cursor-not-allowed border border-hairline-strong bg-paper-2 px-3 font-mono text-[0.8125rem] text-ink-3 placeholder:text-ink-3"
                />
                <p id="repo-url-help" className="mt-1.5 text-[0.8125rem] text-ink-3">
                  Inert until the runner is reachable.
                </p>
                <button
                  type="button"
                  disabled
                  className="btn btn-primary mt-3 w-full"
                >
                  Start ingestion
                </button>
              </div>
            </div>

            <div className="border border-hairline bg-paper-2 p-4">
              <h2 className="label mb-2 text-ink">What this needs</h2>
              <ul className="flex flex-col gap-2 text-[0.9375rem] leading-snug text-ink-2">
                <li>
                  <span className="data">GET /api/generate/stream</span> as
                  server-sent events.
                </li>
                <li>A clone, Repomix, and two model passes per repository.</li>
                <li>
                  Writes under <span className="data">content/&lt;repo&gt;/</span>,
                  which the reader already serves.
                </li>
              </ul>
            </div>

            <Link href="/wiki" className="btn btn-quiet w-full">
              Browse existing lines
              <ArrowRight className="size-4" aria-hidden="true" />
            </Link>
          </aside>
        </div>
      </main>
    </div>
  );
}
