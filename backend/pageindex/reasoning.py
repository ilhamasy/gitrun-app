"""
PageIndex reasoning and retrieval engine.
Executes 3-step vectorless reasoning:
1. Tree Navigation (LLM or ranker selects 1-3 relevant node_ids)
2. Section Extraction (reads exact markdown text for selected node_ids)
3. Synthesis & Streaming (streams answer token-by-token with node citations)
"""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

from backend.pageindex.llm import LLMClient
from backend.pageindex.parser import SectionNode, extract_section_by_node_id, parse_markdown_sections

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "he",
    "in", "is", "it", "its", "of", "on", "that", "the", "to", "was", "were",
    "will", "with", "how", "what", "where", "when", "why", "who", "which",
    "does", "do", "did", "can", "could", "should", "would"
}


@dataclass
class RetrievedSection:
    node_id: str
    file: str
    title: str
    level: int
    content: str
    repo: str = ""


@dataclass
class ReasoningEvent:
    event: str
    data: Dict[str, Any]

    def to_sse(self) -> str:
        """Format as SSE event and data line."""
        payload = json.dumps(self.data)
        return f"event: {self.event}\ndata: {payload}\n\n"


class PageIndexEngine:
    def __init__(
        self,
        content_dir: str | Path,
        llm_client: Optional[LLMClient] = None,
    ):
        self.content_dir = Path(content_dir).resolve()
        self.llm = llm_client or LLMClient()

    def load_tree(self, repo_name: str) -> Dict[str, Any]:
        """Loads pageindex_tree.json for a repository."""
        tree_path = self.content_dir / repo_name / "pageindex_tree.json"
        if not tree_path.exists():
            raise FileNotFoundError(f"Tree index not found at {tree_path}")
        with open(tree_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # -- corpus loading ---------------------------------------------------

    def available_repos(self) -> List[str]:
        """Every repository that currently has a tree index on disk."""
        repos: List[str] = []
        if not self.content_dir.exists():
            return repos
        for child in sorted(self.content_dir.iterdir()):
            if not child.is_dir() or child.name.startswith("."):
                continue
            if (child / "pageindex_tree.json").exists():
                repos.append(child.name)
        return repos

    def load_corpus(
        self,
        repos: Optional[List[str]] = None,
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Loads one flat node list across every requested repository.

        Each node keeps the repository it came from, because a citation from a
        cross-line answer has to link back to the right line, not to whichever
        line happened to be selected in the UI.

        Returns (nodes, repos_loaded).
        """
        targets = repos if repos else self.available_repos()
        nodes: List[Dict[str, Any]] = []
        loaded: List[str] = []

        for repo_name in targets:
            try:
                tree = self.load_tree(repo_name)
            except (FileNotFoundError, json.JSONDecodeError, OSError):
                continue
            loaded.append(repo_name)
            for node in tree.get("nodes", []):
                nodes.append({**node, "repo": repo_name})

        return nodes, loaded

    async def navigate_corpus(
        self,
        query: str,
        repos: Optional[List[str]] = None,
        top_k: int = 5,
    ) -> Tuple[str, List[Dict[str, Any]], List[str]]:
        """
        Step 1 across one or many repositories.

        With a single repository this is the original behaviour. With several,
        the ranker sees every node from every line and the answer may cite
        sections from more than one wiki.
        """
        nodes, loaded = self.load_corpus(repos)
        if not nodes:
            return "No tree index was found for the requested scope.", [], loaded

        if not self.llm.is_configured():
            thought, selected = self.fallback_select_nodes(query, nodes, top_k=top_k)
            return thought, selected, loaded

        index_summary = []
        for n in nodes:
            index_summary.append(
                f"- repo: {n.get('repo')}\n"
                f"  node_id: {n.get('node_id')}\n"
                f"  title: {n.get('title')}\n"
                f"  file: {n.get('file')}\n"
                f"  summary: {n.get('summary')}"
            )
        formatted_index = "\n".join(index_summary)

        scope = (
            f"{len(loaded)} repositories ({', '.join(loaded)})"
            if len(loaded) > 1
            else f"repository '{loaded[0]}'"
        )

        prompt = (
            "You are the PageIndex Retrieval Navigator for GoWiki.\n"
            f"You are searching across {scope}.\n"
            "Analyze the user's question and select the 1 to 5 most relevant nodes from the tree index.\n"
            "Nodes are grouped by repository; prefer nodes that directly answer the question.\n"
            "If the question asks to compare services or find a problem across services, "
            "select nodes from multiple repositories.\n\n"
            "Tree Index:\n"
            f"{formatted_index}\n\n"
            f"User Question: {query}\n\n"
            "Return strictly valid JSON in this exact structure:\n"
            "{\n"
            '  "thought": "1-2 sentence explanation of why these nodes answer the query",\n'
            '  "selected_node_ids": ["<node_id_1>", "<node_id_2>"]\n'
            "}"
        )

        try:
            resp_text = await self.llm.complete(
                prompt=prompt,
                system="You are a precise technical document retrieval engine. Return valid JSON only.",
                json_mode=True,
                temperature=0.0,
            )
            data = json.loads(resp_text)
            selected_ids = data.get("selected_node_ids", [])
            thought = data.get("thought", "Selected relevant tree nodes.")

            by_id: Dict[str, List[Dict[str, Any]]] = {}
            for node in nodes:
                by_id.setdefault(node["node_id"], []).append(node)

            selected: List[Dict[str, Any]] = []
            for nid in selected_ids:
                for candidate in by_id.get(nid, []):
                    if candidate not in selected:
                        selected.append(candidate)

            if not selected:
                thought, selected = self.fallback_select_nodes(query, nodes, top_k=top_k)

            return thought, selected[:top_k], loaded
        except Exception:
            thought, selected = self.fallback_select_nodes(query, nodes, top_k=top_k)
            return thought, selected, loaded

    def extract_corpus_sections(
        self,
        selected_nodes: List[Dict[str, Any]],
    ) -> List[RetrievedSection]:
        """Step 2 across repositories; each section remembers its line."""
        retrieved: List[RetrievedSection] = []

        for node in selected_nodes:
            repo_name = node.get("repo", "")
            node_id = node.get("node_id", "")
            filename = node.get("file", "")
            title = node.get("title", "")
            level = node.get("level", 2)

            file_path = self.content_dir / repo_name / filename
            if not file_path.exists():
                continue

            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            sec = extract_section_by_node_id(
                content, slug=file_path.stem, target_node_id=node_id
            )
            if sec:
                retrieved.append(
                    RetrievedSection(
                        node_id=sec.node_id,
                        file=sec.file,
                        title=sec.title,
                        level=sec.level,
                        content=sec.content,
                        repo=repo_name,
                    )
                )
            else:
                retrieved.append(
                    RetrievedSection(
                        node_id=node_id,
                        file=filename,
                        title=title,
                        level=level,
                        content=content[:2000],
                        repo=repo_name,
                    )
                )

        return retrieved

    def fallback_select_nodes(
        self,
        query: str,
        nodes: List[Dict[str, Any]],
        top_k: int = 3,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Deterministic keyword & semantic ranker for tree navigation when LLM is offline.
        """
        clean_query = re.sub(r"[^\w\s-]", " ", query.lower())
        raw_terms = [t.strip() for t in clean_query.split() if t.strip()]
        terms = [t for t in raw_terms if t not in STOPWORDS and len(t) > 1]
        if not terms:
            terms = raw_terms

        scored: List[Tuple[float, Dict[str, Any]]] = []

        for node in nodes:
            node_id = node.get("node_id", "").lower()
            title = node.get("title", "").lower()
            summary = node.get("summary", "").lower()

            score = 0.0
            for term in terms:
                # Direct match in node_id or title has high weight
                if term in node_id:
                    score += 3.0
                if term in title:
                    score += 4.0
                if term in summary:
                    score += 1.5

                # Partial root match (e.g. 'charge' in 'charging', 'idempotent' in 'idempotency')
                stem = term[:5] if len(term) >= 5 else term
                if stem in node_id:
                    score += 1.0
                if stem in title:
                    score += 1.5
                if stem in summary:
                    score += 0.8

            scored.append((score, node))

        scored.sort(key=lambda x: x[0], reverse=True)

        # Pick top nodes with non-zero score
        candidates = [node for score, node in scored if score > 0]
        if not candidates and nodes:
            # Fallback to the first overview or architecture node
            candidates = [nodes[0]]

        selected = candidates[:top_k]
        names = ", ".join(f"'{n.get('title')}'" for n in selected)
        thought = (
            f"Searched document tree for '{' '.join(terms[:4])}'. "
            f"Matched {len(selected)} relevant section(s): {names}."
        )
        return thought, selected

    async def navigate_tree(
        self,
        repo_name: str,
        query: str,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Step 1: Tree Navigation.
        Prompts LLM to reason over tree index to choose 1-3 most relevant node_ids.
        Falls back to deterministic keyword ranker if LLM is offline.
        """
        tree = self.load_tree(repo_name)
        nodes: List[Dict[str, Any]] = tree.get("nodes", [])
        if not nodes:
            return "Tree index is empty.", []

        if not self.llm.is_configured():
            return self.fallback_select_nodes(query, nodes)

        # Format node summaries for LLM prompt
        index_summary = []
        for n in nodes:
            index_summary.append(
                f"- node_id: {n.get('node_id')}\n"
                f"  title: {n.get('title')}\n"
                f"  file: {n.get('file')}\n"
                f"  summary: {n.get('summary')}"
            )
        formatted_index = "\n".join(index_summary)

        prompt = (
            "You are the PageIndex Retrieval Navigator for GoWiki.\n"
            "Analyze the user's question and select the 1 to 3 most relevant node_id values from the tree index.\n\n"
            "Tree Index:\n"
            f"{formatted_index}\n\n"
            f"User Question: {query}\n\n"
            "Return strictly valid JSON in this exact structure:\n"
            "{\n"
            '  "thought": "1-2 sentence explanation of why these nodes answer the query",\n'
            '  "selected_node_ids": ["<node_id_1>", "<node_id_2>"]\n'
            "}"
        )

        try:
            resp_text = await self.llm.complete(
                prompt=prompt,
                system="You are a precise technical document retrieval engine. Return valid JSON only.",
                json_mode=True,
                temperature=0.0,
            )
            data = json.loads(resp_text)
            selected_ids = data.get("selected_node_ids", [])
            thought = data.get("thought", "Selected relevant tree nodes.")

            # Filter valid nodes
            node_map = {n["node_id"]: n for n in nodes}
            selected_nodes = [node_map[nid] for nid in selected_ids if nid in node_map]

            if not selected_nodes:
                return self.fallback_select_nodes(query, nodes)

            return thought, selected_nodes[:3]
        except Exception:
            return self.fallback_select_nodes(query, nodes)

    def extract_sections(
        self,
        repo_name: str,
        selected_nodes: List[Dict[str, Any]],
    ) -> List[RetrievedSection]:
        """
        Step 2: Section Extraction.
        Reads exact markdown files and extracts section text matching selected node_ids.
        """
        retrieved: List[RetrievedSection] = []
        repo_dir = self.content_dir / repo_name

        for node in selected_nodes:
            node_id = node.get("node_id", "")
            filename = node.get("file", "")
            title = node.get("title", "")
            level = node.get("level", 2)

            file_path = repo_dir / filename
            if not file_path.exists():
                continue

            slug = file_path.stem
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            sec = extract_section_by_node_id(content, slug=slug, target_node_id=node_id)
            if sec:
                retrieved.append(
                    RetrievedSection(
                        node_id=sec.node_id,
                        file=sec.file,
                        title=sec.title,
                        level=sec.level,
                        content=sec.content,
                        repo=repo_name,
                    )
                )
            else:
                # If exact section not cleanly bounded, find the heading or pass full content
                retrieved.append(
                    RetrievedSection(
                        node_id=node_id,
                        file=filename,
                        title=title,
                        level=level,
                        content=content[:2000],
                        repo=repo_name,
                    )
                )

        return retrieved

    async def stream_chat(
        self,
        repo_name: str,
        messages: List[Dict[str, str]],
    ) -> AsyncIterator[ReasoningEvent]:
        """
        Step 3: Synthesis & Streaming.
        Yields reasoning, citations, token deltas, and done events.
        """
        user_query = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                user_query = m.get("content", "")
                break

        if not user_query:
            user_query = "Overview of this repository"

        # Step 1: Tree Navigation
        thought, selected_nodes = await self.navigate_tree(repo_name, user_query)

        # Emit reasoning step
        yield ReasoningEvent(
            event="reasoning",
            data={
                "type": "step",
                "step": "inspecting_tree",
                "thought": thought,
                "message": f"Inspected tree: selected {len(selected_nodes)} node(s)",
            },
        )

        # Step 2: Section Extraction
        sections = self.extract_sections(repo_name, selected_nodes)

        # Emit citations
        citations = [
            {
                "node_id": s.node_id,
                "title": s.title,
                "file": s.file,
                "repo": s.repo,
            }
            for s in sections
        ]
        yield ReasoningEvent(
            event="citations",
            data={
                "type": "nodes",
                "nodes": citations,
            },
        )

        # Step 3: Synthesis
        if self.llm.is_configured():
            context_blocks = []
            for s in sections:
                context_blocks.append(
                    f"### Node: [{s.node_id}] ({s.file})\n"
                    f"Title: {s.title}\n\n"
                    f"{s.content}"
                )
            context_str = "\n\n---\n\n".join(context_blocks)

            system_prompt = (
                "You are GoWiki Assistant, an autonomous technical documentation expert.\n"
                "Answer the user's question accurately using ONLY the provided documentation sections below.\n"
                "When referencing facts, rules, or steps, cite the node id in brackets like `[architecture#distributed-idempotency-protocol]`.\n"
                "Provide code snippets, parameters, or configurations whenever relevant.\n\n"
                f"Authoritative Documentation Context:\n{context_str}"
            )

            try:
                async for chunk in self.llm.stream_chat(
                    messages=messages,
                    system=system_prompt,
                    temperature=0.2,
                ):
                    yield ReasoningEvent(
                        event="token",
                        data={"type": "token", "delta": chunk},
                    )
            except Exception as e:
                # LLM stream error fallback
                fallback_text = (
                    f"Encountered an issue communicating with the LLM gateway ({e}). "
                    f"Here is the verified documentation from the retrieved nodes:\n\n"
                )
                for s in sections:
                    fallback_text += f"#### [{s.title}](/wiki/{repo_name}/{s.node_id})\n{s.content}\n\n"
                for word in fallback_text.split(" "):
                    yield ReasoningEvent(
                        event="token",
                        data={"type": "token", "delta": word + " "},
                    )
                    await asyncio.sleep(0.01)
        else:
            # Grounded offline synthesizer
            offline_synthesis = self._synthesize_offline(repo_name, user_query, sections)
            tokens = re.split(r"(\s+)", offline_synthesis)
            for token in tokens:
                if token:
                    yield ReasoningEvent(
                        event="token",
                        data={"type": "token", "delta": token},
                    )
                    await asyncio.sleep(0.015)

        # Emit completion
        yield ReasoningEvent(
            event="done",
            data={"type": "done", "finish_reason": "stop"},
        )

    async def stream_corpus_chat(
        self,
        messages: List[Dict[str, str]],
        repos: Optional[List[str]] = None,
    ) -> AsyncIterator[ReasoningEvent]:
        """
        Answers a question by searching every selected repository's tree.

        `repos=None` means the whole wiki board: the ranker sees every node from
        every line, so a question about a problem can land on whichever service
        actually contains it. Passing one repository narrows the search to that
        line and reproduces the per-line behaviour.
        """
        user_query = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                user_query = m.get("content", "")
                break
        if not user_query:
            user_query = "Summarize the documented projects"

        thought, selected_nodes, loaded = await self.navigate_corpus(
            user_query, repos=repos
        )

        scope_label = (
            ", ".join(loaded) if loaded else "no indexed repositories"
        )
        yield ReasoningEvent(
            event="reasoning",
            data={
                "type": "step",
                "step": "inspecting_tree",
                "thought": thought,
                "message": (
                    f"Searched {len(loaded)} line(s) and selected "
                    f"{len(selected_nodes)} node(s)"
                ),
                "repos": loaded,
            },
        )

        if not selected_nodes:
            yield ReasoningEvent(
                event="citations",
                data={"type": "nodes", "nodes": []},
            )
            yield ReasoningEvent(
                event="token",
                data={
                    "type": "token",
                    "delta": (
                        f"No indexed section in {scope_label} matched that question. "
                        "Narrow the scope to one line, or ingest the repository you "
                        "expected to find."
                    ),
                },
            )
            yield ReasoningEvent(
                event="done",
                data={"type": "done", "finish_reason": "stop", "engine": "local"},
            )
            return

        sections = self.extract_corpus_sections(selected_nodes)

        citations = [
            {
                "node_id": s.node_id,
                "title": s.title,
                "file": s.file,
                "repo": s.repo,
            }
            for s in sections
        ]
        yield ReasoningEvent(
            event="citations",
            data={"type": "nodes", "nodes": citations},
        )

        # Step 3: Synthesis
        if self.llm.is_configured():
            context_blocks = []
            for s in sections:
                context_blocks.append(
                    f"### Line: {s.repo} | Node: [{s.node_id}] ({s.file})\n"
                    f"Title: {s.title}\n\n"
                    f"{s.content}"
                )
            context_str = "\n\n---\n\n".join(context_blocks)

            multi = len(loaded) > 1
            scope_rule = (
                f"The excerpts come from {len(loaded)} different repositories "
                f"({', '.join(loaded)}). Name the repository for every claim, and do not "
                "merge two repositories' behaviour into one statement."
                if multi
                else "All excerpts come from one repository."
            )

            system_prompt = (
                "You are GoWiki Assistant, an autonomous technical documentation expert.\n"
                "Answer the user's question accurately using ONLY the provided documentation sections below.\n"
                "When referencing facts, rules, or steps, cite the node id in brackets like "
                "`[line: architecture#distributed-idempotency-protocol]`.\n"
                f"{scope_rule}\n"
                "If the excerpts do not contain the answer, say which repositories you "
                "searched and that the answer was not found. Never invent one.\n\n"
                f"Authoritative Documentation Context:\n{context_str}"
            )

            try:
                async for chunk in self.llm.stream_chat(
                    messages=messages,
                    system=system_prompt,
                    temperature=0.2,
                ):
                    yield ReasoningEvent(
                        event="token",
                        data={"type": "token", "delta": chunk},
                    )
                yield ReasoningEvent(
                    event="done",
                    data={"type": "done", "finish_reason": "stop", "engine": "model"},
                )
                return
            except Exception as e:
                fallback_text = (
                    f"The model gateway was unreachable ({e}). "
                    "Here are the retrieved sections verbatim:\n\n"
                )
                for s in sections:
                    fallback_text += (
                        f"#### {s.repo} · [{s.title}](/wiki/{s.repo}/"
                        f"{s.node_id.split('#')[0]}#{s.node_id.split('#')[1]})\n"
                        f"{s.content}\n\n"
                    )
                for word in fallback_text.split(" "):
                    yield ReasoningEvent(
                        event="token",
                        data={"type": "token", "delta": word + " "},
                    )
                    await asyncio.sleep(0.01)
                yield ReasoningEvent(
                    event="done",
                    data={"type": "done", "finish_reason": "stop", "engine": "local"},
                )
                return

        offline = self._synthesize_offline_multi(user_query, sections, loaded)
        for token in re.split(r"(\s+)", offline):
            if token:
                yield ReasoningEvent(
                    event="token",
                    data={"type": "token", "delta": token},
                )
                await asyncio.sleep(0.015)

        yield ReasoningEvent(
            event="done",
            data={"type": "done", "finish_reason": "stop", "engine": "local"},
        )

    def _synthesize_offline_multi(
        self,
        query: str,
        sections: List[RetrievedSection],
        loaded: List[str],
    ) -> str:
        """Offline answer that names the line each passage came from."""
        if not sections:
            return (
                f"No indexed section in {len(loaded)} line(s) matched: \"{query}\". "
                "Browse the wiki pages directly."
            )

        repos_hit = sorted({s.repo for s in sections if s.repo})
        parts = [
            f"Searching {len(loaded)} line(s) ({', '.join(loaded)}), "
            f"{len(sections)} section(s) matched the question across "
            f"{len(repos_hit)} line(s): {', '.join(repos_hit)}.\n"
        ]

        for sec in sections:
            anchor = sec.node_id.split("#")[-1]
            parts.append(
                f"\n### {sec.repo} · [{sec.title}](/wiki/{sec.repo}/"
                f"{sec.node_id.split('#')[0]}#{anchor}) (`{sec.node_id}`)\n"
            )
            body = "\n".join(
                line for line in sec.content.split("\n") if not line.startswith("#")
            ).strip()
            parts.append(body)

        parts.append(
            "\n\n*Retrieved via PageIndex vectorless tree search across the selected "
            "lines, without embeddings.*"
        )
        return "\n".join(parts)

    def _synthesize_offline(
        self,
        repo_name: str,
        query: str,
        sections: List[RetrievedSection],
    ) -> str:
        """
        Synthesizes a grounded technical answer from extracted sections when LLM is offline.
        """
        if not sections:
            return (
                f"No specific documentation sections matched the query: \"{query}\". "
                f"Please browse the wiki pages directly."
            )

        parts = []
        parts.append(
            f"Based on the **PageIndex tree search** across `{repo_name}`, "
            f"the relevant technical specifications were retrieved from {len(sections)} section(s):\n"
        )

        for sec in sections:
            line = sec.repo or repo_name
            anchor_link = f"/wiki/{line}/{sec.node_id.replace('#', '#')}"
            parts.append(f"\n### [{sec.title}]({anchor_link}) (`{sec.node_id}`)\n")

            # Extract clean content without duplicate heading
            lines = sec.content.split("\n")
            body_lines = [l for l in lines if not l.startswith("#")]
            body = "\n".join(body_lines).strip()
            parts.append(body)

        parts.append(
            f"\n\n*Retrieved directly via PageIndex vectorless tree navigation without embeddings.*"
        )
        return "\n".join(parts)
