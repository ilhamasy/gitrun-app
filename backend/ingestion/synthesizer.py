"""
Two-Pass Document Synthesizer.
Pass 1: Generates Table of Contents (toc.json) schema from codebase bundle.
Pass 2: Synthesizes comprehensive Markdown pages in parallel and writes to content/.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.pageindex.llm import LLMClient


STANDARD_PAGES = [
    {
        "slug": "overview",
        "title": "System Overview",
        "description": "Core responsibilities, business domain, and high-level system boundaries.",
    },
    {
        "slug": "architecture",
        "title": "Internal Architecture",
        "description": "Package organization, event queues, concurrency models, and ledger consistency.",
    },
    {
        "slug": "setup",
        "title": "Setup & Configuration",
        "description": "Local development with Docker Compose, environment variables, and migration runs.",
    },
    {
        "slug": "api-reference",
        "title": "API Reference",
        "description": "REST and gRPC contracts, error codes, and idempotent transaction flows.",
    },
]


def detect_primary_language(bundle_text: str) -> str:
    """Detect dominant programming language from bundle file extensions."""
    counts = {
        "TypeScript": len(re.findall(r'<file path="[^"]*\.(?:ts|tsx)"', bundle_text)),
        "Go": len(re.findall(r'<file path="[^"]*\.go"', bundle_text)),
        "Python": len(re.findall(r'<file path="[^"]*\.py"', bundle_text)),
        "Rust": len(re.findall(r'<file path="[^"]*\.rs"', bundle_text)),
        "Java": len(re.findall(r'<file path="[^"]*\.java"', bundle_text)),
        "JavaScript": len(re.findall(r'<file path="[^"]*\.(?:js|jsx)"', bundle_text)),
    }
    sorted_langs = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    if sorted_langs and sorted_langs[0][1] > 0:
        return sorted_langs[0][0]
    return "Polyglot"


def extract_file_paths(bundle_text: str) -> List[str]:
    """Extract list of file paths included in the bundle."""
    return re.findall(r'<file path="([^"]+)"', bundle_text)


class DocSynthesizer:
    def __init__(
        self,
        content_dir: str | Path,
        llm_client: Optional[LLMClient] = None,
    ):
        self.content_dir = Path(content_dir).resolve()
        self.llm = llm_client or LLMClient()

    async def pass1_generate_toc(
        self,
        repo_name: str,
        bundle_path: Path,
    ) -> Dict[str, Any]:
        """
        Pass 1: Generates TOC schema with metadata and 4 standard pages.
        Writes content/<repo_name>/toc.json.
        """
        repo_dir = self.content_dir / repo_name
        repo_dir.mkdir(parents=True, exist_ok=True)

        bundle_content = bundle_path.read_text(encoding="utf-8", errors="replace")
        primary_lang = detect_primary_language(bundle_content)
        file_list = extract_file_paths(bundle_content)[:120]
        files_snippet = "\n".join(f"- {f}" for f in file_list)

        # Truncate bundle content for Pass 1 context prompt
        bundle_snippet = bundle_content[:35000]

        if not self.llm.is_configured():
            toc = self._fallback_toc(repo_name, primary_lang)
            (repo_dir / "toc.json").write_text(json.dumps(toc, indent=2), encoding="utf-8")
            return toc

        prompt = f"""You are an autonomous principal software architect.
Analyze this codebase bundle and synthesize a structured Table of Contents (TOC) schema for repository '{repo_name}'.

Repository Files:
{files_snippet}

Codebase Sample:
{bundle_snippet}

Grounding rules (mandatory):
- Describe only what the code above actually contains. Do not guess at
  technologies, brokers, datastores, or domain concepts that are not visible.
- The "description" must be supported by identifiable files or code in the
  sample. If the repository's purpose is unclear, say what it literally
  contains (e.g. "small Go module exposing two HTTP handlers") instead of
  inventing a business domain.
- Do not name a product (Kafka, Redis, Stripe, ...) unless that name appears in
  the code sample.

Output MUST be a valid JSON object strictly matching this schema:
{{
  "repo_name": "{repo_name}",
  "display_name": "<Human readable title derived from the repository itself>",
  "description": "<Concise 1-2 sentence summary of what this repository demonstrably contains>",
  "language": "{primary_lang}",
  "pages": [
    {{
      "slug": "overview",
      "title": "System Overview",
      "description": "<Summary of overview scope>"
    }},
    {{
      "slug": "architecture",
      "title": "Internal Architecture",
      "description": "<Summary of architecture scope>"
    }},
    {{
      "slug": "setup",
      "title": "Setup & Configuration",
      "description": "<Summary of setup scope>"
    }},
    {{
      "slug": "api-reference",
      "title": "API Reference",
      "description": "<Summary of API reference scope>"
    }}
  ]
}}
"""
        try:
            raw_res = await self.llm.complete(
                prompt=prompt,
                system="You return only strictly valid JSON matching the requested TOC schema.",
                json_mode=True,
                temperature=0.2,
            )
            data = json.loads(raw_res)
            # Ensure required keys exist
            data["repo_name"] = repo_name
            if "pages" not in data or len(data["pages"]) != 4:
                data["pages"] = STANDARD_PAGES
            toc = data
        except Exception:
            toc = self._fallback_toc(repo_name, primary_lang)

        (repo_dir / "toc.json").write_text(json.dumps(toc, indent=2), encoding="utf-8")
        return toc

    def _fallback_toc(self, repo_name: str, language: str) -> Dict[str, Any]:
        display_name = " ".join(part.capitalize() for part in repo_name.replace("-", " ").replace("_", " ").split())
        if not display_name.endswith("Service") and not display_name.endswith("App"):
            display_name = f"{display_name} Service"

        return {
            "repo_name": repo_name,
            "display_name": display_name,
            "description": f"{display_name} repository built with {language}.",
            "language": language,
            "pages": STANDARD_PAGES,
        }

    async def pass2_generate_pages(
        self,
        repo_name: str,
        bundle_path: Path,
        toc: Dict[str, Any],
        progress_callback: Optional[Any] = None,
    ) -> List[Path]:
        """
        Pass 2: Runs parallel LLM calls to generate 4 comprehensive Markdown pages.
        Writes content/<repo_name>/<slug>.md.
        """
        repo_dir = self.content_dir / repo_name
        repo_dir.mkdir(parents=True, exist_ok=True)

        bundle_content = bundle_path.read_text(encoding="utf-8", errors="replace")
        bundle_snippet = bundle_content[:45000]

        pages = toc.get("pages", STANDARD_PAGES)
        total_pages = len(pages)
        completed_count = 0

        async def generate_single_page(page_meta: Dict[str, str]) -> Path:
            nonlocal completed_count
            slug = page_meta["slug"]
            title = page_meta["title"]
            desc = page_meta.get("description", "")
            out_file = repo_dir / f"{slug}.md"

            if self.llm.is_configured():
                md_content = await self._generate_page_llm(
                    repo_name=repo_name,
                    slug=slug,
                    title=title,
                    description=desc,
                    bundle_snippet=bundle_snippet,
                    toc=toc,
                )
            else:
                md_content = self._fallback_page_markdown(
                    repo_name=repo_name,
                    slug=slug,
                    title=title,
                    description=desc,
                    bundle_content=bundle_content,
                    toc=toc,
                )

            out_file.write_text(md_content, encoding="utf-8")
            completed_count += 1
            if progress_callback:
                await progress_callback(completed_count, total_pages, slug)
            return out_file

        # Run page generation concurrently
        tasks = [generate_single_page(p) for p in pages]
        generated_paths = await asyncio.gather(*tasks)
        return generated_paths

    async def _generate_page_llm(
        self,
        repo_name: str,
        slug: str,
        title: str,
        description: str,
        bundle_snippet: str,
        toc: Dict[str, Any],
    ) -> str:
        prompt = f"""You are a principal technical author documenting repository '{repo_name}'.
Page title: '{title}'. Page slug: '{slug}'.
Page Scope: {description}

Repository Metadata:
- Display Name: {toc.get('display_name')}
- Description: {toc.get('description')}
- Language: {toc.get('language')}

Codebase Sample:
{bundle_snippet}

Grounding rules — these override every stylistic preference:
1. Start with a top-level '# {title}' heading.
2. Document only what is visible in the codebase sample above. Every named
   component, dependency, datastore, broker, environment variable, route, and
   technical claim must be traceable to code in that sample.
3. Never introduce a technology, product, or integration that does not appear
   in the sample. If a layer is not present, do not describe it.
4. Do not invent endpoints, environment variables, tables, metrics, or error
   codes. If the sample does not show them, write that it was not found.
5. Prefer citing real identifiers (function names, file paths, route strings,
   config keys) over generic prose.
6. A diagram is optional and only belongs here if it reflects the real module
   structure in the sample. Do not draw components that are not in the code.
7. Use '## Section Name' headings. Include a table only when you have real
   rows to put in it.
"""
        try:
            res = await self.llm.complete(
                prompt=prompt,
                system=(
                    "You write grounded technical documentation. You never describe "
                    "libraries, services, or behaviour that the provided code does not "
                    "contain. When information is missing you say so explicitly."
                ),
                temperature=0.2,
            )
            cleaned = res.strip()
            # If wrapped in markdown code fence, strip it
            if cleaned.startswith("```markdown"):
                cleaned = cleaned[len("```markdown") :].strip()
            elif cleaned.startswith("```md"):
                cleaned = cleaned[len("```md") :].strip()
            elif cleaned.startswith("```"):
                cleaned = cleaned[len("```") :].strip()
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3].strip()

            if not cleaned.startswith("# "):
                cleaned = f"# {title}\n\n{cleaned}"
            return cleaned
        except Exception:
            return self._fallback_page_markdown(
                repo_name=repo_name,
                slug=slug,
                title=title,
                description=description,
                bundle_content=bundle_snippet,
                toc=toc,
            )

    def _fallback_page_markdown(
        self,
        repo_name: str,
        slug: str,
        title: str,
        description: str,
        bundle_content: str,
        toc: Dict[str, Any],
    ) -> str:
        """
        Deterministic page rendering when no model is available.

        Every line here is derived from the bundle: file paths, declared routes,
        environment lookups, driver imports, and topic literals. Nothing is
        described that the code did not show, and absent facts are named as
        absent rather than filled in.
        """
        from backend.ingestion.mesh import UNKNOWN, extract_service_metadata

        evidence = extract_service_metadata(repo_name, bundle_content, toc)
        display_name = toc.get("display_name", repo_name)
        lang = toc.get("language", "Generic")

        files = extract_file_paths(bundle_content)[:40]
        files_table = "\n".join(f"| `{f}` |" for f in files) or f"| {UNKNOWN} |"

        def bullet(items: List[str], empty: str) -> str:
            return "\n".join(f"- {item}" for item in items) if items else f"- {empty}"

        stacks = (
            [f"**Datastore**: {s}" for s in evidence.datastores]
            + [f"**Message broker**: {b}" for b in evidence.brokers]
            + [f"**Observability**: {o}" for o in evidence.observability]
        )

        if slug == "overview":
            return f"""# {display_name} Overview

Repository `{repo_name}`, written in {lang}. This page records what the source
tree contains; anything marked `{UNKNOWN}` was searched for and not found.

## Files In Scope

| File |
| :--- |
{files_table}

## Detected Stack

{bullet(stacks, f"No datastore driver, message broker, or instrumentation library was found in the bundle.")}

## Runtime Surface

- **Listening port**: `{evidence.port_label}`
- **Declared routes**: {evidence.routes_label}
- **Environment variables read**: {(", ".join(f"`{v}`" for v in evidence.env_vars) if evidence.env_vars else UNKNOWN)}

## Description

{evidence.description}
"""

        if slug == "architecture":
            return f"""# {display_name} Internal Architecture

Module layout and declared entry points for `{repo_name}`, taken directly from
the bundle.

## Source Files

| File |
| :--- |
{files_table}

## Declared Routes

{bullet([f"`{e}`" for e in evidence.exposed_endpoints], "No route declarations were found in the bundle.")}

## Environment Variables

{bullet([f"`{v}`" for v in evidence.env_vars], "No environment lookups were found in the bundle.")}

## Dependencies Observed

{bullet(stacks, "No datastore driver, broker client, or instrumentation library was found.")}

## Not Documented Here

Cross-module runtime behaviour is only described when the bundle exposes it.
No concurrency model, saga, or persistence guarantee is asserted
because none was readable from the ingested files.
"""

        if slug == "setup":
            port_line = (
                f"- **Port**: `{evidence.port}`"
                if evidence.port
                else f"- **Port**: {UNKNOWN} (no port declaration found)"
            )
            env_table = (
                "\n".join(f"| `{v}` | read by the code |" for v in evidence.env_vars)
                or f"| {UNKNOWN} |"
            )
            return f"""# {display_name} Setup & Configuration

Runtime prerequisites observed in `{repo_name}`.

## Prerequisites

- **Language runtime**: {lang}
{port_line}

## Environment Variables

| Variable | Evidence |
| :--- | :--- |
{env_table}

## Startup

No start command was inferred from the bundle. Use the repository's own
entrypoint files:

{bullet([f"`{f}`" for f in files[:10]], "No files were available in the bundle.")}

## Verification

{bullet([f"health probe: `{e}`" for e in evidence.exposed_endpoints if "health" in e.lower()], "No health endpoint was declared in the bundle.")}
"""

        # api-reference
        route_table = (
            "\n".join(f"| `{e}` | declared in source |" for e in evidence.exposed_endpoints)
            or f"| {UNKNOWN} | no routes declared |"
        )
        header_list = ", ".join(f"`{h}`" for h in evidence.headers) if evidence.headers else UNKNOWN
        topic_list = (
            "\n".join(
                f"| `{t}` | {'published' if t in evidence.published_topics else ('subscribed' if t in evidence.subscribed_topics else 'declared')} |"
                for t in evidence.declared_topics
            )
            or f"| {UNKNOWN} | no topic literals found |"
        )

        return f"""# {display_name} API Reference

Interfaces declared in `{repo_name}`.

## Declared Routes

| Route | Status |
| :--- | :--- |
{route_table}

## Header Names

Headers referenced in code: {header_list}

## Message Topics

| Topic | Role |
| :--- | :--- |
{topic_list}

## Error Conventions

No error catalogue is documented here because none is declared explicitly in
the code bundle. Consult the source files above for actual error handling.
"""
