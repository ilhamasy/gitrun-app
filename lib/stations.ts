/**
 * Pure station/wayfinding helpers. Kept free of Node APIs so client components
 * (the rail, the on-page index) and server components share one source of truth.
 */

export interface RepoPage {
  slug: string;
  title: string;
  description: string;
}

export interface PeerService {
  repo_name: string;
  display_name: string;
  role: string;
}

export interface SystemMeta {
  system_name: string;
  display_name: string;
  peer_services?: PeerService[];
}

export interface RepoToc {
  repo_name: string;
  display_name: string;
  description: string;
  language?: string;
  stars?: number;
  /** What was actually read: source URL/path, requested ref, branch, commit. */
  source?: string;
  ref?: string;
  branch?: string;
  commit?: string;
  is_system?: boolean;
  system?: SystemMeta;
  member_repos?: string[];
  pages: RepoPage[];
}

export interface PageIndexNode {
  node_id: string;
  file: string;
  title: string;
  level: number;
  summary: string;
}

export interface PageIndexTree {
  repo: string;
  generated_at: string;
  nodes: PageIndexNode[];
}

export interface HeadingItem {
  id: string;
  /** The heading's own words, with any leading document numeral removed. */
  text: string;
  level: number;
}

export interface NumberedHeading extends HeadingItem {
  code: string;
}

export const LINE_HUES = [
  { key: "harbour", name: "Harbour", field: "#1f5c94", ink: "#1f5c94" },
  { key: "bramble", name: "Bramble", field: "#7a2141", ink: "#7a2141" },
  { key: "cedar", name: "Cedar", field: "#11643f", ink: "#11643f" },
  { key: "amber", name: "Amber", field: "#8a4b00", ink: "#8a4b00" },
  { key: "violet", name: "Violet", field: "#4a3c7a", ink: "#4a3c7a" },
] as const;

export type LineHue = (typeof LINE_HUES)[number];

/** Deterministic per repository, so a line never changes colour between visits. */
export function getLineHue(repoName: string): LineHue {
  let hash = 0;
  for (let i = 0; i < repoName.length; i += 1) {
    hash = (hash * 31 + repoName.charCodeAt(i)) >>> 0;
  }
  return LINE_HUES[hash % LINE_HUES.length];
}

export function lineVars(hue: LineHue): Record<string, string> {
  return {
    "--line": hue.field,
    "--line-ink": hue.ink,
  };
}

/** Two-digit station code, derived from page position. This is the address. */
export function stationCode(index: number): string {
  return String(index + 1).padStart(2, "0");
}

/**
 * Headings and the tree index must agree on the anchor, or a citation lands in
 * the wrong place. One slug rule, used by the renderer and the extractor.
 */
export function slugifyHeading(text: string): string {
  return text
    .toLowerCase()
    .replace(/[`*_~]/g, "")
    .replace(/[^\w\s-]/g, "")
    .trim()
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-");
}

/**
 * Headings are markdown. A heading that names a status code writes it in
 * backticks ("### Response `201 Created`"); the index and the margin print
 * plain text, so the inline markers are removed rather than shown literally.
 */
function plainHeadingText(text: string): string {
  return text.replace(/[`*_~]/g, "").replace(/\s+/g, " ").trim();
}

/**
 * A document may already number its own sections ("## 1. Create Payment
 * Intent"). The margin owns the address, so a leading numeral is stripped
 * before display: a section never wears two numbers.
 */
const DOCUMENT_NUMERAL = /^(\d+(?:\.\d+)*)\.?\s+/;

export function splitDocumentNumeral(text: string): { code: string | null; text: string } {
  const match = text.match(DOCUMENT_NUMERAL);
  if (!match) return { code: null, text };
  return { code: match[1], text: text.slice(match[0].length) };
}

export function extractHeadings(markdown: string): HeadingItem[] {
  const headings: HeadingItem[] = [];
  for (const line of markdown.split("\n")) {
    const match = line.match(/^(#{2,4})\s+(.+)$/);
    if (match) {
      // The id keeps the author's numeral so existing anchors never move; the
      // display text drops it, because the margin carries the address.
      const raw = match[2].trim();
      headings.push({
        id: slugifyHeading(raw),
        text: plainHeadingText(splitDocumentNumeral(raw).text),
        level: match[1].length,
      });
    }
  }
  return headings;
}

/** Section numbers in document order, so the margin can print them. */
/**
 * The margin number is the section's address in the retrieval tree — that is
 * the whole thesis — so it is always sequential. A numeral the author wrote
 * into the heading text is display, not address, and is stripped before the
 * heading is set, so a section never wears two numbers.
 */
export function numberHeadings(headings: HeadingItem[]): NumberedHeading[] {
  let h2 = 0;
  let h3 = 0;
  return headings.map((heading) => {
    if (heading.level === 2) {
      h2 += 1;
      h3 = 0;
      return { ...heading, code: `${h2}` };
    }
    h3 += 1;
    return { ...heading, code: `${h2}.${h3}` };
  });
}

export function formatGenerationDate(iso: string | undefined): string | null {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  return date
    .toLocaleDateString("en-GB", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      timeZone: "UTC",
    })
    .toUpperCase();
}
