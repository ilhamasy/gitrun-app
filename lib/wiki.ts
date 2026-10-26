import fs from "fs/promises";
import path from "path";

import type { PageIndexTree, RepoPage, RepoToc } from "@/lib/stations";

export type { PageIndexNode, PageIndexTree, RepoPage, RepoToc } from "@/lib/stations";
export {
  LINE_HUES,
  extractHeadings,
  formatGenerationDate,
  getLineHue,
  lineVars,
  numberHeadings,
  slugifyHeading,
  stationCode,
} from "@/lib/stations";

const CONTENT_DIR = path.join(process.cwd(), "content");

/**
 * Repository names and page slugs arrive from the URL and from the chat API,
 * so they are untrusted. Resolve the path and refuse anything that escapes
 * `content/` — a viewer may only read a compiled wiki, never the disk.
 */
function contentPath(...segments: string[]): string | null {
  const resolved = path.resolve(CONTENT_DIR, ...segments);
  const relative = path.relative(CONTENT_DIR, resolved);
  if (relative === "" || relative.startsWith("..") || path.isAbsolute(relative)) {
    return null;
  }
  return resolved;
}

export interface StationContext {
  title: string;
  description: string;
  summary: string | null;
  code: string;
  index: number;
  total: number;
}

export async function getAllRepos(): Promise<RepoToc[]> {
  "use cache";
  try {
    const entries = await fs.readdir(CONTENT_DIR, { withFileTypes: true });
    const repos: RepoToc[] = [];

    for (const entry of entries) {
      if (entry.isDirectory()) {
        const tocPath = path.join(CONTENT_DIR, entry.name, "toc.json");
        try {
          const raw = await fs.readFile(tocPath, "utf-8");
          repos.push(JSON.parse(raw) as RepoToc);
        } catch {
          // Skip directories without valid toc.json
        }
      }
    }

    return repos.sort((a, b) => a.display_name.localeCompare(b.display_name));
  } catch {
    return [];
  }
}

export async function getRepoToc(repoName: string): Promise<RepoToc | null> {
  "use cache";
  const tocPath = contentPath(repoName, "toc.json");
  if (!tocPath) return null;
  try {
    const raw = await fs.readFile(tocPath, "utf-8");
    return JSON.parse(raw) as RepoToc;
  } catch {
    return null;
  }
}

export async function getRepoPageMarkdown(
  repoName: string,
  slug: string
): Promise<string | null> {
  "use cache";
  const pagePath = contentPath(repoName, `${slug}.md`);
  if (!pagePath) return null;
  try {
    return await fs.readFile(pagePath, "utf-8");
  } catch {
    return null;
  }
}

export async function getRepoPageIndexTree(
  repoName: string
): Promise<PageIndexTree | null> {
  "use cache";
  const treePath = contentPath(repoName, "pageindex_tree.json");
  if (!treePath) return null;
  try {
    const raw = await fs.readFile(treePath, "utf-8");
    return JSON.parse(raw) as PageIndexTree;
  } catch {
    return null;
  }
}

export interface StationEntry extends RepoPage {
  code: string;
  index: number;
}

export function stationsOf(toc: RepoToc): StationEntry[] {
  return toc.pages.map((page, index) => ({
    ...page,
    code: String(index + 1).padStart(2, "0"),
    index,
  }));
}

/** The tree node that heads a page: its summary is the station subtitle. */
export function getStationContext(
  toc: RepoToc,
  tree: PageIndexTree | null,
  slug: string
): StationContext | null {
  const index = toc.pages.findIndex((page) => page.slug === slug);
  if (index < 0) return null;
  const page = toc.pages[index];
  const node = tree?.nodes.find((n) => n.file === `${slug}.md` && n.level === 2);
  return {
    title: page.title,
    description: page.description,
    summary: node?.summary ?? null,
    code: String(index + 1).padStart(2, "0"),
    index,
    total: toc.pages.length,
  };
}

/** First sentence of a page's opening paragraph, for the departure board. */
export function firstParagraph(markdown: string | null): string | null {
  if (!markdown) return null;
  const body = markdown
    .split("\n")
    .filter((line) => !line.startsWith("#"))
    .join(" ")
    .replace(/\s+/g, " ")
    .trim();
  if (!body) return null;
  const sentence = body.match(/^(.{40,220}?[.!?])(\s|$)/);
  return sentence
    ? sentence[1].replace(/\*\*/g, "").replace(/`/g, "")
    : body.slice(0, 160);
}

export function countHeadings(markdown: string | null): number {
  if (!markdown) return 0;
  return extractHeadingCount(markdown);
}

function extractHeadingCount(markdown: string): number {
  let count = 0;
  for (const line of markdown.split("\n")) {
    if (/^#{2,4}\s+/.test(line)) count += 1;
  }
  return count;
}

