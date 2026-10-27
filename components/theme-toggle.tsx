"use client";

import { useSyncExternalStore } from "react";
import { Moon, Sun } from "lucide-react";

/**
 * The projector scene is bright, so light is the default. This control exists
 * for the engineer reading beside an editor at night, and it remembers.
 *
 * The resolved theme lives in the document's class list, set by the head
 * script before paint. The toggle subscribes to it rather than copying it into
 * component state, so there is one source of truth and no post-mount write.
 */
const THEME_EVENT = "gitrun-theme-change";

function subscribe(onChange: () => void): () => void {
  window.addEventListener(THEME_EVENT, onChange);
  window.addEventListener("storage", onChange);
  return () => {
    window.removeEventListener(THEME_EVENT, onChange);
    window.removeEventListener("storage", onChange);
  };
}

function readTheme(): "light" | "dark" {
  return document.documentElement.classList.contains("dark") ? "dark" : "light";
}

export function ThemeToggle() {
  const theme = useSyncExternalStore(subscribe, readTheme, () => null);
  const dark = theme === "dark";

  function toggle() {
    const next = dark ? "light" : "dark";
    document.documentElement.classList.toggle("dark", next === "dark");
    try {
      window.localStorage.setItem("gitrun-theme", next);
    } catch {
      // Storage can be blocked; the toggle still works for this visit.
    }
    window.dispatchEvent(new Event(THEME_EVENT));
  }

  return (
    <button
      type="button"
      onClick={toggle}
      aria-pressed={theme === null ? undefined : dark}
      aria-label={
        dark ? "Switch to the light theme" : "Switch to the dark theme"
      }
      className="grid h-9 w-9 place-items-center border border-white/30 text-white/85 transition-colors hover:border-white/60 hover:text-white"
    >
      {theme === null ? (
        <span className="block h-3.5 w-3.5" aria-hidden="true" />
      ) : dark ? (
        <Sun className="size-4" aria-hidden="true" />
      ) : (
        <Moon className="size-4" aria-hidden="true" />
      )}
    </button>
  );
}
