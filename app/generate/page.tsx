import { Masthead } from "@/components/masthead";
import { IngestionStepper } from "@/components/ingestion-stepper";

export const metadata = {
  title: "Document a repository — GoWiki Ingestion Engine",
  description:
    "Run the autonomous five-stage GoWiki ingestion pipeline: Git clone, Repomix pack, two-pass LLM synthesis, and PageIndex tree generation.",
};


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
            Run the five-stage GoWiki ingestion pipeline. Clones the repository,
            packs source with Repomix, synthesizes standardized markdown documentation
            across two LLM passes, and builds vectorless PageIndex trees for reasoning chat.
          </p>
          <p className="mt-4 flex flex-wrap items-center gap-3">
            <span className="tag bg-line-cedar text-white">Live pipeline ready</span>
            <span className="label-wide text-ink-3">
              Connected to backend SSE runner
            </span>
          </p>
        </header>

        <IngestionStepper />
      </main>
    </div>
  );
}
