import {
  slugifyHeading,
  type PageIndexNode,
  type PageIndexTree,
} from "@/lib/stations";
import { getRepoPageIndexTree, getRepoPageMarkdown, getRepoToc } from "@/lib/wiki";
import type { ChatCitation, ChatStep } from "@/lib/chat";

const STOPWORDS: Record<string, true> = {
  a: true, an: true, and: true, are: true, as: true, at: true, be: true, by: true,
  for: true, from: true, has: true, he: true, in: true, is: true, it: true, its: true,
  of: true, on: true, that: true, the: true, to: true, was: true, were: true,
  will: true, with: true, how: true, what: true, where: true, when: true, why: true,
  who: true, which: true, does: true, do: true, did: true, can: true, could: true,
  should: true, would: true,
};

export interface ExtractedSection {
  node_id: string;
  file: string;
  title: string;
  level: number;
  content: string;
}

/**
 * Extracts a specific section's markdown content by its anchor/node_id.
 * Scans markdown lines starting at the matching heading until the next heading of equal or higher level.
 */
export function extractSectionMarkdown(
  markdown: string,
  nodeId: string
): { title: string; content: string; level: number } | null {
  const targetAnchor = nodeId.includes("#") ? nodeId.split("#")[1] : nodeId;
  const lines = markdown.split("\n");

  let inSection = false;
  let sectionLevel = 0;
  let sectionTitle = "";
  const sectionLines: string[] = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const match = line.match(/^(#{2,4})\s+(.+)$/);

    if (match) {
      const level = match[1].length;
      const rawHeading = match[2].trim();
      const anchor = slugifyHeading(rawHeading);

      if (inSection) {
        // If we hit a heading of equal or higher level, section is over
        if (level <= sectionLevel) {
          break;
        }
        sectionLines.push(line);
      } else if (anchor === targetAnchor) {
        inSection = true;
        sectionLevel = level;
        sectionTitle = rawHeading.replace(/[`*_~]/g, "").trim();
        sectionLines.push(line);
      }
    } else if (inSection) {
      sectionLines.push(line);
    }
  }

  if (!inSection) {
    return null;
  }

  return {
    title: sectionTitle,
    content: sectionLines.join("\n").trim(),
    level: sectionLevel,
  };
}

/**
 * Deterministic vectorless PageIndex search across node titles, summaries, and IDs.
 */
export function searchTreeNodes(
  tree: PageIndexTree,
  query: string,
  topK = 3
): { thought: string; nodes: PageIndexNode[] } {
  const clean = query.toLowerCase().replace(/[^\w\s-]/g, " ");
  const rawTerms = clean.split(/\s+/).filter(Boolean);
  const terms = rawTerms.filter((t) => !STOPWORDS[t] && t.length > 1);
  const activeTerms = terms.length > 0 ? terms : rawTerms;

  const scored: { score: number; node: PageIndexNode }[] = tree.nodes.map((node) => {
    let score = 0;
    const nid = node.node_id.toLowerCase();
    const title = node.title.toLowerCase();
    const summary = node.summary.toLowerCase();

    for (const term of activeTerms) {
      if (nid.includes(term)) score += 3.0;
      if (title.includes(term)) score += 4.0;
      if (summary.includes(term)) score += 1.5;

      const stem = term.length >= 5 ? term.slice(0, 5) : term;
      if (nid.includes(stem)) score += 1.0;
      if (title.includes(stem)) score += 1.5;
      if (summary.includes(stem)) score += 0.8;
    }

    return { score, node };
  });

  scored.sort((a, b) => b.score - a.score);

  const matched = scored.filter((s) => s.score > 0).map((s) => s.node);
  const nodes = (matched.length > 0 ? matched : tree.nodes.slice(0, 1)).slice(0, topK);

  const names = nodes.map((n) => `'${n.title}'`).join(", ");
  const thought = `Navigated PageIndex tree for '${activeTerms.slice(0, 4).join(" ")}'. Selected ${nodes.length} section(s): ${names}.`;

  return { thought, nodes };
}

/**
 * Local vectorless reasoning stream that navigates pageindex_tree.json and extracts markdown sections.
 */
export async function* localPageIndexChat(
  repoName: string,
  messages: { role: string; content: string }[]
): AsyncIterable<{ event: string; data: Record<string, unknown> }> {
  const tree = await getRepoPageIndexTree(repoName);
  if (!tree) {
    yield {
      event: "error",
      data: { error: `Tree index not found for repository '${repoName}'` },
    };
    return;
  }

  const userQuery =
    [...messages].reverse().find((m) => m.role === "user")?.content ??
    "System Overview";

  // Step 1: Tree Navigation
  const { thought, nodes } = searchTreeNodes(tree, userQuery, 3);

  yield {
    event: "reasoning",
    data: {
      type: "step",
      step: "Inspecting PageIndex tree",
      thought,
      message: thought,
    },
  };

  // Step 2: Section Extraction
  const extractedSections: ExtractedSection[] = [];
  for (const node of nodes) {
    const slug = node.file.replace(/\.md$/, "");
    const md = await getRepoPageMarkdown(repoName, slug);
    if (!md) continue;

    yield {
      event: "reasoning",
      data: {
        type: "step",
        step: "Opened section",
        detail: node.node_id,
        message: `Opened ${node.file}#${node.node_id.split("#")[1] || ""}`,
      },
    };

    const sec = extractSectionMarkdown(md, node.node_id);
    if (sec) {
      extractedSections.push({
        node_id: node.node_id,
        file: node.file,
        title: sec.title || node.title,
        level: sec.level,
        content: sec.content,
      });
    } else {
      extractedSections.push({
        node_id: node.node_id,
        file: node.file,
        title: node.title,
        level: node.level,
        content: md.slice(0, 1500),
      });
    }
  }

  // Citations event
  yield {
    event: "citations",
    data: {
      type: "nodes",
      nodes: extractedSections.map((s) => ({
        node_id: s.node_id,
        title: s.title,
        file: s.file,
      })),
    },
  };

  // Step 3: Synthesis & Streaming
  const synthesis = [
    `Based on **PageIndex tree retrieval** across \`${repoName}\`, verified specifications were extracted from ${extractedSections.length} section(s):\n`,
  ];

  for (const sec of extractedSections) {
    synthesis.push(`\n### [${sec.title}](/wiki/${repoName}/${sec.node_id}) (\`${sec.node_id}\`)\n`);
    const bodyLines = sec.content
      .split("\n")
      .filter((line) => !line.startsWith("#"))
      .join("\n")
      .trim();
    synthesis.push(bodyLines);
  }

  synthesis.push("\n\n*Retrieved directly via PageIndex vectorless tree search without embeddings.*");

  const fullText = synthesis.join("\n");
  const words = fullText.split(/(\s+)/);

  for (const word of words) {
    if (word) {
      yield {
        event: "token",
        data: {
          type: "token",
          delta: word,
        },
      };
      const { promise, resolve } = Promise.withResolvers<void>();
      setTimeout(resolve, 12);
      await promise;
    }
  }

  // Done event
  yield {
    event: "done",
    data: {
      type: "done",
      finish_reason: "stop",
      engine: "local",
    },
  };
}

export interface IndexedSection {
  citation: ChatCitation;
  body: string;
}

export interface RoutingResult {
  sections: IndexedSection[];
  steps: ChatStep[];
  matched: boolean;
}

/**
 * Loads indexed sections with full content bodies for advanced ranking.
 */
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

  const byFile = new Map<string, string>();
  for (const page of pages) {
    byFile.set(`${page.slug}.md`, page.markdown);
  }

  const sections: IndexedSection[] = tree.nodes.map((node) => {
    const md = byFile.get(node.file) ?? "";
    const extracted = extractSectionMarkdown(md, node.node_id);
    return {
      citation: {
        node_id: node.node_id,
        title: node.title,
        file: node.file,
        summary: node.summary,
      },
      body: extracted?.content ?? "",
    };
  });

  return { sections, pageCount: toc.pages.length };
}

/**
 * Helper to route question using PageIndex tree search.
 */
export async function routeQuestion(
  repoName: string,
  question: string,
  limit = 3
): Promise<RoutingResult | null> {
  const tree = await getRepoPageIndexTree(repoName);
  if (!tree) return null;

  const { thought, nodes } = searchTreeNodes(tree, question, limit);
  const sections: IndexedSection[] = [];

  for (const node of nodes) {
    const slug = node.file.replace(/\.md$/, "");
    const md = await getRepoPageMarkdown(repoName, slug);
    const extracted = md ? extractSectionMarkdown(md, node.node_id) : null;
    sections.push({
      citation: {
        node_id: node.node_id,
        title: node.title,
        file: node.file,
        summary: node.summary,
      },
      body: extracted?.content ?? "",
    });
  }

  const steps: ChatStep[] = [
    { step: "Navigating PageIndex tree", detail: thought },
    ...nodes.map((n) => ({
      step: "Selected section",
      detail: n.node_id,
    })),
  ];

  return {
    sections,
    steps,
    matched: nodes.length > 0,
  };
}

/**
 * Helper to compose answer from retrieved sections.
 */
export function composeLocalAnswer(
  _question: string,
  sections: IndexedSection[],
  matched: boolean
): { answer: string; quoted: number } {
  if (!matched || sections.length === 0) {
    return {
      answer: "No section in the PageIndex tree matched the query.",
      quoted: 0,
    };
  }

  const parts = sections.map((s) => `### ${s.citation.title}\n\n${s.body}`);
  return {
    answer: parts.join("\n\n"),
    quoted: sections.length,
  };
}
