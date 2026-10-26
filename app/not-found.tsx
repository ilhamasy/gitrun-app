import Link from "next/link";
import { Masthead } from "@/components/masthead";

export const metadata = {
  title: "No such station",
};

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col bg-paper">
      <Masthead />
      <main className="mx-auto flex w-full max-w-[1100px] flex-1 items-start px-4 py-16 sm:px-6">
        <div className="w-full border border-hairline bg-surface px-6 py-12 sm:px-10">
          <p className="label-wide mb-3 text-ink-3">Station not found</p>
          <h1 className="signage max-w-[20ch] text-[2.5rem] sm:text-[3rem]">
            This station is not on any line.
          </h1>
          <p className="mt-3 max-w-[52ch] text-[1.0625rem] leading-relaxed text-ink-2">
            The page you asked for does not exist in any compiled wiki. Lines are
            built from folders under <code className="data">content/</code>, so a
            repository that was never documented has nothing to show here.
          </p>
          <div className="mt-7 flex flex-wrap gap-3">
            <Link href="/wiki" className="btn btn-primary">
              Open the line board
            </Link>
            <Link href="/" className="btn btn-quiet">
              Back to the start
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
}
