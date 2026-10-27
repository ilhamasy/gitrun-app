"""
GoWiki Ingestion Pipeline.
Orchestrates clone, bundle, two-pass doc synthesis, and PageIndex tree generation.
Emits SSE streaming events following the master plan contract.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncIterator, Dict, Optional

from backend.ingestion.bundler import RepomixBundler
from backend.ingestion.cloner import RepoCloner
from backend.ingestion.synthesizer import DocSynthesizer
from backend.pageindex.indexer import TreeIndexer
from backend.pageindex.llm import LLMClient


@dataclass
class IngestionEvent:
    event: str
    data: Dict[str, Any]

    def to_sse(self) -> str:
        return f"event: {self.event}\ndata: {json.dumps(self.data)}\n\n"


class IngestionPipeline:
    def __init__(
        self,
        content_dir: str | Path,
        temp_dir: str | Path,
        llm_client: Optional[LLMClient] = None,
    ):
        self.content_dir = Path(content_dir).resolve()
        self.temp_dir = Path(temp_dir).resolve()
        self.llm = llm_client or LLMClient()

        self.cloner = RepoCloner(temp_dir=self.temp_dir, content_dir=self.content_dir)
        self.bundler = RepomixBundler(temp_dir=self.temp_dir)
        self.synthesizer = DocSynthesizer(content_dir=self.content_dir, llm_client=self.llm)
        self.indexer = TreeIndexer(content_dir=self.content_dir, llm_client=self.llm)

    async def run(
        self,
        source: str,
        branch: Optional[str] = None,
        name: Optional[str] = None,
    ) -> AsyncIterator[IngestionEvent]:
        """
        Executes end-to-end ingestion and streams SSE events.

        `branch` may be a branch or a tag; omitted means the remote's default
        branch. `name` overrides the wiki line name derived from the source.
        """
        try:
            # Step 1: Clone
            yield IngestionEvent(
                event="step",
                data={
                    "step": "clone",
                    "status": "running",
                    "message": (
                        f"Cloning {branch} (depth 1)..."
                        if branch
                        else "Cloning default branch (depth 1)..."
                    ),
                },
            )
            # Run cloner in executor to avoid blocking event loop on git subprocess
            cloned = await asyncio.to_thread(
                self.cloner.clone,
                source,
                branch,
                True,
                name,
            )
            repo_name, repo_dir = cloned.repo_name, cloned.repo_dir

            provenance = cloned.provenance
            yield IngestionEvent(
                event="step",
                data={
                    "step": "clone",
                    "status": "completed",
                    "message": (
                        f"Checked out {cloned.ref or cloned.branch or 'default branch'}"
                        + (f" at {cloned.short_commit}" if cloned.short_commit else "")
                    ),
                    "ref": cloned.ref or cloned.branch,
                    "commit": cloned.commit,
                },
            )

            # Step 2: Bundle
            yield IngestionEvent(
                event="step",
                data={
                    "step": "bundle",
                    "status": "running",
                    "message": "Packing codebase with Repomix...",
                },
            )
            bundle_path = await asyncio.to_thread(
                self.bundler.bundle,
                repo_dir,
                repo_name,
            )

            # Step 3: Pass 1 - Synthesize TOC
            yield IngestionEvent(
                event="step",
                data={
                    "step": "toc",
                    "status": "running",
                    "message": "Synthesizing Table of Contents...",
                },
            )
            toc = await self.synthesizer.pass1_generate_toc(
                repo_name=repo_name,
                bundle_path=bundle_path,
                provenance=provenance,
            )

            # Step 4: Pass 2 - Synthesize Pages in parallel with progress streaming
            event_queue: asyncio.Queue[IngestionEvent] = asyncio.Queue()

            async def progress_callback(completed: int, total: int, slug: str) -> None:
                await event_queue.put(
                    IngestionEvent(
                        event="step",
                        data={
                            "step": "doc_gen",
                            "status": "running",
                            "progress": f"{completed}/{total} pages generated",
                            "page": slug,
                        },
                    )
                )

            # Fire Pass 2 generation
            pages_task = asyncio.create_task(
                self.synthesizer.pass2_generate_pages(
                    repo_name=repo_name,
                    bundle_path=bundle_path,
                    toc=toc,
                    progress_callback=progress_callback,
                )
            )

            while not pages_task.done():
                try:
                    ev = await asyncio.wait_for(event_queue.get(), timeout=0.2)
                    yield ev
                except asyncio.TimeoutError:
                    pass

            # Flush remaining events from queue
            await pages_task
            while not event_queue.empty():
                yield event_queue.get_nowait()

            # Step 5: PageIndex Tree Construction
            yield IngestionEvent(
                event="step",
                data={
                    "step": "pageindex",
                    "status": "running",
                    "message": "Building hierarchical tree index...",
                },
            )
            await self.indexer.build_repo_tree(repo_name=repo_name)

            # Done
            yield IngestionEvent(
                event="done",
                data={
                    "step": "completed",
                    "repo": repo_name,
                    "branch": cloned.branch,
                    "ref": cloned.ref or cloned.branch,
                    "commit": cloned.commit,
                    "redirect": f"/wiki/{repo_name}/overview",
                },
            )

        except Exception as e:
            yield IngestionEvent(
                event="error",
                data={"error": str(e)},
            )
