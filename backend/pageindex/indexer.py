"""
PageIndex tree indexer.
Parses markdown files in a repository documentation directory,
generates dense semantic summaries per section, and outputs pageindex_tree.json.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.pageindex.llm import LLMClient, fallback_summarize
from backend.pageindex.parser import SectionNode, parse_markdown_sections


class TreeIndexer:
    def __init__(
        self,
        content_dir: str | Path,
        llm_client: Optional[LLMClient] = None,
    ):
        self.content_dir = Path(content_dir).resolve()
        self.llm = llm_client or LLMClient()

    async def summarize_section(self, section: SectionNode) -> str:
        """Generate a dense 1-2 sentence semantic summary for a section."""
        if not self.llm.is_configured():
            return fallback_summarize(section.title, section.content)

        prompt = (
            "You are an expert technical documentation indexer. "
            "Write a dense, factual 1 to 2 sentence semantic summary of this documentation section. "
            "Focus on what architecture components, protocols, constraints, or invariants it defines. "
            "Do not include meta phrases like 'This section discusses'.\n\n"
            f"Section Title: {section.title}\n"
            f"File: {section.file}\n"
            f"Content:\n{section.content[:3000]}\n\n"
            "Summary:"
        )

        try:
            summary = await self.llm.complete(
                prompt=prompt,
                system="You produce dense, highly informative 1-2 sentence technical summaries.",
                temperature=0.1,
            )
            summary = summary.strip().strip('"').replace("\n", " ")
            return summary if summary else fallback_summarize(section.title, section.content)
        except Exception:
            return fallback_summarize(section.title, section.content)

    async def build_repo_tree(
        self,
        repo_name: str,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Builds pageindex_tree.json for the specified repository."""
        repo_path = self.content_dir / repo_name
        if not repo_path.is_dir():
            raise FileNotFoundError(f"Repository directory not found: {repo_path}")

        # Check toc.json to preserve canonical page order
        toc_path = repo_path / "toc.json"
        ordered_files: List[str] = []
        if toc_path.exists():
            try:
                with open(toc_path, "r", encoding="utf-8") as f:
                    toc_data = json.load(f)
                    for page in toc_data.get("pages", []):
                        slug = page.get("slug")
                        if slug:
                            ordered_files.append(f"{slug}.md")
            except Exception:
                pass

        # If any markdown files in repo are not in toc, append them
        for md_file in sorted(repo_path.glob("*.md")):
            if md_file.name not in ordered_files:
                ordered_files.append(md_file.name)

        all_sections: List[SectionNode] = []
        for filename in ordered_files:
            file_path = repo_path / filename
            if not file_path.exists():
                continue

            slug = file_path.stem
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            sections = parse_markdown_sections(content, slug=slug, target_levels=(2,))
            all_sections.extend(sections)

        async def summarize_node(sec: SectionNode) -> Dict[str, Any]:
            summary = await self.summarize_section(sec)
            return {
                "node_id": sec.node_id,
                "file": sec.file,
                "title": sec.title,
                "level": sec.level,
                "summary": summary,
            }

        nodes = list(await asyncio.gather(*[summarize_node(s) for s in all_sections]))
        tree = {
            "repo": repo_name,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "nodes": nodes,
        }

        if not dry_run:
            out_file = repo_path / "pageindex_tree.json"
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(tree, f, indent=2)

        return tree


async def main():
    parser = argparse.ArgumentParser(description="Build PageIndex tree for a repo")
    parser.add_argument("repo", help="Repository folder name under content/")
    parser.add_argument(
        "--content-dir",
        default=os.environ.get("CONTENT_DIR", "content"),
        help="Path to content directory",
    )
    args = parser.parse_args()

    indexer = TreeIndexer(content_dir=args.content_dir)
    tree = await indexer.build_repo_tree(args.repo)
    print(f"Indexed {len(tree['nodes'])} nodes for '{args.repo}' into pageindex_tree.json")


if __name__ == "__main__":
    asyncio.run(main())
