/**
 * The vectorless reader.
 *
 * Retrieval here is the mechanism the product claims: rank tree nodes from
 * their titles and summaries, open the sections those nodes point at, then
 * quote them. Nothing is embedded, and nothing is paraphrased — the local
 * answer is assembled from sentences that exist in the generated wiki.
 *
 * Server-only: it reads the compiled pages from disk.
 */

import type { ChatCitation, ChatStep } from "@/lib/chat";
import { getRepoPageIndexTree, getRepoPageMarkdown, getRepoToc } from "@/lib/wiki";
import { slugifyHeading } from "@/lib/stations";

const STOPWORDS = new Set(
  `a about above after again against all am an and any are as at be because been before being below
  between both but by can cannot could did do does doing down during each few for from further had has
  have having he her here hers herself him himself his how i if in into is it its itself just me more
  most my myself no nor not of off on once only or other our ours ourselves out over own same she should
  so some such than that the their theirs them themselves then there these they this those through to
  too under until up very was we were what when where which while who whom why will with would you your
  yours yourself yourselves does doing done give gives show shows tell tells describe explain explains
  handle handles work works use uses used using get gets got make makes made`
    .split(/\s+/)
    .filter(Boolean)
);

/**
 * A five-character prefix is enough to keep `charge`/`charging`,
 * `prevent`/`preventing`, and `partition`/`partitioned` in one bucket. It is a
 * routing aid, not linguistics: the index decides where to look, the section
 * decides what is true.
 */
function tokenize(text: string): string[] {
  const words = text
    .toLowerCase()
    .replace(/[`*_>#|]/g, " ")
    .match(/[a-z0-9]+/g);
  if (!words) return [];
  return words
    .filter((word) => word.length > 2 && !STOPWORDS.has(word))
    .map((word) => (word.length > 5 ? word.slice(0, 5) : word));
}

function countTerms(text: string): Map<string, number> {
  const counts = new Map<string, number>();
  for (const token of tokenize(text)) {
    counts.set(token, (counts.get(token) ?? 0) + 1);
  }
  return counts;
}

interface Section {
  anchor: string;
  level: number;
  body: string;
}

/** Split a page at its headings, ignoring `#` characters inside code fences. */
function splitSections(markdown: string): Section[] {
  const lines = markdown.split(/\r?\n/);
  const headings: { anchor: string; line: number; level: number }[] = [];
  let inFence = false;

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    if (/^\s*(```|~~~)/.test(line)) {
      inFence = !inFence;
      continue;
    }
    if (inFence) continue;
    const match = line.match(/^(#{1,4})\s+(.+?)\s*$/);
    if (match) {
      headings.push({
        anchor: slugifyHeading(match[2]),
        line: index,
        level: match[1].length,
      });
    }
  }

  return headings.map((heading, position) => {
    let end = lines.length;
    for (let next = position + 1; next < headings.length; next += 1) {
      if (headings[next].level <= heading.level) {
        end = headings[next].line;
        break;
      }
    }
    return {
      anchor: heading.anchor,
      level: heading.level,
      body: lines.slice(heading.line + 1, end).join("\n").trim(),
    };
  });
}

export interface IndexedSection {
  citation: ChatCitation;
  body: string;
}

/** Every node in the tree, with the markdown its anchor points at. */
export async function loadIndexedSections(
  repoName: string
): Promise<{ sections: IndexedSection[]; pageCount: number } | null> {
  const [tree, toc] = await Promise.all([
    getRepoPageIndexTree(repoName),
    getRepoToc(repoName),
  ]);
  if (!tree || !toc) return null;

  const pages = await Promise.all(
    toc.pages.map(async (page) => ({
      slug: page.slug,
      markdown: (await getRepoPageMarkdown(repoName, page.slug)) ?? "",
    }))
  );

  const byFile = new Map<string, Section[]>();
  for (const page of pages) {
    byFile.set(`${page.slug}.md`, splitSections(page.markdown));
  }

  const sections: IndexedSection[] = tree.nodes.map((node) => {
    const anchor = node.node_id.split("#")[1] ?? "";
    const section = byFile.get(node.file)?.find((entry) => entry.anchor === anchor);
    return {
      citation: {
        node_id: node.node_id,
        title: node.title,
        file: node.file,
        summary: node.summary,
      },
      body: section?.body ?? "",
    };
  });

  return { sections, pageCount: toc.pages.length };
}

export interface RoutingResult {
  sections: IndexedSection[];
  steps: ChatStep[];
  matched: boolean;
}

/**
 * Step 1 of the protocol: walk the tree, score each node's title, summary, and
 * body against the question, and stop on the ones that answer it.
 */
export async function routeQuestion(
  repoName: string,
  question: string,
  limit = 3
): Promise<RoutingResult | null> {
  const indexed = await loadIndexedSections(repoName);
  if (!indexed) return null;
  const { sections, pageCount } = indexed;
  const query = [...new Set(tokenize(question))];

  if (query.length === 0 || sections.length === 0) {
    return {
      sections: sections.slice(0, 1),
      matched: false,
      steps: [
        { step: "Opened the index", detail: `${sections.length} nodes · ${pageCount} pages` },
        { step: "Ranked the tree", detail: "the question carried no terms to rank" },
      ],
    };
  }

  const documentFrequency = new Map<string, number>();
  const prepared = sections.map((section) => {
    const title = countTerms(section.citation.title);
    const summary = countTerms(section.citation.summary);
    const body = countTerms(section.body);
    for (const token of new Set([...title.keys(), ...summary.keys(), ...body.keys()])) {
      documentFrequency.set(token, (documentFrequency.get(token) ?? 0) + 1);
    }
    return { section, title, summary, body };
  });

  const scored = prepared
    .map((entry) => {
      let score = 0;
      for (const token of query) {
        const idf = Math.log(1 + sections.length / (documentFrequency.get(token) ?? 0.5));
        const titleHits = entry.title.get(token) ?? 0;
        const summaryHits = entry.summary.get(token) ?? 0;
        const bodyHits = entry.body.get(token) ?? 0;
        if (titleHits === 0 && summaryHits === 0 && bodyHits === 0) continue;
        score +=
          idf *
          (3 * Math.log1p(titleHits) +
            2 * Math.log1p(summaryHits) +
            1 * Math.log1p(bodyHits));
      }
      return { section: entry.section, score };
    })
    .filter((entry) => entry.score > 0)
    .sort((a, b) => b.score - a.score);

  if (scored.length === 0) {
    // No node names the question. Say so, and open one node from each page so
    // the reader can see the shape of what the index actually holds, instead
    // of receiving an invented answer.
    const seen = new Set<string>();
    const heads = sections.filter((section) => {
      if (seen.has(section.citation.file)) return false;
      seen.add(section.citation.file);
      return true;
    });
    return {
      sections: heads.slice(0, 2),
      matched: false,
      steps: [
        { step: "Opened the index", detail: `${sections.length} nodes · ${pageCount} pages` },
        { step: "Ranked the tree", detail: "no node title, summary, or section matched" },
      ],
    };
  }

  const selected = scored.slice(0, limit);
  const steps: ChatStep[] = [
    { step: "Opened the index", detail: `${sections.length} nodes · ${pageCount} pages` },
    {
      step: "Ranked the tree",
      detail: `${selected.length} of ${sections.length} nodes match the question`,
    },
    ...selected.map((entry) => ({
      step: "Opened the section",
      detail: entry.section.citation.node_id,
    })),
  ];

  return { sections: selected.map((entry) => entry.section), steps, matched: true };
}

const MAX_PASSAGE = 640;

/** Blocks are paragraphs, lists, tables, and code fences — not lines. */
function splitBlocks(body: string): string[] {
  const blocks: string[] = [];
  let current: string[] = [];
  let inFence = false;

  const flush = () => {
    const block = current.join("\n").trim();
    if (block) blocks.push(block);
    current = [];
  };

  for (const line of body.split(/\r?\n/)) {
    if (/^\s*(```|~~~)/.test(line)) {
      inFence = !inFence;
      current.push(line);
      continue;
    }
    if (inFence) {
      current.push(line);
      continue;
    }
    if (line.trim() === "") {
      flush();
      continue;
    }
    current.push(line);
  }
  flush();
  return blocks;
}

function trimPassage(block: string): string {
  if (block.length <= MAX_PASSAGE) return block;
  if (block.includes("```") || block.trimStart().startsWith("|")) return block;
  const cut = block.slice(0, MAX_PASSAGE);
  const stop = Math.max(cut.lastIndexOf(". "), cut.lastIndexOf("? "), cut.lastIndexOf("! "));
  return `${stop > 120 ? cut.slice(0, stop + 1) : cut.trimEnd()} …`;
}

/**
 * Step 2 and 3: keep the passages that carry the question's terms, in the
 * order they appear in the section, and quote them verbatim.
 */
export function composeLocalAnswer(
  question: string,
  sections: IndexedSection[],
  matched: boolean
): { answer: string; quoted: number } {
  const query = [...new Set(tokenize(question))];

  if (!matched) {
    const listing = sections
      .map((section) => `- **${section.citation.title}** — ${section.citation.summary}`)
      .join("\n");
    return {
      answer: `No section of the index matches that question, so there is nothing to quote. These are the nodes it opened instead:\n\n${listing}\n\nRephrase the question, or ask about a capability, endpoint, or setup step the wiki covers.`,
      quoted: 0,
    };
  }

  const parts: string[] = [];
  let quoted = 0;

  for (const section of sections) {
    const blocks = splitBlocks(section.body);
    const ranked = blocks
      .map((block, index) => {
        const terms = new Set(tokenize(block));
        const hits = query.filter((token) => terms.has(token)).length;
        const headingPenalty = block.startsWith("#") ? 100 : 0;
        return { block, index, score: hits - headingPenalty };
      })
      .filter((entry) => entry.score > 0)
      .sort((a, b) => b.score - a.score || a.index - b.index);

    const chosen = (ranked.length > 0 ? ranked.slice(0, 2) : blocks.slice(0, 1).map((block, index) => ({ block, index, score: 0 })))
      .sort((a, b) => a.index - b.index)
      .map((entry) => trimPassage(entry.block));

    const passages = chosen.filter(Boolean);
    if (passages.length === 0) continue;
    quoted += passages.length;
    parts.push(
      `**${section.citation.title}**\n\n${passages.join("\n\n")}`
    );
  }

  if (parts.length === 0) {
    return {
      answer:
        "The sections that matched carry no prose to quote. Open the cited node in the wiki and read it directly.",
      quoted: 0,
    };
  }

  const lead =
    sections.length === 1
      ? "The index routed this question to one section. Quoted from the generated page:"
      : `The index routed this question to ${sections.length} sections. Quoted from the generated pages:`;

  return { answer: `${lead}\n\n${parts.join("\n\n")}`, quoted };
}
