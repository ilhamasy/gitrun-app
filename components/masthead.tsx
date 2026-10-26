"use client";

import { Suspense } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ThemeToggle } from "@/components/theme-toggle";

/**
 * Two label lengths: the full destination where there is room, the same
 * destination in sign language where there is not. Nothing is truncated.
 */
const DESTINATIONS = [
  { href: "/wiki", short: "Lines", label: "Wiki lines" },
  { href: "/chat", short: "Chat", label: "Reasoning chat" },
  { href: "/generate", short: "Document", label: "Document a repo" },
] as const;

function isCurrent(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}

/**
 * One row at every width. On narrow screens the destinations scroll beside the
 * wordmark instead of stacking into a second bar, so the page starts higher.
 */
function MastheadNav() {
  const pathname = usePathname();
  return (
    <nav
      aria-label="Primary"
      className="masthead-nav -mr-2 flex min-w-0 flex-1 items-stretch gap-4 overflow-x-auto px-1 sm:mr-0 sm:gap-7 sm:px-0 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
    >
      {DESTINATIONS.map((destination) => (
        <Link
          key={destination.href}
          href={destination.href}
          aria-current={isCurrent(pathname, destination.href) ? "page" : undefined}
          className="masthead-link shrink-0 text-[0.6875rem] sm:text-[0.8125rem]"
        >
          <span className="sm:hidden">{destination.short}</span>
          <span className="hidden sm:inline">{destination.label}</span>
        </Link>
      ))}
    </nav>
  );
}

export function Masthead() {
  return (
    <header className="masthead sticky top-0 z-40">
      <div className="mx-auto flex h-14 max-w-[1600px] items-stretch gap-5 px-4 sm:gap-8 sm:px-6">
        <Link href="/" className="wordmark shrink-0 self-center">
          <span className="pip-mark" aria-hidden="true" />
          <span className="wordmark-text">GoWiki</span>
        </Link>

        <Suspense
          fallback={
            <nav
              aria-label="Primary"
              className="masthead-nav -mr-2 flex min-w-0 flex-1 items-stretch gap-4 overflow-x-auto px-1 sm:mr-0 sm:gap-7 sm:px-0 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
            />
          }
        >
          <MastheadNav />
        </Suspense>

        <div className="flex shrink-0 items-center gap-2">
          <ThemeToggle />
          <Link
            href="/generate"
            className="btn btn-on-enamel hidden h-9 px-3.5 text-[0.7rem] sm:inline-flex"
          >
            Pipeline
          </Link>
        </div>
      </div>
    </header>
  );
}
