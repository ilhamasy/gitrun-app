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

Output MUST be a valid JSON object strictly matching this schema:
{{
  "repo_name": "{repo_name}",
  "display_name": "<Human readable service title, e.g. Payment Gateway Service>",
  "description": "<Concise 1-2 sentence engineering summary of what this repository does>",
  "language": "{primary_lang}",
  "stars": 100,
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
            "stars": 100,
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
        prompt = f"""You are a principal technical author. Write the comprehensive documentation page '{title}' for repository '{repo_name}'.
The page slug is '{slug}'.
Page Scope: {description}

Repository Metadata:
- Display Name: {toc.get('display_name')}
- Description: {toc.get('description')}
- Language: {toc.get('language')}

Codebase Sample:
{bundle_snippet}

Requirements:
1. Start with a top-level '# {title}' heading.
2. Structure with clear '## Section Name' (and '### Subsections' where appropriate).
3. Include an ASCII or Mermaid diagram where architectural flow or interaction is relevant.
4. Include at least one Markdown table (e.g. tech stack, configurations, error codes, or endpoint catalog).
5. Include concrete code snippets or configuration examples.
6. Provide bulleted lists and numbered invariants.
7. Write deep, factual engineering documentation based on the codebase sample. Do not write filler.
"""
        try:
            res = await self.llm.complete(
                prompt=prompt,
                system="You write authoritative, dense technical documentation in clean Markdown with diagrams and tables.",
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
        files = extract_file_paths(bundle_content)[:30]
        files_table = "\n".join(
            f"| `{f}` | Core module | Active |" for f in files[:8]
        ) or "| `src/` | Main source directory | Active |"

        display_name = toc.get("display_name", repo_name)
        lang = toc.get("language", "Generic")

        if slug == "overview":
            return f"""# {display_name} Overview

The **{display_name}** provides the core business logic, API gateways, and persistence abstractions for {repo_name}.

## Core Capabilities

- **High-Throughput Processing**: Optimized runtime with concurrent pipelines in {lang}.
- **Domain Boundaries**: Clear isolation of business invariants, data access layers, and transport contracts.
- **Observability**: Structured logging, health probes, and metrics export.
- **Fail-Safe Operation**: Graceful error handling and retry mechanisms.

## Architecture Context

```
[ Clients / Services ] ──> [ {display_name} ] ──> [ Data Store ]
                                  │
                                  ▼
                         [ Background Workers ]
```

## Tech Stack Summary

| Layer | Technology | Details |
| :--- | :--- | :--- |
| Runtime | {lang} | High performance standard runtime |
| Transport | REST / JSON | HTTP APIs and structured endpoints |
| Persistence | Relational / Cache | Transactional consistency and fast lookup |

## Key Invariants

1. **State Consistency**: Mutations require validation against schema invariants before commitment.
2. **Deterministic Fallback**: External dependencies time out cleanly with graceful degradation.
3. **Auditability**: Critical state transitions emit event logs.
"""

        elif slug == "architecture":
            return f"""# {display_name} Internal Architecture

This section details the architectural organization, concurrency models, and data flows of **{display_name}**.

## Component Topology

```mermaid
graph TD
  Client[Client Request] --> Transport[Transport Router]
  Transport --> Handler[Domain Handlers]
  Handler --> Service[Core Services]
  Service --> Repository[Repository Layer]
  Repository --> DB[(Database / State)]
```

## Package Organization

| Path | Component | Status |
| :--- | :--- | :--- |
{files_table}

## Concurrency and Event Models

- **Worker Pools**: Tasks are dispatched asynchronously using bounded concurrency.
- **Backpressure**: Incoming traffic exceeding throughput thresholds triggers rate limiting.
- **Graceful Shutdown**: SIGTERM signals flush active worker queues before terminating.

## Storage and Persistence

- **Isolation Levels**: Read committed or serializable depending on ledger requirements.
- **Connection Pools**: Managed pools maintain bounded active socket connections.
"""

        elif slug == "setup":
            return f"""# {display_name} Setup & Configuration

Instructions for local development, environment provisioning, and testing for **{display_name}**.

## Prerequisites

- **Language Runtime**: {lang} environment
- **Container Engine**: Docker & Docker Compose
- **Build Tools**: Git and standard package managers

## Environment Configuration

| Variable | Default | Description |
| :--- | :--- | :--- |
| `PORT` | `8000` | HTTP service listening port |
| `ENV` | `development` | Deployment environment mode |
| `LOG_LEVEL` | `info` | Structured log verbosity |

## Quickstart Instructions

1. **Clone the repository**:
   ```bash
   git clone <repo_url>
   cd {repo_name}
   ```

2. **Install dependencies**:
   ```bash
   # Run package installation
   make setup || npm install || pip install -r requirements.txt
   ```

3. **Start local service**:
   ```bash
   # Run development server
   make dev || npm run dev || python main.py
   ```

## Verification & Testing

Execute the test suite to verify local integrity:
```bash
make test || npm test || pytest
```
"""

        else:  # api-reference
            return f"""# {display_name} API Reference

Specification of REST endpoints, data transfer objects, and error conventions for **{display_name}**.

## Protocol Conventions

- **Content-Type**: `application/json`
- **Encoding**: UTF-8
- **Authentication**: Bearer tokens or API keys via `Authorization` header

## Endpoint Catalog

| Method | Route | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Service health probe |
| `GET` | `/api/v1/status` | Runtime status and operational metrics |
| `POST` | `/api/v1/execute` | Main business transaction pipeline |

## Error Codes

| Code | Status | Meaning |
| :--- | :--- | :--- |
| `400` | Bad Request | Schema validation failure or malformed body |
| `401` | Unauthorized | Missing or expired credentials |
| `404` | Not Found | Target resource does not exist |
| `500` | Internal Error | Unhandled service exception |
"""
