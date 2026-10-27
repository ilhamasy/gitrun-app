"""
System Ingestion Pipeline for Multi-Repo Microservice Architectures.
Coordinates parallel clone, bundle, metadata extraction, individual service wiki generation,
federated system topology synthesis, cross-linking, and PageIndex tree construction.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional

from backend.ingestion.bundler import RepomixBundler
from backend.ingestion.cloner import RepoCloner
from backend.ingestion.mesh import (
    ServiceNodeInfo,
    SystemSynthesizer,
    extract_service_metadata,
)
from backend.ingestion.pipeline import IngestionEvent
from backend.ingestion.synthesizer import DocSynthesizer
from backend.pageindex.indexer import TreeIndexer
from backend.pageindex.llm import LLMClient


@dataclass
class MemberRepoInput:
    name: str
    url: str
    branch: Optional[str] = None


class SystemIngestionPipeline:
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
        self.system_synthesizer = SystemSynthesizer(content_dir=self.content_dir, llm_client=self.llm)
        self.indexer = TreeIndexer(content_dir=self.content_dir, llm_client=self.llm)

    async def run(
        self,
        system_name: str,
        repos: List[Dict[str, Any]],
        display_name: Optional[str] = None,
    ) -> AsyncIterator[IngestionEvent]:
        """
        Executes end-to-end multi-repo microservice mesh ingestion.
        """
        try:
            sys_clean = system_name.strip().lower().replace(" ", "-")
            disp_clean = display_name.strip() if display_name else sys_clean.replace("-", " ").title()

            # 1. System Init
            yield IngestionEvent(
                event="step",
                data={
                    "step": "system_init",
                    "status": "running",
                    "message": f"Initializing multi-repo mesh for {disp_clean} ({len(repos)} repositories)...",
                    "count": len(repos),
                },
            )

            # 2. Parallel Clone
            yield IngestionEvent(
                event="step",
                data={
                    "step": "clone_all",
                    "status": "running",
                    "message": f"Cloning {len(repos)} member repositories in parallel...",
                },
            )

            async def clone_member(repo_item: Dict[str, Any]):
                url = repo_item["url"]
                branch = repo_item.get("branch")
                # The member's declared name is the wiki line name, so it wins
                # over the one derived from the URL (which drops the owner and
                # would collide across same-named services).
                declared = repo_item.get("name") or None
                cloned = await asyncio.to_thread(
                    self.cloner.clone, url, branch, True, declared
                )
                return cloned

            cloned_results = await asyncio.gather(*[clone_member(r) for r in repos])
            repo_map: Dict[str, Path] = {
                c.repo_name: c.repo_dir for c in cloned_results
            }
            provenance_map: Dict[str, Dict[str, Any]] = {
                c.repo_name: c.provenance for c in cloned_results
            }

            # 3. Parallel Bundle
            yield IngestionEvent(
                event="step",
                data={
                    "step": "bundle_all",
                    "status": "running",
                    "message": "Bundling codebases with Repomix (stripping noise)...",
                },
            )

            async def bundle_member(name: str, path: Path):
                b_path = await asyncio.to_thread(self.bundler.bundle, path, name)
                return name, b_path

            bundled_results = await asyncio.gather(*[bundle_member(n, p) for n, p in repo_map.items()])
            bundle_map: Dict[str, Path] = {name: b_path for name, b_path in bundled_results}

            # Read bundle contents into memory map for topology analysis
            bundle_text_map: Dict[str, str] = {
                name: b_path.read_text(encoding="utf-8", errors="replace")
                for name, b_path in bundle_map.items()
            }

            # 4. Synthesize Member Repositories & Extract Metadata
            yield IngestionEvent(
                event="step",
                data={
                    "step": "synthesize_members",
                    "status": "running",
                    "message": "Synthesizing individual documentation wikis for member services...",
                },
            )

            services_info: List[ServiceNodeInfo] = []

            for name, b_path in bundle_map.items():
                # Pass 1 TOC for member
                toc = await self.synthesizer.pass1_generate_toc(
                    name, b_path, provenance=provenance_map.get(name)
                )
                # Pass 2 Pages for member
                await self.synthesizer.pass2_generate_pages(name, b_path, toc)
                # Extract metadata
                svc_info = extract_service_metadata(name, bundle_text_map[name], toc)
                services_info.append(svc_info)

            # 5. Synthesize Federated System Architecture & Cross-Links
            yield IngestionEvent(
                event="step",
                data={
                    "step": "mesh_extract",
                    "status": "running",
                    "message": "Scanning member repositories for service references, ports, and message topics...",
                },
            )

            detected_interactions = self.system_synthesizer.mesh_extractor.build_mesh(
                services_info, bundle_text_map
            )

            self.system_synthesizer.generate_system_wiki(
                system_name=sys_clean,
                display_name=disp_clean,
                services=services_info,
                bundle_map=bundle_text_map,
                interactions=detected_interactions,
            )

            self.system_synthesizer.inject_system_context_into_member_repos(
                system_name=sys_clean,
                system_display=disp_clean,
                services=services_info,
                interactions=detected_interactions,
            )

            # 6. Build PageIndex Trees for all member repos and the federated system
            yield IngestionEvent(
                event="step",
                data={
                    "step": "pageindex_all",
                    "status": "running",
                    "message": "Building vectorless PageIndex trees for all microservices and federated system...",
                },
            )

            async def build_tree_member(name: str):
                await self.indexer.build_repo_tree(name)

            # Build member trees + system tree concurrently
            tree_tasks = [build_tree_member(n) for n in repo_map.keys()]
            tree_tasks.append(build_tree_member(sys_clean))
            await asyncio.gather(*tree_tasks)

            # 7. Completed
            yield IngestionEvent(
                event="done",
                data={
                    "step": "completed",
                    "system": sys_clean,
                    "display_name": disp_clean,
                    "services_count": len(services_info),
                    "repos": list(repo_map.keys()),
                    "redirect": f"/wiki/{sys_clean}/overview",
                },
            )

        except Exception as e:
            yield IngestionEvent(
                event="error",
                data={"error": f"Multi-Repo Ingestion Error: {str(e)}"},
            )
